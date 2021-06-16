import pytest
import logging
import serial
from constants import *
from datetime import datetime
from unittest.mock import MagicMock
from manager import Effector, Effectors, SensorValues

log = logging.getLogger()
log.setLevel(logging.DEBUG)

class State():
    def __init__(self, name,
                 air_hum, air_temp, 
                 soil_hum, soil_temp,
                 blower_state_1,
                 water_pump_state_1,
                 radiator_valve_state_1, 
                 air_renew_valve_state_1,
                 expected_handshakes):
        self.name = name,
        self.air_hum = air_hum,
        self.air_temp = air_temp,
        self.soil_hum = soil_hum,
        self.soil_temp = soil_temp
        
        self.sensors = SensorValues("file")
        self.sensors.air_hum = air_hum
        self.sensors.air_temp = air_temp
        self.sensors.soil_hum = soil_hum
        self.sensors.soil_temp = soil_temp
        self.sensors.air_O2 = None
        
        self.expected_handshakes = expected_handshakes
    
        self.effectors = Effectors(
            "file",
            water_pump=Effector(
                    is_on=water_pump_state_1, 
                    prev_time=datetime.now(),
                    on_interval=WATER_PUMP_ON_INTERVAL
                ),
            blower=Effector(
                    is_on=blower_state_1, 
                    prev_time=datetime.now(),
                    on_interval=BLOWER_ON_INTERVAL,
                    off_interval=BLOWER_OFF_INTERVAL,
                ),
            radiator_valve=Effector(
                    is_on=radiator_valve_state_1, 
                    prev_time=datetime.now(),
                    on_interval=RADIATOR_VALVE_ON_INTERVAL
                ),
            air_renew_valve=Effector(
                    is_on=air_renew_valve_state_1, 
                    prev_time=datetime.now(),
                    on_interval=AIR_RENEW_ON_INTERVAL,
                    off_interval=AIR_RENEW_OFF_INTERVAL,
                ),
            )
        
state_list = [
    State(
        name = "nominal",
        air_hum = 40,
        air_temp = 22,
        soil_hum = SOIL_H2O_MIN,
        soil_temp = SOIL_TEMP_MAX - 10,
        blower_state_1 = False,
        water_pump_state_1 = False,
        radiator_valve_state_1 = False,
        air_renew_valve_state_1 = False,
        expected_handshakes = []
        
    ),
    State(
        name = "soil temp too high",
        air_hum = 40,
        air_temp = 22,
        soil_hum = SOIL_H2O_MIN,
        soil_temp = SOIL_TEMP_MAX + 1,
        blower_state_1 = False,
        water_pump_state_1 = False,
        radiator_valve_state_1 = False,
        air_renew_valve_state_1 = False,
        expected_handshakes= [RADIATOR_ON_MSG, BLOWER_ON_MSG]
    ),
    State(
        name = "soil temp too high, blower already on",
        air_hum = 40,
        air_temp = 22,
        soil_hum = SOIL_H2O_MIN,
        soil_temp = SOIL_TEMP_MAX + 1,
        blower_state_1 = True,
        water_pump_state_1 = False,
        radiator_valve_state_1 = False,
        air_renew_valve_state_1 = False,
        expected_handshakes= [RADIATOR_ON_MSG]
    ),
    State(
        name = "soil humidity too high",
        air_hum = 40,
        air_temp = 22,
        soil_hum = SOIL_H2O_MAX + 1,
        soil_temp = SOIL_TEMP_MAX + 1,
        blower_state_1 = False,
        water_pump_state_1 = False,
        radiator_valve_state_1 = False,
        air_renew_valve_state_1 = False,
        expected_handshakes= [BLOWER_ON_MSG, BLOWER_ON_MSG]
    ),
    State(
        name = "soil humidity too high with water pump to turn off",
        air_hum = 40,
        air_temp = 22,
        soil_hum = SOIL_H2O_MAX + 1,
        soil_temp = SOIL_TEMP_MAX + 1,
        blower_state_1 = False,
        water_pump_state_1 = True,
        radiator_valve_state_1 = False,
        air_renew_valve_state_1 = False,
        expected_handshakes= [BLOWER_ON_MSG, WATER_PUMP_OFF_MSG, BLOWER_ON_MSG]
    )
]

@pytest.mark.parametrize("case", state_list)
def test_state(case):
    logging.info(case.name)
    # Do not emit any real messages
    ser = serial.Serial()
    ser.write = MagicMock() 
    case.effectors.emit_state_change_msgs(ser, case.sensors)
    
    for handshake in case.expected_handshakes:
        assert(handshake in case.effectors.expected_handshakes.keys())
    assert(len(case.expected_handshakes) == len(case.effectors.expected_handshakes))