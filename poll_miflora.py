import logging as log
import sys
import threading
import time

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
_PLANT_NAME = "Plumeria"

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

class UnfulfilledRequirementException(Exception):
    """
    Marker exception type to signal startup failure.
    """

    pass


# Main entry point
def main():
    _configure_logger()
    _setup_exception_handling()
    _check_for_btle_backend_presence_or_abort()

    log.info("=== POLL MIFLORA STARTING (Backend: %s) ===", _BT_BACKEND.__name__)

    devices = _find_and_get_mac_addresses_of_miflora_peripheral()
    
    log.info("=====")
    log.info("Those are the mac addresses of all nearby sensors:")
    for mac_address in devices:
      log.info("%s", mac_adress)
    
    log.info("=====")
    
    for mac_address in devices:
      peripheral = MiFloraPoller(mac_address, _BT_BACKEND, adapter=_BT_ADAPTER)

      _receive_basic_statistics_for_peripheral(peripheral)

      polling_interval_in_seconds = _POLLING_INTERVAL_IN_MINUTES * 60
      poller = MultiTimer(interval=polling_interval_in_seconds, function=_send_current_sensor_data, kwargs={'mac_address': mac_address,'peripheral': peripheral})
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
    exit_code = -1

    if issubclass(exception_type, KeyboardInterrupt):
        log.info("Detected CTRL+C! Exiting...")
        log.info("=== POLL MIFLORA EXITING ===")
        exit(130) 
    elif issubclass(exception_type, btlewrap.base.BluetoothBackendException):
        log.error(
            "Received Bluetooth error! Error was: '%s' Aborting...",
            failsafe_message
        )
    elif issubclass(exception_type, UnfulfilledRequirementException):
        log.error(failsafe_message)
        exit_code = 1
    else:
        log.error(
            "Received exception '%s', error was : '%s'! Aborting...",
            exception_type.__name__,
            failsafe_message
        )

    log.info("=== POLL MIFLORA ABORTING ===")
    exit(exit_code)

def _check_for_btle_backend_presence_or_abort():
    available_backends = btlewrap.available_backends()
    if _BT_BACKEND not in available_backends:
        raise UnfulfilledRequirementException("Bluetooth LE backend '%s' was unavailable! Exiting..." % (_BT_BACKEND.__name__))

def _find_and_get_mac_addresses_of_miflora_peripheral() -> str:
    log.info("Scanning for %d seconds...", _SCAN_INTERVAL_IN_SECONDS)
    devices = miflora_scanner.scan(_BT_BACKEND, _SCAN_INTERVAL_IN_SECONDS)

    return devices

def _receive_basic_statistics_for_peripheral(peripheral: MiFloraPoller):
    log.info("Getting basic statistics about device...")
    firmware_version = peripheral.firmware_version()
    battery_level = peripheral.battery_level()
    log.info("Mi Flora Firmware: %s, Battery Status: %s percent", firmware_version, battery_level)

def _send_current_sensor_data(mac_address, peripheral: MiFloraPoller):
    log.info("Time's up! Fetching new sensor data...")

    temperature = peripheral.parameter_value(MI_TEMPERATURE)
    moisture = peripheral.parameter_value(MI_MOISTURE)
    light = peripheral.parameter_value(MI_LIGHT)
    conductivity = peripheral.parameter_value(MI_CONDUCTIVITY)
    battery_percentage = peripheral.parameter_value(MI_BATTERY)

    current_time_ms = int(time.time())*1000

    log.info("Sending plant status for %s %s with time %s...", _PLANT_NAME, mac_address, current_time_ms)
    response = requests.post(f"{_BACKEND_URL}/sensor/{mac_address}", json={
        "dateAndTime" : current_time_ms,
        "light": int(light),
        "temperature": float(temperature),
        "moisture": int(moisture),
        "conductivity": int(conductivity),
        "battery": int(battery_percentage),
        "name": str(_PLANT_NAME)
    })

    response.raise_for_status()

    log.info("Sending plant status was successful!")


if __name__ == "__main__":
    main()
