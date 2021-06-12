from datetime import timedelta

# A place to put constants needed by testing function
# Not great, but will do for now.
WATER_PUMP_ON_INTERVAL = timedelta(seconds=2)
BLOWER_ON_INTERVAL = timedelta(seconds=10)
BLOWER_OFF_INTERVAL = timedelta(hours=1)
VALVE_BUFFER_INTERVAL = timedelta(seconds=5)
AIR_RENEW_ON_INTERVAL = timedelta(minutes=1)
AIR_RENEW_OFF_INTERVAL = timedelta(hours=8)
RADIATOR_VALVE_ON_INTERVAL = BLOWER_ON_INTERVAL + VALVE_BUFFER_INTERVAL
MAX_WAIT_HANDSHAKE = timedelta(seconds=10)