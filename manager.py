#!/usr/bin/env python3
import serial
import csv
import os
import logging
import git
import time
from threading import Thread, Lock
from multiprocessing.dummy import Pool as ThreadPool
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

repo = git.Repo(os.path.dirname(os.path.realpath(__file__)))

log_buffer = [] 

def update_log_file(lock, filename):
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            log_buffer.append(format_data_row(line))
        if len(log_buffer) > 0:
            # Get lock, write to file, and empty.
            pass

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

def write_data_to_file(filename):
    if not os.path.exists(filename):
        with open(filename, "a") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS.keys())
    with open(filename, "a") as f:
        writer = csv.writer(f)
        writer.writerow(data)

def upload_to_cloud(lock, start_time):
    while True:
        if (time.time() - start_time >= UPLOAD_INTERVAL_SECONDS):
            pass

if __name__ == '__main__':
    # Thead example form https://stackoverflow.com/questions/23100704/running-infinite-loops-using-threads-in-python
    start_time = time.time()
    lock = Lock()
    t1 = Thread(target = update_log_file, args=(lock, LOG_FILE))
    t2 = Thread(target = upload_to_cloud, args=(lock, start_time,))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()
    while True:
        pass
