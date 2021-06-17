#!/usr/bin/env python3
import serial
import csv
import os
import logging
import git
import pytz 
from threading import Thread
from datetime import datetime, timezone, timedelta
from constants import *

format = "%(asctime)s: %(levelname)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

# Runtime values
TEST_ALL_SYSTEMS = False
UPDATE_EFFECTORS_STATES = True

IS_SOIL_H2O_SENSOR_ENABLED = True

DATA_FOLDER = "data"
SENSOR_DATA_FILEPATH = os.path.join(DATA_FOLDER, "sensor_values.csv")
EFFECTOR_DATA_FILEPATH = os.path.join(DATA_FOLDER, "effector_states.csv")

SENSOR_FIELDS = {
    "timestamp_utc": None,
    "soil_humidity": 1,
    "soil_temperature": 3, 
    "system_air_humidity": 5, 
    "system_air_temperature": 7, 
}

HEADER_SENSOR_DATA = "i"
HEADER_LOG_DATA = "j"

class Handshake():
    def __init__(self, timestamp, out_msg):
        self.timestamp = timestamp
        self.out_msg = out_msg
    
    def __repr__(self):
        return f"{self.out_msg}"
        
class Effector():
    def __init__(self, prev_time=datetime.now(), 
                curr_state=State.OFF, on_msg=None, off_msg=None,
                on_interval=None, off_interval=None, name=None):
        # Current state is the inverse of the last state
        self.curr_state: bool = curr_state
        self.next_state: State = curr_state
        self.prev_time: datetime = prev_time
        self.on_interval: int = on_interval
        self.off_interval: int = off_interval
        self.name: str = name
        self.on_msg: bytes = on_msg
        self.off_msg: bytes = off_msg
        
    def __repr__(self):
        return f"{self.name}"
    
    def toggle_on(self):
        self.next_state = State.ON
    
    def toggle_off(self):
        self.next_state = State.OFF
    
    def state_change_occured(self):
        if self.curr_state != self.next_state:
            return True
        
    def get_msg(self):
        """Get the Arduino message based on the state change
        """
        if self.next_state == State.ON: 
            return self.on_msg
        else: 
            return self.off_msg
        
    def update_prev_time_if_needed(self):
        """Update time at which the effector is last turned on
        """
        if self.next_state == State.ON: 
            self.prev_time = datetime.now()


class EffectorManager():
    def __init__(self, file=None, water_pump=None, blower=None, radiator_valve=None, air_renew_valve=None):
        self._file = file
        
        # Keep track of the unconfirmed state changes asked through serial
        self.expected_handshakes = dict()
        
        self.water_pump: Effector = water_pump
        self.blower: Effector = blower
        self.radiator_valve: Effector = radiator_valve
        self.air_renew_valve: Effector = air_renew_valve

    def update_state(self, ser: serial.Serial, effector: Effector):
        """Update the state of a specific effector.
        """
        if not effector.state_change_occured():
            return
        msg: bytes = effector.get_msg()
        effector.update_prev_time_if_needed()
            
        if msg not in self.expected_handshakes:
            # RPi is not waiting for serial to respond to this very same message 
            logging.info(f"MESSAGE for {effector}: {msg}")
            ser.write(msg)
            self.expected_handshakes[msg] = (Handshake(datetime.now(), msg))  
        elif datetime.now() - self.expected_handshakes[msg].timestamp >= MAX_WAIT_HANDSHAKE:
            logging.error(f"handshake from serial not received for message: {msg}")
            # Remove from expected handshake to retry forever
            self.expected_handshakes.pop(msg)
    
    def manage(self, ser: serial.Serial, sensors):
        """Manage all effectors and their state changes.
        """
        circulate_air = False
        need_drying = False # State at which all params are wrong because compost just got added
            
        # --------- Circulate air on Schedule-------------
        if current_time_is_at_night():
            pass
        elif datetime.now() - self.blower.prev_time >= \
                BLOWER_ON_INTERVAL + BLOWER_OFF_INTERVAL:
            # Force blower on at a set interval no matter what 
            # parameter updates happened beforehand.
            logging.info("turning blower on for set schedule")
            self.blower.toggle_on()
        elif self.blower.curr_state and datetime.now() - \
                                    self.blower.prev_time >= BLOWER_ON_INTERVAL:
            logging.info("turning blower off for set schedule")
            self.blower.toggle_on()
        
        # ------------- Air Renew ---------------
        # TODO: Complete when sensor is attached.
        if sensors.air_O2 is not None:
            pass
        else:
            # Renew air on a set schedule
            if datetime.now() - self.air_renew_valve.prev_time >= \
                        self.air_renew_valve.off_interval + self.air_renew_valve.on_interval:
                self.air_renew_valve.toggle_on()
                if self.air_renew_valve.state_change_occured():
                    logging.info("opening air renewal valve on set schedule")
                
            elif datetime.now() - self.air_renew_valve.prev_time >= \
                        self.air_renew_valve.on_interval:
                self.air_renew_valve.toggle_off()
                if self.air_renew_valve.state_change_occured():            
                    logging.info("closing air renewal valve on set schedule")
        
        # --------- Soil temperature -------------
        # Temperature should NEVER go above maximum.
        if sensors.soil_temp >= SOIL_TEMP_MAX:
            self.radiator_valve.toggle_on()
            if self.radiator_valve.state_change_occured():
                # Open radiator path and close direct path.
                logging.info("temperature high: opening radiator valve and closing shortest path valve")
                
            circulate_air = True
        elif sensors.soil_temp < SOIL_TEMP_MAX - TEMP_BUFFER_C \
                    and sensors.air_hum <= AIR_H2O_MAX:
            self.radiator_valve.toggle_off()
            if self.radiator_valve.state_change_occured():
                logging.info(
                    "temperature in range: closing radiator valve and opening shortest path valve")
        
        # --------- Soil Humidity -------------
        if not IS_SOIL_H2O_SENSOR_ENABLED:
            pass
        elif sensors.soil_hum >= SOIL_H2O_MAX:
            need_drying = True
            self.water_pump.toggle_off()
            if self.water_pump.state_change_occured():
                logging.info("soil humidity high: stop pump")
                
        # Water may take some time to diffuse through soil and reach the sensor. Do not water until 
        # normal levels are reached because that will likely mean that one part of the compost will 
        # be completely drenched.
        elif sensors.soil_hum < SOIL_H2O_MIN and datetime.now() - self.water_pump.prev_time >= \
                        self.water_pump.off_interval + self.water_pump.on_interval:
                self.water_pump.toggle_on()
                if self.water_pump.state_change_occured():
                    logging.info("soil humidity low, adding water for {self.water_pump.on_interval}")
                
        elif datetime.now() - self.water_pump.prev_time >= self.water_pump.on_interval:
            self.water_pump.toggle_off()
            if self.water_pump.state_change_occured():
                logging.info(f"stopping water pump for {self.water_pump.off_interval} to give time to the water to diffuse through the soil")
                    
        elif sensors.soil_hum >= SOIL_H2O_NORM:
            self.water_pump.toggle_off()
            if self.water_pump.state_change_occured():
                logging.info("soil humidity in range, stop water pump")
        
        # --------- Air Humidity -------------
        if sensors.air_hum > AIR_H2O_MAX:
            need_drying = True
        
        # --------- Circulate Air to Adjust Parameters-------------
        if current_time_is_at_night():
            self.radiator_valve.toggle_off()
            self.air_renew_valve.toggle_off()
            pass
        elif need_drying:
            if datetime.now() - self.blower.prev_time >= DRYING_ON_INTERVAL and self.blower.curr_state is State.ON:
                self.blower.toggle_off()
                self.radiator_valve.toggle_off()
                if self.blower.state_change_occured():
                    logging.info(f"turning blower off to let it cool down for {DRYING_ON_INTERVAL.seconds / 60} minutes")
            elif datetime.now() - self.blower.prev_time >= \
                        DRYING_OFF_INTERVAL + DRYING_ON_INTERVAL and self.blower.curr_state is State.OFF:
                self.blower.toggle_on()
                self.radiator_valve.toggle_on()
                self.air_renew_valve.toggle_on()
                if self.blower.state_change_occured():
                    logging.info("turning blower, radiator and renew valve on to dry compost") 
        elif circulate_air:
            if self.blower.state_change_occured():
                logging.info("turning blower on to adjust parameters")
            self.blower.toggle_on()
            
        # ----------- Emit all state update messages -------------
        effectors = [self.water_pump, self.blower, self.radiator_valve, self.air_renew_valve]
        for e in effectors:
            if e.state_change_occured():
                self.update_state(ser, e)
  
            
    def turn_off_all(self, ser):
        logging.info("turning off all effectors to start")
        self.update_state(ser, BLOWER_OFF_MSG)
        self.update_state(ser, RADIATOR_OFF_MSG)
        self.update_state(ser, AIR_RENEW_OFF_MSG)
        self.update_state(ser, WATER_PUMP_OFF_MSG)
        
    def handshake_received(self, handshake_msg):
        self.expected_handshakes.pop(handshake_msg)
        
        # Update the state of the effectors
        if handshake_msg == BLOWER_ON_MSG:
            self.blower.curr_state = True
            self.blower.prev_time = datetime.now()
        elif handshake_msg == BLOWER_OFF_MSG:
            self.blower.curr_state = False
            
        elif handshake_msg == RADIATOR_ON_MSG:
            self.radiator_valve.curr_state = True
            self.radiator_valve.prev_time = datetime.now()
        elif handshake_msg == RADIATOR_OFF_MSG:
            self.radiator_valve.curr_state = False
            
        elif handshake_msg == AIR_RENEW_ON_MSG:
            self.air_renew_valve.curr_state = True
            self.air_renew_valve.prev_time = datetime.now()
        elif handshake_msg == AIR_RENEW_OFF_MSG:
            self.air_renew_valve.curr_state = False
            
        elif handshake_msg == WATER_PUMP_ON_MSG:
            self.water_pump.curr_state = True
            self.water_pump.prev_time = datetime.now()
        elif handshake_msg == WATER_PUMP_OFF_MSG:
            self.water_pump.curr_state = False
        
        logging.info(f"handshake received for the following message: {handshake_msg}")
    
    def persist_to_file(self):
        column_names = ["timestamp_utc", "air_blower", "water_pump", "radiator_valve", "air_renew_valve"]
        row_values = [
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            self.blower.curr_state,
            self.water_pump.curr_state,
            self.radiator_valve.curr_state,
            self.air_renew_valve.curr_state
            ]
        create_file_if_not_exist(self._file, column_names)
        write_data_to_file(self._file, row_values)


class SensorValues():
    def __init__(self, file):
        self._file = file
        self.air_O2 = None  # Not implemented, sensor missing
        self.air_hum = None
        self.air_temp = None
        self.soil_hum = None
        self.soil_temp = None
        self.current_time = None

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
        return SENSOR_FIELDS.keys()
    
    def persist_to_file(self):
        create_file_if_not_exist(self._file, self.column_names())
        write_data_to_file(self._file, self.to_list())
        
    def log_to_console(self):
        log = f"air_hum: {self.air_hum}%, air_temp: {self.air_temp}ºC, soil_hum: {self.soil_hum}%, soil_temp: {self.soil_temp}ºC"
        logging.info(log)
        
################################################################

def manage_serial(effectors: EffectorManager):
    """Reads serial data and writes it to disk.
    """
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    sensor_vals = SensorValues(SENSOR_DATA_FILEPATH)
    effectors.turn_off_all(ser)
    if TEST_ALL_SYSTEMS:
        ser.write(RUN_ALL_EFFECTORS)
    if not UPDATE_EFFECTORS_STATES:
        logging.info("read-only mode activated")
        
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            logging.debug(line)
            handle_msg(line, sensor_vals, effectors, ser)

def handle_msg(msg, sensors, effectors, ser):
    """Parses serial messages, updates effectors, and writes to disk if needed.
    Return true if new information is acquired.
    """
    if not msg:
        return 
    elif msg[0] == HEADER_SENSOR_DATA:
        # This is sensor data
        sensors.update_values(msg[1:])
        sensors.persist_to_file()
        sensors.log_to_console()
        
        if UPDATE_EFFECTORS_STATES:
            effectors.emit_state_change_msgs(ser, sensors)
            effectors.persist_to_file()
    elif msg[0] == HEADER_LOG_DATA:
        logging.info(f"SERIAL IN: {msg[1:].strip()}")
    elif msg[0].encode() in effectors.expected_handshakes.keys():
        effectors.handshake_received(msg[0].encode())
    elif msg[0].encode() in ALL_MSG:
        logging.warn(f"expired handshake {msg[0].encode()} received but not accepted")
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
    start_time = datetime.now()
    while True:
        if datetime.now() - start_time >= UPLOAD_INTERVAL_SECONDS:
            start_time = datetime.now()
            repo.index.add(files)
            repo.index.commit("Push data")
            logging.info("start pushing data updates to repo...")
            repo.remotes.origin.push()
            logging.info("finished pushing data updates to repo.")

def current_time_is_at_night():
    tz = pytz.timezone('US/Pacific')
    now_pt = datetime.now(tz)
    if now_pt.hour > LOUD_SYSTEM_EARLIEST_HOUR_PT and now_pt.hour < LOUD_SYSTEM_LATEST_HOUR_PT:
        return False
    return True
    
if __name__ == '__main__':
    # Thead example form https://stackoverflow.com/questions/23100704/running-infinite-loops-using-threads-in-python
    repo = git.Repo(os.path.dirname(os.path.realpath(__file__)))

    water_pump = Effector(
        name="water pump",
        on_interval=WATER_PUMP_ON_INTERVAL, 
        off_interval=WATER_PUMP_OFF_INTERVAL,
        on_msg=WATER_PUMP_ON_MSG,
        off_msg=WATER_PUMP_OFF_MSG)
    
    blower = Effector(
        name="blower",
        on_interval=BLOWER_ON_INTERVAL, 
        off_interval=BLOWER_OFF_INTERVAL,
        on_msg=BLOWER_ON_MSG,
        off_msg=BLOWER_OFF_MSG)
    
    radiator_valve = Effector(
        name="radiator valve",
        on_interval=RADIATOR_VALVE_ON_INTERVAL,
        on_msg=RADIATOR_ON_MSG,
        off_msg=RADIATOR_OFF_MSG)
    
    air_renew_valve = Effector(
        name="air renewal valve",
        on_interval=AIR_RENEW_ON_INTERVAL, 
        off_interval=AIR_RENEW_OFF_INTERVAL,
        on_msg=AIR_RENEW_ON_MSG,
        off_msg=AIR_RENEW_OFF_MSG)
        
    effectors = EffectorManager(
        file=EFFECTOR_DATA_FILEPATH, 
        water_pump=water_pump, 
        blower=blower, 
        radiator_valve=radiator_valve, 
        air_renew_valve=air_renew_valve)
    
    files = [SENSOR_DATA_FILEPATH, EFFECTOR_DATA_FILEPATH]
    
    t1 = Thread(target = manage_serial, args=(effectors,))
    t2 = Thread(target = upload_changes_to_cloud, args=(repo, files, ))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()
    while True:
        pass
