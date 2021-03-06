import argparse
import time
import struct
import os
import asyncio
from bluepy.sensortag import SensorTag
from bluepy.btle import BTLEException, AssignedNumbers
from model.soldier import Soldier
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


class TagReader:
    def __init__(self, addr, loop):
        self.enable_wait = 1  # wait seconds for enable sensor to read value
        self.addr = addr
        self.tag = None
        self.loop = loop

    def connect(self):
        try:
            self.tag = SensorTag(self.addr)
            return self.tag
        except BTLEException as e:
            if "Failed to connect to peripheral" in e.message:
                logger.error("connection failed: {0}".format(self.addr))
                return None
            if "Device disconnected" in e.message:
                logger.error("Device disconnected: {0}".format(self.addr))
                return None
            raise

    def get_values(self, vals):
        # tasks = [
        #     asyncio.ensure_future(self.brightness()),
        #     asyncio.ensure_future(self.temperature()),
        #     ... ]
        tasks = [asyncio.ensure_future(getattr(self, v)(), loop=self.loop)
                 for v in vals]
        loop.run_until_complete(asyncio.gather(*tasks))

        return {vals[i]:tasks[i].result() for i in range(len(vals))}

    async def brightness(self):
        try:
            self.tag.lightmeter.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.lightmeter.read()
            self.tag.lightmeter.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "lux"

    async def temperature(self):
        try:
            self.tag.IRtemperature.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.IRtemperature.read()[0]
            self.tag.IRtemperature.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "degC"

    async def target_temp(self):
        try:
            self.tag.IRtemperature.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.IRtemperature.read()[1]
            self.tag.IRtemperature.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "degC"

    async def humidity(self):
        try:
            self.tag.humidity.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.humidity.read()[1]
            self.tag.humidity.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "%"

    async def humi_temp(self):
        try:
            self.tag.humidity.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.humidity.read()[0]
            self.tag.humidity.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "degC"

    async def barometer(self):
        try:
            self.tag.barometer.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.barometer.read()[1]
            self.tag.barometer.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "mbar"

    async def baro_temp(self):
        try:
            self.tag.barometer.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.barometer.read()[0]
            self.tag.barometer.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "degC"

    async def accelerometer(self):
        try:
            self.tag.accelerometer.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.accelerometer.read()
            self.tag.accelerometer.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "g"

    async def magnetometer(self):
        try:
            self.tag.magnetometer.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.magnetometer.read()
            self.tag.magnetometer.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "uT"

    async def gyroscope(self):
        try:
            self.tag.gyroscope.enable()
            await asyncio.sleep(self.enable_wait, loop=self.loop)
            val = self.tag.gyroscope.read()
            self.tag.gyroscope.disable()
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "deg/sec"

    async def battery(self):
        try:
            b_uuid = AssignedNumbers.battery_level
            chara = self.tag.getCharacteristics(uuid=b_uuid)[0]
            val = struct.unpack('b', chara.read())[0]
        except BTLEException:
            logger.warn("failed to read value: {0}".format(self.addr))
            return None, None
        return val, "%"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-R', '--rec_addr', type=str, help="recruiter url",
        default="http://localhost:50000/recruiter/")
    parser.add_argument(
        '-T', '--tag_addr', type=str, help="sensortag's MAC addr")
    params = parser.parse_args()
    rec_addr = params.rec_addr
    tag_addr = params.tag_addr

    loop = asyncio.get_event_loop()
    reader = TagReader(tag_addr, loop)
    if reader.connect() is None:
        logger.error("failed to connect to SensorTag. retry after 10 seconds.")
        time.sleep(10)
        os._exit(1)

    # SensorTag専用に改造する措置
    tag_weapons = {
        "temperature":   None,
        "humidity":      None,
        "barometer":     None,
        "accelerometer": None,
        "magnetometer":  None,
        "gyroscope":     None,
        "brightness":    None,
        "target_temp":   None,
        "humi_temp":     None,
        "baro_temp":     None,
        "battery":       None,
    }

    soldier = Soldier("CC2650-" + tag_addr, "SensorTag")
    soldier.weapons.update(tag_weapons)
    soldier.tag = reader

    retry = 10
    for i in range(retry):
        if not soldier.awake(rec_addr, 10):
            logger.error("soldier.awake failed. retry after 10 seconds.")
            time.sleep(10)
            continue
        
        # soldier is working
        while True:
            pass
        break

    soldier.shutdown()
    loop.close()
