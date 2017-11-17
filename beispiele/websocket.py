# -*- coding: utf-8 -*-
#
#
from libsoundtouch import soundtouch_device
import time


# Events listeners

# Volume updated
def volume_listener(volume):
    print(volume.actual)


# Status updated
def status_listener(status):
    print(status.track)


# Presets updated
def preset_listener(presets):
    for preset in presets:
        print(preset.name)


# Zone updated
def zone_status_listener(zone_status):
    if zone_status:
        print(zone_status.master_id)
    else:
        print('no Zone')


device = soundtouch_device('192.168.18.1')

device.add_volume_listener(volume_listener)
device.add_status_listener(status_listener)
device.add_presets_listener(preset_listener)
device.add_zone_status_listener(zone_status_listener)

# Start websocket thread. Not started by default
device.start_notification()

time.sleep(600)  # Wait for events
