#!/usr/bin/env python3
import serial
import csv
import os
import logging
import git
import time
from threading import Thread
from datetime import datetime, timezone

format = "%(asctime)s: %(levelname)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

DATA_FOLDER = "data"
SENSOR_DATA_FILEPATH = os.path.join(DATA_FOLDER, "sensor_data.csv")

UPLOAD_INTERVAL_SECONDS = 3600
SENSOR_FIELDS = {
            "timestamp_utc": None,
            "soil_humidity": 1,
            "soil_temperature": 3, 
            "system_air_humidity": 5, 
            "system_air_temperature": 7, 
        }

HEADER_SENSOR_DATA = "i"

FILES = {HEADER_SENSOR_DATA: SENSOR_DATA_FILEPATH}

WATER_PUMP_ON_INTERVAL = 2
BLOWER_ON_INTERVAL = 10
BLOWER_OFF_INTERVAL = 3600
VALVE_BUFFER_INTERVAL = 5
RADIATOR_VALVE_ON_INTERVAL = BLOWER_ON_INTERVAL + VALVE_BUFFER_INTERVAL


class Effector():
    def __init__(self, is_on=False, prev_time=None, 
            on_interval=None, off_interval=None):
        # Current state is the inverse of the last state
        self.is_on: bool = False
        self.prev_time: datetime = prev_time 
        self.on_interval: int = on_interval
        self.off_interval: int = off_interval


class Effectors():
    def __init__(self, water_pump, blower, radiator_valve, air_renew_valve):
        self.water_pump: Effector = water_pump
        self.blower: Effector = blower
        self.radiator_valve: Effector = radiator_valve
        self.air_renew_valve: Effector = air_renew_valve


class Sensors():
    def __init__(self, raw_line: str = None):
        if raw_line:
            split_data = raw_line.split()
            self.current_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            self.air_hum = split_data[SENSOR_FIELDS["system_air_humidity"]][:-1]
            self.air_temp = split_data[SENSOR_FIELDS["system_air_temperature"]][:-2]
            self.soil_hum = split_data[SENSOR_FIELDS["soil_humidity"]][:-1]
            self.soil_temp = split_data[SENSOR_FIELDS["soil_temperature"]][:-2]
        else:
            self.air_hum = None
            self.air_temp = None
            self.soil_hum = None
            self.soil_temp = None

    def to_list(self):
        l = list()
        l.append(self.current_time)
        l.append(self.soil_hum)
        l.append(self.soil_temp)
        l.append(self.air_hum)
        l.append(self.air_temp)
        return l



def handle_serial_in(files: dict, effectors: Effectors):
    """Reads serial data and writes it to disk.
    """
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            logging.info(line)
            handle_msg(line, files)

def handle_msg(msg, files):
    """Parses serial messages, updates effectors, and writes to disk if needed.
    """
    sensors = Sensors()

    header = msg[0]
    line = ""
    if msg[0] == HEADER_SENSOR_DATA:
        # This is sensor data
        sensors = Sensors(msg[1:])
    else:
        logging.error(f"data message cannot be read, header unsupported: '{msg}'")
        return

    create_file_if_not_exist(header, files[header])
    write_data_to_file(files[header], sensors.to_list())



def format_sensor_data_row(line) -> str:
    """Format a serial sensor data message.
    """

    return data

def format_effector_data_row(line) -> str:
    """Format a serial effector data message.
    """
    return ""

def format_log_data_row(line) -> str:
    """Format a serial log data message.
    """
    return ""

def create_file_if_not_exist(header: str, filename: str):
    if os.path.exists(filename):
        return
    column_names = SENSOR_FIELDS.values()
    with open(filename, "a") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)


def write_data_to_file(filename: str, line: str):
    with open(filename, "a") as f:
        writer = csv.writer(f)
        writer.writerow(line)

def upload_changes_to_cloud(repo, files: dict):
    start_time = time.time()
    while True:
        if (time.time() - start_time >= UPLOAD_INTERVAL_SECONDS):
            start_time = time.time()
            repo.index.add([files.keys()])
            repo.index.commit("Push data")
            logging.info("Start pushing data updates to repo...")
            repo.remotes.origin.push()
            logging.info("Finished pushing data updates to repo.")

if __name__ == '__main__':
    # Thead example form https://stackoverflow.com/questions/23100704/running-infinite-loops-using-threads-in-python
    repo = git.Repo(os.path.dirname(os.path.realpath(__file__)))

    water_pump = Effector(on_interval=WATER_PUMP_ON_INTERVAL)
    blower = Effector(on_interval=BLOWER_ON_INTERVAL, off_interval=BLOWER_OFF_INTERVAL)
    radiator_valve = Effector(on_interval=RADIATOR_VALVE_ON_INTERVAL)
    air_renew_valve = Effector(on_interval=BLOWER_ON_INTERVAL)

    effectors = Effectors(water_pump, blower, radiator_valve, air_renew_valve)
    
    t1 = Thread(target = handle_serial_in, args=(FILES, effectors))
    t2 = Thread(target = upload_changes_to_cloud, args=(repo, FILES,))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()
    while True:
        pass
