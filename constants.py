from datetime import timedelta

# A place to put constants needed by testing function
# Not great, but will do for now.

# --- Sensor Values ---
AIR_O2_MIN = 15     # Minimum O2 % of system air
AIR_O2_NORM = 18    # Normal O2 % of system air
MAX_SOIL_TEMP_C = 60     # Max temperature allowed during thermophilic composting phase
TEMP_BUFFER_C = 5
SOIL_H2O_MAX = 60   # Max % humidity in soil
SOIL_H2O_NORM = 50  # Normal % humidity in soil
SOIL_H2O_MIN = 45   # Minimum % humidity in soil

# --- Time Intervals ---
WATER_PUMP_ON_INTERVAL = timedelta(seconds=2)
BLOWER_ON_INTERVAL = timedelta(seconds=10)
BLOWER_OFF_INTERVAL = timedelta(hours=1)
VALVE_BUFFER_INTERVAL = timedelta(seconds=5)
AIR_RENEW_ON_INTERVAL = timedelta(minutes=1)
AIR_RENEW_OFF_INTERVAL = timedelta(hours=8)
RADIATOR_VALVE_ON_INTERVAL = BLOWER_ON_INTERVAL + VALVE_BUFFER_INTERVAL
MAX_WAIT_HANDSHAKE = timedelta(seconds=10)

# Serial out messages
BLOWER_ON_MSG = 'a'.encode()
BLOWER_OFF_MSG = 'b'.encode()
RADIATOR_ON_MSG = 'c'.encode()
RADIATOR_OFF_MSG = 'd'.encode()
AIR_RENEW_ON_MSG = 'e'.encode()
AIR_RENEW_OFF_MSG = 'f'.encode()
WATER_PUMP_ON_MSG = 'g'.encode()
WATER_PUMP_OFF_MSG = 'h'.encode()

ALL_MSG = {BLOWER_ON_MSG, BLOWER_OFF_MSG, RADIATOR_ON_MSG, RADIATOR_OFF_MSG, 
           AIR_RENEW_ON_MSG, AIR_RENEW_OFF_MSG, WATER_PUMP_ON_MSG, WATER_PUMP_OFF_MSG}