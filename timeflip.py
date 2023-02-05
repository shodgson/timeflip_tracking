#!/usr/bin/env python3

import asyncio
import logging
import time
from bleak import BleakClient, BleakScanner
import argparse

# Parse arguments
parser = argparse.ArgumentParser(
        prog = 'TimeFlip logger',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Connect to a TimeFlip and log activities to a CSV file')
parser.add_argument('-a', '--address', type=str,
                    help='Bluetooth MAC address of TimeFlip device', 
                    required=True)
parser.add_argument('-p', '--password', type=str,
                    help='Password for TimeFlip device', 
                    default='000000')
parser.add_argument('-d', '--log_level', type=int, default=logging.INFO,
                    help='Log level (i.e. 10: debug, 20: info)')
parser.add_argument('-o', '--output',
                    default='timeflip_activities.csv',
                    type=argparse.FileType('a'),
                    help="Filepath to save activity timestamps") 
args = parser.parse_args()


# create console handler and set level to debug
logger = logging.getLogger(__name__)
logger.setLevel(args.log_level)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# TIMEFLIP DETAILS
address = args.address
password = args.password

# FACETS
activities = [
        "", # 0
        "", # 1
        "", # 2
        "", # 3
        "", # 4
        "Break", # 5
        "", # 6
        "Plan", # 7
        "", # 8
        "Chore", # 9
        "Mindless", # 10
        "Build", # 11
        "Think", # 12
        "Profile", # 13
        "", # 14
        "", # 15
        "", # 16
        "", # 17
        "" # 0
        ]

# TIMEFLIP CHARACTERISTICS                                       bytes  R/W/N
ACCEL_DATA = "F1196F51-71A4-11E6-BDF4-0800200C9A66"            #   6    R
FACETS = "F1196F52-71A4-11E6-BDF4-0800200C9A66"                #   1    R, N
COMMAND_RESULT_OUTPUT = "F1196F53-71A4-11E6-BDF4-0800200C9A66" #  21    R
COMMAND = "F1196F54-71A4-11E6-BDF4-0800200C9A66"               #  21    R, W
DOUBLE_TAP_DEFINITION = "F1196F55-71A4-11E6-BDF4-0800200C9A66" #   1    N
CALIBRATION_VERSION = "F1196F56-71A4-11E6-BDF4-0800200C9A66"   #   4    R, W
PASSWORD = "F1196F57-71A4-11E6-BDF4-0800200C9A66"              #   6    W


def facet(b):
    return int.from_bytes(b, "big")

track_time = int(time.time())

def log_time_start(activity):
    global track_time
    track_time = int(time.time())
    args.output.write(f"{track_time},{activity},")
    args.output.flush()

def log_time_end():
    global track_time
    new_track_time = int(time.time())
    duration = new_track_time - track_time
    track_time = new_track_time
    args.output.write(f"{track_time},{duration}\n")
    args.output.flush()

# TimeFlipScanner: not used
class TimeFlipScanner:
    def __init__(self):
        self._scanner = BleakScanner(self.scan_callback)
        self.timeflip_found = asyncio.Event()

    def scan_callback(self, device, advertising_data):
        if device.address == address and not self.timeflip_found.is_set():
            self.timeflip_found.set()
            logger.debug(f"{device}\t{advertising_data}")

    async def run(self):
        logger.debug(f"Scanning..")
        await self._scanner.start()
        logger.debug(f"Scanner started")
        await self.timeflip_found.wait()
        logger.debug(f"Timeflip found. Stopping scanner")
        await self._scanner.stop()
        await asyncio.sleep(1.0)

class TimeFlipReader:
    def __init__(self):
        self._client = BleakClient(address, self.disconnected_callback)
        self.disconnected_event = asyncio.Event()

    def disconnected_callback(self, client):
        logger.debug(f"Disconnected")
        log_time_end()
        self.disconnected_event.set()

    def changed_side(self, characteristic, data):
        logger.debug(f"{characteristic.description}: {data}")
        logger.debug(f"Facet: {facet(data)}")
        logger.info(f"New activity: {activities[facet(data)]}")
        activity = activities[facet(data)]
        log_time_end()
        log_time_start(activity)

    async def run(self):
        logger.info(f"Connected: {self._client.is_connected}")
        try:
            async with self._client as client:
                logger.debug(f"Connected: {self._client.is_connected}")
                logger.debug(f"Sending password to Timeflip")
                await client.write_gatt_char(PASSWORD, password.encode('ascii'))
                await asyncio.sleep(1.0)

                logger.debug(f"Finding starting facet")
                current_facet = await client.read_gatt_char(FACETS)
                logger.info(f"Currently set to facet #{facet(current_facet)}")
                activity = activities[facet(current_facet)]
                log_time_start(activity)

                await client.start_notify(FACETS, self.changed_side)
                logger.debug(f"Waiting for disconnection")
                await self.disconnected_event.wait()
                logger.debug("Disconnected and ending run()")

        except Exception as e:
            logger.debug("Could not connect..")
            logger.debug(e)
            logger.debug("Retrying in 60 seconds")
            await asyncio.sleep(60)
            await self.run()


if __name__ == '__main__':
    reader = TimeFlipReader()
    try:
        logger.debug("Start reader")
        asyncio.run(reader.run())
    except KeyboardInterrupt:
        logger.debug("Closing due to keyboard interrupt")
    except Exception as e:
        logger.error(e)
