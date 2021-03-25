# Custom Xiaomi Mi Flora Poller
This poller is connecting to ONE nearby Mi Flora sensor, collecting its data and sending it to
the backend currently running at jeanne.plumeria.tech.
You can find the code for the backend here: https://gitlab.com/plumeria1/poll-miflora


## Installation
First you need to clone this repository and enter its directory.
```
git clone https://gitlab.com/plumeria1/poll-miflora.git
cd poll-miflora
```

To start this script enter the following command
```python3
sudo pip3 install bluepy miflora blurry
sudo python3 poll_miflora.py
```
or install the attached systemd service
```
sudo ln -s poll_miflora.service /etc/systemd/system/poll_miflora.service
sudo systemctl daemon-reload
sudo systemctl enable poll_miflora
sudo systemctl start poll_miflora
sudo systemctl status poll_miflora
```

