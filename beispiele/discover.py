# -*- coding: utf-8 -*-
from libsoundtouch import discover_devices

devices = discover_devices(timeout=2)  # Default timeout is 5 seconds


for device in devices:
    print(device.config.name + " - " + device.config.type)
    