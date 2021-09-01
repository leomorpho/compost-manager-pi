from datetime import timedelta
from enum import Flag

# A place to put constants needed by testing function
# Not great, but will do for now.


class State(Flag):
    """A C-like enumeration to portray state as a boolean
    """
    ON = True
    OFF = False


# --- Sensor Values ---
AIR_O2_MIN = 15     # Minimum O2 % of system air
AIR_O2_NORM = 18    # Normal O2 % of system air
AIR_H2O_MAX = 80
SOIL_TEMP_MAX = 60  # Max temperature allowed during thermophilic composting phase in ºC
TEMP_BUFFER_C = 5
SOIL_H2O_MAX = 60   # Max % humidity in soil
SOIL_H2O_NORM = 50  # Normal % humidity in soil
SOIL_H2O_MIN = 45   # Minimum % humidity in soil

# --- Time Intervals ---
DRYING_ON_INTERVAL = timedelta(minutes=10)
DRYING_OFF_INTERVAL = timedelta(minutes=10)
WATER_PUMP_ON_INTERVAL = timedelta(seconds=5)
WATER_PUMP_OFF_INTERVAL = timedelta(minutes=5)
BLOWER_ON_INTERVAL = timedelta(minutes=1)
BLOWER_OFF_INTERVAL = timedelta(hours=1)
VALVE_BUFFER_INTERVAL = timedelta(seconds=5)
AIR_RENEW_ON_INTERVAL = timedelta(minutes=2)
AIR_RENEW_OFF_INTERVAL = timedelta(hours=8)
RADIATOR_VALVE_ON_INTERVAL = BLOWER_ON_INTERVAL + VALVE_BUFFER_INTERVAL
MAX_WAIT_HANDSHAKE = timedelta(seconds=10)

UPLOAD_INTERVAL_SECONDS = timedelta(seconds=900)

# Serial out messages. See 'MSG_TO_TEXT' for explanation.
BLOWER_ON_MSG = 'a'.encode()
BLOWER_OFF_MSG = 'b'.encode()
RADIATOR_ON_MSG = 'c'.encode()
RADIATOR_OFF_MSG = 'd'.encode()
AIR_RENEW_ON_MSG = 'e'.encode()
AIR_RENEW_OFF_MSG = 'f'.encode()
WATER_PUMP_ON_MSG = 'g'.encode()
WATER_PUMP_OFF_MSG = 'h'.encode()

RUN_ALL_EFFECTORS = 'j'.encode()
# REMINDER: message 'i' cannot be used as it is the sensor info HEADER!

MSG_TO_TEXT = {
    'a'.encode(): "turn blower on",
    'b'.encode(): "turn blower off",
    'c'.encode(): "turn radiator on",
    'd'.encode(): "turn radiator off",
    'e'.encode(): "turn renew air valve on",
    'f'.encode(): "turn renew air valve off",
    'g'.encode(): "turn water pump on",
    'h'.encode(): "turn water pump off",
    'j'.encode(): "test all effectors",
}

ALL_MSG = {BLOWER_ON_MSG, BLOWER_OFF_MSG, RADIATOR_ON_MSG, RADIATOR_OFF_MSG,
           AIR_RENEW_ON_MSG, AIR_RENEW_OFF_MSG, WATER_PUMP_ON_MSG, WATER_PUMP_OFF_MSG}

# Times during which loud systems should NOT be turned on
LOUD_SYSTEM_EARLIEST_HOUR_PT = 6
LOUD_SYSTEM_LATEST_HOUR_PT = 22
