# -*- coding: utf-8 -*-
#
#
from libsoundtouch import soundtouch_device

master = soundtouch_device('192.168.18.1')
slave1 = soundtouch_device('192.168.18.2')
slave2 = soundtouch_device('192.168.18.3')

# Create a new zone
master.create_zone([slave1, slave2])

# Remove a slave
master.remove_zone_slave([slave2])

# Add a slave
master.add_zone_slave([slave2])
