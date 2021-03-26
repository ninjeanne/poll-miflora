#!/bin/bash

sudo apt install python3 python3-pip bluetooth bluez #der standard Nutzer ist user:pi passwort:raspberry
sudo python3 -m pip install miflora btlewrap bluepy requests multitimer
sudo pip3 install -r requirements.txt
sudo ln -s /home/pi/bin/poll_miflora/poll_miflora.service /etc/systemd/system/poll_miflora.service #verlinkt den service
sudo systemctl daemon-reload #neuladen aller System-Services
sudo systemctl enable poll_miflora #aktivieren vom Service poll_miflora
sudo systemctl start poll_miflora #Service starten
