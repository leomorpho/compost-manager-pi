#!/usr/bin/env python3
import serial
import csv
import os
import logging
import git
import time
from threading import Thread
from datetime import datetime, timezone

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

LOG_FILE = "logs.csv"
UPLOAD_INTERVAL_SECONDS = 3600
FIELDS = {
        "timestamp_utc": None,
        "soil_humidity": 1,
        "soil_temperature": 3, 
        "system_air_humidity": 5, 
        "system_air_temperature": 7, 
        "system_air_heat_index": 9,
        }


def update_log_file(filename):
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            line = format_data_row(line)
            write_data_to_file(filename, line)

def format_data_row(line):
    split_data = line.split()
    data = []
    data.append(datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    data.append(split_data[FIELDS["soil_humidity"]][:-1])
    data.append(split_data[FIELDS["soil_temperature"]][:-2])
    data.append(split_data[FIELDS["system_air_humidity"]][:-1])
    data.append(split_data[FIELDS["system_air_temperature"]][:-2])
    data.append(split_data[FIELDS["system_air_heat_index"]][:-2])

    logging.info(data)
    return data

def write_data_to_file(filename, data):
    if not os.path.exists(filename):
        with open(filename, "a") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS.keys())
    with open(filename, "a") as f:
        writer = csv.writer(f)
        writer.writerow(data)

def upload_to_cloud(repo, filename):
    start_time = time.time()
    while True:
        if (time.time() - start_time >= UPLOAD_INTERVAL_SECONDS):
            start_time = time.time()
            repo.index.add([filename])
            repo.index.commit("Push data")
            logging.info("Start pushing data updates to repo...")
            repo.remotes.origin.push()
            logging.info("Finished pushing data updates to repo.")

if __name__ == '__main__':
    # Thead example form https://stackoverflow.com/questions/23100704/running-infinite-loops-using-threads-in-python
    repo = git.Repo(os.path.dirname(os.path.realpath(__file__)))

    t1 = Thread(target = update_log_file, args=(LOG_FILE,))
    t2 = Thread(target = upload_to_cloud, args=(repo, LOG_FILE,))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()
    while True:
        pass
