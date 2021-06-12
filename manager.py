#!/usr/bin/env python3
import serial
import csv
import os
import logging
import git
import time
from threading import Thread
from datetime import datetime, timezone
from constants import *

format = "%(asctime)s: %(levelname)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

DATA_FOLDER = "data"
SENSOR_DATA_FILEPATH = os.path.join(DATA_FOLDER, "sensor_values.csv")
EFFECTOR_DATA_FILEPATH = os.path.join(DATA_FOLDER, "effector_states.csv")

UPLOAD_INTERVAL_SECONDS = 3600
SENSOR_FIELDS = {
    "timestamp_utc": None,
    "soil_humidity": 1,
    "soil_temperature": 3, 
    "system_air_humidity": 5, 
    "system_air_temperature": 7, 
}

HEADER_SENSOR_DATA = "i"

class Handshake():
    def __init__(self, timestamp, out_msg):
        self.timestamp = timestamp
        self.out_msg = out_msg
        
class Effector():
    def __init__(self, is_on=False, prev_time=datetime.now(), 
            on_interval=None, off_interval=None):
        # Current state is the inverse of the last state
        self.is_on: bool = is_on
        self.prev_time: datetime = prev_time 
        self.on_interval: int = on_interval
        self.off_interval: int = off_interval


class Effectors():
    def __init__(self, file, water_pump, blower, radiator_valve, air_renew_valve):
        self._file = file
        self.water_pump: Effector = water_pump
        self.blower: Effector = blower
        self.radiator_valve: Effector = radiator_valve
        self.air_renew_valve: Effector = air_renew_valve
        self.expected_handshakes = dict()


    def emit_state_change_msg(self, ser: serial.Serial, msg: str):
        if msg not in self.expected_handshakes:
            ser.write(msg)
            self.expected_handshakes[msg] = (Handshake(datetime.now(), msg))   
        elif datetime.now() - self.expected_handshakes[msg].timestamp >= MAX_WAIT_HANDSHAKE:
            logging.error(f"handshake from serial not received for message: {msg}")
            # Remove from expected handshake to retry forever
            self.expected_handshakes.pop(msg)
    
    def emit_state_change_msgs(self, ser: serial.Serial, sensors):
        circulate_air = False
        
        # ------------- Air Renew ---------------
        # TODO: Complete when sensor is attached.
        if sensors.air_O2 is not None:
            pass
        else:
            # Renew air on a set schedule
            if datetime.now() - self.air_renew_valve.prev_time >= \
                        self.air_renew_valve.off_interval + self.air_renew_valve.on_interval and \
                        not self.air_renew_valve.is_on:
                
                logging.info("opening air renewal valve on set schedule")
                self.emit_state_change_msg(ser, AIR_RENEW_ON_MSG)
                circulate_air = True
                
            elif datetime.now() - self.air_renew_valve.prev_time >= \
                        self.air_renew_valve.on_interval and self.air_renew_valve.is_on:
                            
                logging.info("closing air renewal valve on set schedule")
                self.emit_state_change_msg(ser, AIR_RENEW_OFF_MSG)
        
        # --------- Radiator -------------
        # Temperature should NEVER go above maximum.
        if sensors.air_temp >= MAX_SOIL_TEMP_C:
            if not self.radiator_valve.is_on:
                # Open radiatior path and close direct path.
                logging.info(
                    "temperature high: opening radiator valve and closing shortest path valve")
                self.emit_state_change_msg(ser, RADIATOR_ON_MSG)
                
            circulate_air = True
        elif sensors.air_temp < MAX_SOIL_TEMP_C - TEMP_BUFFER_C and self.radiator_valve.is_on:
            logging.info(
                "temperature in range: closing radiator valve and opening shortest path valve")
            self.emit_state_change_msg(ser, RADIATOR_OFF_MSG)
        
        # --------- Humidity -------------
        if sensors.soil_hum >= SOIL_H2O_MAX:
            if self.water_pump.is_on:
                logging.info("soil humidity high: aerating for evaporation")
                self.emit_state_change_msg(ser, WATER_PUMP_OFF_MSG)
                circulate_air = True
        elif sensors.soil_hum < SOIL_H2O_MIN:
            if not self.water_pump.is_on:
                logging.info("soil humidity low: adding water")
                self.emit_state_change_msg(ser, WATER_PUMP_ON_MSG)
        elif sensors.soil_hum >= SOIL_H2O_NORM and self.water_pump.is_on:
            logging.info("soil humidity in range: stop water pump")
            self.emit_state_change_msg(ser, WATER_PUMP_OFF_MSG)
        
        # --------- Circulate air -------------
        if circulate_air:
            self.blower.prev_time = datetime.now()
            if not self.blower.is_on:
                logging.info("turning blower on to adjust parameters")
                self.emit_state_change_msg(ser, BLOWER_ON_MSG)
        elif datetime.now() - self.blower.prev_time >= \
                BLOWER_ON_INTERVAL + BLOWER_OFF_INTERVAL:
            # Force blower on at a set interval no matter what 
            # parameter updates happened beforehand.
            logging.info("turning blower on for set schedule")
            self.emit_state_change_msg(ser, BLOWER_ON_MSG)
        elif self.blower.is_on and datetime.now() - \
                                    self.blower.prev_time >= BLOWER_ON_INTERVAL:
            logging.info("turning blower off for set schedule")
            self.emit_state_change_msg(ser, BLOWER_OFF_MSG)
    
    # def verify_handshakes(self):
    #     for _, handshake in self.expected_handshakes:
    #         if datetime.now() - handshake.timestamp >= MAX_WAIT_HANDSHAKE:
    #             logging.error(f"handshake from serial not received for message: {handshake.out_msg}")
    #             # Remove from expected handshake to retry forever
    #             self.expected_handshakes.pop(handshake.out_msg)
            
    def handshake_received(self, handshake_msg):
        # TODO: I think it's here that I should update the .is_on and .prev_time attributes
        self.expected_handshakes.pop(handshake_msg)
        
        # Update the state of the effectors
        if handshake_msg == BLOWER_ON_MSG:
            self.blower.is_on = True
            self.blower.prev_time = datetime.now()
        elif handshake_msg == BLOWER_OFF_MSG:
            self.blower.is_on = False
            
        elif handshake_msg == RADIATOR_ON_MSG:
            self.radiator_valve.is_on = True
            self.radiator_valve.prev_time = datetime.now()
        elif handshake_msg == RADIATOR_OFF_MSG:
            self.radiator_valve.is_on = False
            
        elif handshake_msg == AIR_RENEW_ON_MSG:
            self.air_renew_valve.is_on = True
            self.air_renew_valve.prev_time = datetime.now()
        elif handshake_msg == AIR_RENEW_OFF_MSG:
            self.air_renew_valve.is_on = False
            
        elif handshake_msg == WATER_PUMP_ON_MSG:
            self.water_pump.is_on = True
            self.water_pump.prev_time = datetime.now()
        elif handshake_msg == WATER_PUMP_OFF_MSG:
            self.water_pump.is_on = False
        
        logging.info(f"handshake received for the following message: {handshake_msg}")
    
    def persist_to_file(self):
        column_names = ["timestamp_utc", "air_blower", "water_pump", "radiator_valve", "air_renew_valve"]
        row_values = [
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            self.blower.is_on,
            self.water_pump.is_on,
            self.radiator_valve.is_on,
            self.air_renew_valve.is_on
            ]
        create_file_if_not_exist(self._file, column_names)
        write_data_to_file(self._file, row_values)


class SensorValues():
    def __init__(self, file):
        self._file = file
        self.air_O2 = None  # Not implemented, sensor missing
        # self.air_hum = None
        # self.air_temp = None
        # self.soil_hum = None
        # self.soil_temp = None
        # self.current_time = None

    def update_values(self, raw_line):
        split_data = raw_line.split()
        self.current_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self.air_hum = float(split_data[SENSOR_FIELDS["system_air_humidity"]][:-1])
        self.air_temp = float(split_data[SENSOR_FIELDS["system_air_temperature"]][:-2])
        self.air_O2 = None
        self.soil_hum = float(split_data[SENSOR_FIELDS["soil_humidity"]][:-1])
        self.soil_temp = float(split_data[SENSOR_FIELDS["soil_temperature"]][:-2])
            
    def to_list(self):
        l = list()
        l.append(self.current_time)
        l.append(self.soil_hum)
        l.append(self.soil_temp)
        l.append(self.air_hum)
        l.append(self.air_temp)
        return l
    
    def column_names(self):
        return SENSOR_FIELDS.values()
    
    def persist_to_file(self):
        create_file_if_not_exist(self._file, self.column_names())
        write_data_to_file(self._file, self.to_list())
        
    def log_to_console(self):
        log = f"air_hum: {self.air_hum}%, air_temp: {self.air_temp}ºC, soil_hum: {self.soil_hum}%, soil_temp: {self.soil_temp}ºC"
        logging.info(log)
        
################################################################

def manage_serial(effectors: Effectors):
    """Reads serial data and writes it to disk.
    """
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    sensor_vals = SensorValues(SENSOR_DATA_FILEPATH)
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            handle_msg(line, sensor_vals, effectors)
            sensor_vals.persist_to_file()
            sensor_vals.log_to_console()
            effectors.emit_state_change_msgs(ser, sensor_vals)
            effectors.persist_to_file()
            

def handle_msg(msg, sensors, effectors):
    """Parses serial messages, updates effectors, and writes to disk if needed.
    """
    if msg[0] == HEADER_SENSOR_DATA:
        # This is sensor data
        sensors.update_values(msg[1:])
    elif msg[0].encode() in effectors.expected_handshakes.keys():
        effectors.handshake_received(msg[0].encode())
    else:
        logging.error(f"data message cannot be read, header '{msg}' unsupported.")
            
def create_file_if_not_exist(filename: str, column_names):
    if os.path.exists(filename):
        return
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
            logging.info("start pushing data updates to repo...")
            repo.remotes.origin.push()
            logging.info("finished pushing data updates to repo.")

if __name__ == '__main__':
    # Thead example form https://stackoverflow.com/questions/23100704/running-infinite-loops-using-threads-in-python
    repo = git.Repo(os.path.dirname(os.path.realpath(__file__)))

    water_pump = Effector(on_interval=WATER_PUMP_ON_INTERVAL)
    blower = Effector(on_interval=BLOWER_ON_INTERVAL, off_interval=BLOWER_OFF_INTERVAL)
    radiator_valve = Effector(on_interval=RADIATOR_VALVE_ON_INTERVAL)
    air_renew_valve = Effector(on_interval=AIR_RENEW_ON_INTERVAL, off_interval=AIR_RENEW_OFF_INTERVAL)

    effectors = Effectors(EFFECTOR_DATA_FILEPATH, water_pump, blower, radiator_valve, air_renew_valve)
    files = [SENSOR_DATA_FILEPATH, EFFECTOR_DATA_FILEPATH]
    
    t1 = Thread(target = manage_serial, args=(effectors,))
    t2 = Thread(target = upload_changes_to_cloud, args=(repo, files, ))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()
    while True:
        pass
