# Raspberry Pi Compost Manager
This manager maintains an enclosed compost within predetermined environmental values. 



The following metrics can be controlled:

* Soil humidity
* Air humidity 
* Soil and air temperature
* Oxygen concentration
* Forced aeration

## Getting Started
To run, use python3:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 manager.py
```
It may optionally  be installed as a service so that it automatically resumes on computer reboot.
## General Architecture

This package is meant to run on a unix machine acting as a controller to a slave microcontroller. A Raspberry Pi 2 and an Arduino Nano were selected for this project. These two communicate by sending and receiving simple messages over serial. 

## Messaging

The master and slave communicate over serial. If the master sends a state update message to the slave and receives no confirmation, the master will

## Future Extensions

* Instead of using CSV files to store logs of sensors and effectors, use time series database. Influxdata and Timescale also have nice GUI to visualize the data.
* It would be nice to directly connect the microcontrollers to Wifi such that multiple ones can be controlled from a single manager. This is easy to achieve for Arduinos. This would allow automating a compost, as