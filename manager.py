#!/usr/bin/env python3
import serial
import csv
import os
import logging
import git

logging.basicConfig(level = logging.INFO)

LOG_FILE = "logs.csv"
FIELDS = {
        "soil_humidity": 1,
        "soil_temperature": 3, 
        "system_air_humidity": 5, 
        "system_air_temperature": 7, 
        "system_air_heat_index": 9,
        }

repo = git.Repo(os.path.dirname(os.path.realpath(__file__)))

def write_data_row(filename, line):
    """Append a new row of data to a csv. If the csv doesn't exist, create it.
    """
    if not os.path.exists(filename):
        with open(filename, "a") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS.keys())
    
    split_data = line.split()
    data = []
    data.append(split_data[FIELDS["soil_humidity"]][:-1])
    data.append(split_data[FIELDS["soil_temperature"]][:-2])
    data.append(split_data[FIELDS["system_air_humidity"]][:-1])
    data.append(split_data[FIELDS["system_air_temperature"]][:-2])
    data.append(split_data[FIELDS["system_air_heat_index"]][:-2])

    logging.info(data)

    with open(filename, "a") as f:
        writer = csv.writer(f)
        writer.writerow(line)


if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            write_data_row(LOG_FILE, line)
