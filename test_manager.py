import pytest
import logging
import serial
import manager
from constants import *
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from manager import Effector, EffectorManager, SensorValues

log = logging.getLogger()
log.setLevel(logging.DEBUG)


class TestState():
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

        self.effectors = EffectorManager(
            "file",
            water_pump=Effector(
                name="water pump",
                curr_state=water_pump_state_1,
                prev_time=datetime.now(),
                on_interval=WATER_PUMP_ON_INTERVAL,
                off_interval=WATER_PUMP_OFF_INTERVAL,
                on_msg=WATER_PUMP_ON_MSG,
                off_msg=WATER_PUMP_OFF_MSG,
            ),
            blower=Effector(
                name="blower",
                curr_state=blower_state_1,
                prev_time=datetime.now() - DRYING_OFF_INTERVAL -
                DRYING_ON_INTERVAL - timedelta(seconds=1),
                on_interval=BLOWER_ON_INTERVAL,
                off_interval=BLOWER_OFF_INTERVAL,
                on_msg=BLOWER_ON_MSG,
                off_msg=BLOWER_OFF_MSG,
            ),
            radiator_valve=Effector(
                name="radiator valve",
                curr_state=radiator_valve_state_1,
                prev_time=datetime.now(),
                on_interval=RADIATOR_VALVE_ON_INTERVAL,
                on_msg=RADIATOR_ON_MSG,
                off_msg=RADIATOR_OFF_MSG,
            ),
            air_renew_valve=Effector(
                name="air renewal valve",
                curr_state=air_renew_valve_state_1,
                prev_time=datetime.now(),
                on_interval=AIR_RENEW_ON_INTERVAL,
                off_interval=AIR_RENEW_OFF_INTERVAL,
                on_msg=AIR_RENEW_ON_MSG,
                off_msg=AIR_RENEW_OFF_MSG,
            ),
        )


state_list = [
    TestState(
        name="nominal",
        air_hum=40,
        air_temp=22,
        soil_hum=SOIL_H2O_MIN,
        soil_temp=SOIL_TEMP_MAX - 10,
        blower_state_1=State.OFF,
        water_pump_state_1=State.OFF,
        radiator_valve_state_1=State.OFF,
        air_renew_valve_state_1=State.OFF,
        expected_handshakes=[]

    ),
    TestState(
        name="soil temp too high",
        air_hum=40,
        air_temp=22,
        soil_hum=SOIL_H2O_MIN,
        soil_temp=SOIL_TEMP_MAX + 1,
        blower_state_1=State.OFF,
        water_pump_state_1=State.OFF,
        radiator_valve_state_1=State.OFF,
        air_renew_valve_state_1=State.OFF,
        expected_handshakes=[RADIATOR_ON_MSG, BLOWER_ON_MSG]
    ),
    TestState(
        name="soil temp too high, blower already on",
        air_hum=40,
        air_temp=22,
        soil_hum=SOIL_H2O_MIN,
        soil_temp=SOIL_TEMP_MAX + 1,
        blower_state_1=State.ON,
        water_pump_state_1=State.OFF,
        radiator_valve_state_1=State.OFF,
        air_renew_valve_state_1=State.OFF,
        expected_handshakes=[RADIATOR_ON_MSG]
    ),
    TestState(
        name="soil humidity too high",
        air_hum=40,
        air_temp=22,
        soil_hum=SOIL_H2O_MAX + 1,
        soil_temp=40,
        blower_state_1=State.OFF,
        water_pump_state_1=State.OFF,
        radiator_valve_state_1=State.OFF,
        air_renew_valve_state_1=State.OFF,
        expected_handshakes=[BLOWER_ON_MSG, RADIATOR_ON_MSG, AIR_RENEW_ON_MSG]
    ),
    TestState(
        name="soil humidity too high with water pump to turn off",
        air_hum=40,
        air_temp=22,
        soil_hum=SOIL_H2O_MAX + 1,
        soil_temp=SOIL_TEMP_MAX + 1,
        blower_state_1=State.OFF,
        water_pump_state_1=State.ON,
        radiator_valve_state_1=State.OFF,
        air_renew_valve_state_1=State.OFF,
        expected_handshakes=[
            BLOWER_ON_MSG, WATER_PUMP_OFF_MSG, RADIATOR_ON_MSG, AIR_RENEW_ON_MSG]
    )
]


@pytest.mark.parametrize("case", state_list)
def test_state(case):
    logging.info(case.name)
    # Do not emit any real messages
    ser = serial.Serial()
    ser.write = MagicMock()
    manager.current_time_is_at_night = MagicMock(return_value=False)
    case.effectors.manage(ser, case.sensors)

    for handshake in case.expected_handshakes:
        logging.info(f"Expected handshake: {MSG_TO_TEXT[handshake]}")

    for handshake in case.effectors.expected_handshakes.keys():
        logging.info(f"Received handshake: {MSG_TO_TEXT[handshake]}")

    for handshake in case.expected_handshakes:
        assert(handshake in case.effectors.expected_handshakes.keys())
    assert(len(case.expected_handshakes) == len(
        case.effectors.expected_handshakes))
