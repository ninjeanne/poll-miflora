import logging as log
import sys
import threading
from datetime import datetime

import btlewrap
from miflora import miflora_scanner
from miflora.miflora_poller import (
    MI_BATTERY,
    MI_CONDUCTIVITY,
    MI_LIGHT,
    MI_MOISTURE,
    MI_TEMPERATURE,
    MiFloraPoller,
)

from multitimer import MultiTimer

import requests


# Configuration - Plant name reported to backend
_PLANT_NAME = "Ananas"

# Configuration - Mi Flora polling interval in minutes
_POLLING_INTERVAL_IN_MINUTES = 10

# Configuration - How long to scan for a Mi Flora peripheral in seconds
_SCAN_INTERVAL_IN_SECONDS = 10

# Configuration - Log level
_LOG_LEVEL = log.INFO

# Configuration - Backend URL
_BACKEND_URL = "https://plumeria.jeanne.tech"

# Configuration - The BTLE backend to be used with Mi Flora
_BT_BACKEND = btlewrap.BluepyBackend

# Configuration - The Bluetooth device to be used
_BT_ADAPTER = "hci0"


# Main entry point
def main():
    _configure_logger()
    _setup_exception_handling()
    _check_for_btle_backend_presence_or_abort()

    log.info("=== POLL MIFLORA STARTING (Backend: %s) ===", _BT_BACKEND.__name__)

    mac_address = _find_and_get_mac_address_of_miflora_peripheral()
    peripheral = MiFloraPoller(mac_address, _BT_BACKEND, adapter=_BT_ADAPTER)

    _receive_basic_statistics_for_peripheral(peripheral)

    _register_peripheral_as_plant_in_backend(peripheral, _PLANT_NAME)

    polling_interval_in_seconds = _POLLING_INTERVAL_IN_MINUTES * 60
    poller = MultiTimer(interval=polling_interval_in_seconds, function=_send_current_sensor_data, kwargs={'peripheral': peripheral})
    poller.start()

def _configure_logger():
    log.basicConfig(level=_LOG_LEVEL)

def _setup_exception_handling():
    """
    Setup a custom exception handler both for <main> and other threads.
    """

    sys.excepthook = __handle_exception

    # This only works Python 3.8 and greater.
    threading.excepthook = lambda args: __handle_exception(args.exc_type, args.exc_value, args.exc_traceback, args.thread)

def __handle_exception(exception_type, exception_object, exception_traceback, thread=None):
    cause = exception_object.__cause__
    message = str(cause or exception_object)
    failsafe_message = "<unknown>" if not message else message

    if issubclass(exception_type, KeyboardInterrupt):
        log.info("Detected CTRL+C! Exiting...")
        log.info("=== POLL MIFLORA EXITING ===")
        exit(130) 
    elif issubclass(exception_type, btlewrap.base.BluetoothBackendException):
        log.error(
            "Received Bluetooth error! Error was: '%s' Aborting...",
            failsafe_message
        )
    else:
        log.error(
            "Received exception '%s', error was : '%s'! Aborting...",
            exception_type.__name__,
            failsafe_message
        )

    log.info("=== POLL MIFLORA ABORTING ===")
    exit(-1)

def _check_for_btle_backend_presence_or_abort():
    available_backends = btlewrap.available_backends()
    if _BT_BACKEND not in available_backends:
        log.error("Bluetooth LE backend '%s' was unavailable! Exiting...", _BT_BACKEND.__name__)

        log.info("=== POLL MIFLORA ABORTING ===")
        exit(1)

def _find_and_get_mac_address_of_miflora_peripheral() -> str:
    log.info("Scanning for %d seconds...", _SCAN_INTERVAL_IN_SECONDS)
    devices = miflora_scanner.scan(_BT_BACKEND, _SCAN_INTERVAL_IN_SECONDS)
    if len(devices) != 1:
        log.error("Did not find exactly 1 Mi Flora peripheral, found %d instead! Exiting...")
        exit(1)

    mac_address = devices[0]
    log.info("Found MiFlora peripheral with MAC address '%s'.", mac_address)

    return mac_address

def _receive_basic_statistics_for_peripheral(peripheral: MiFloraPoller):
    log.info("Getting basic statistics about device...")
    firmware_version = peripheral.firmware_version()
    battery_level = peripheral.battery_level()
    log.info("Mi Flora Firmware: %s, Battery Status: %s percent", firmware_version, battery_level)

def _register_peripheral_as_plant_in_backend(peripheral: MiFloraPoller, plant_name: str):
    log.info("Registering plant '%s' in backend...", plant_name)
    response = requests.post(f"{_BACKEND_URL}/plant", json={
        "name": str(plant_name),
        "data": [],
    })
    log.debug(response.text)

    response.raise_for_status()

    log.info("Registration successful!")

def _send_current_sensor_data(peripheral: MiFloraPoller):
    log.info("Time's up! Fetching new sensor data...")

    temperature = peripheral.parameter_value(MI_TEMPERATURE)
    moisture = peripheral.parameter_value(MI_MOISTURE)
    light = peripheral.parameter_value(MI_LIGHT)
    conductivity = peripheral.parameter_value(MI_CONDUCTIVITY)
    battery_percentage = peripheral.parameter_value(MI_BATTERY)

    current_time_iso8601 = datetime.now().astimezone().replace(microsecond=0).isoformat()

    log.info("Sending plant status for '%s'...", _PLANT_NAME)
    response = requests.post(f"{_BACKEND_URL}/plant/{_PLANT_NAME}/sensor", json={
        "dateAndTime" : str(current_time_iso8601),
        "light": int(light),
        "temperature": float(temperature),
        "moisture": int(moisture),
        "conductivity": int(conductivity),
        "battery": int(battery_percentage),
    })

    response.raise_for_status()

    log.info("Sending plant status was successful!")


if __name__ == "__main__":
    main()
