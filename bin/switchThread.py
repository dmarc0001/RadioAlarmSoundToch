#!/usr/bin/python3
# -*- coding: utf-8 -*-

from threading import Thread, Lock
import RPi.GPIO as GPIO
from time import time, sleep

__author__ = 'Dirk Marciniak'
__copyright__ = 'Copyright 2017'
__license__ = 'GPL'
__version__ = '0.1'


class SwitchThread(Thread):
    """
    Thread zum schalten der Jalousien, die Relais dürfen nur begrenzt an bleiben
    """
    lock = Lock()

    def __init__(self, _log, _transfer_time, _channels):
        Thread.__init__(self)
        self.log = _log
        self.transfer_time = _transfer_time
        self.isRunning = True
        self.channels = _channels
        GPIO.setwarnings(False)
        GPIO.cleanup()
        self.config_gpio()
        self.log.debug("thread constructor...")

    def __del__(self):
        self.log.debug("thread destructor...")

    def run(self):
        self.isRunning = True
        while self.isRunning:
            if len(self.channels) == 0: # achtung kein lock...
                sleep(1)
                self.log.debug("empty queue...")
                continue
            # Liste nicht leer
            # gesamte Liste bearbeiten
            try:
                SwitchThread.lock.acquire()
                for channel, item in self.channels.items():
                    # is noch kein zeitstempel da == nix zu tun
                    if item['timestamp'] is None:
                        continue
                    else:
                        if item['timestamp'] == 0:
                            # da muss ich was machen
                            self.log.info("transfer channel %s (%s) to %s..." % (channel, item['name'], item['state']) )
                            # schalte den richtgen PIN ein (beide gleichzeitig gibt KURZSCHLUSS)
                            self.__set_channel_on(item)
                            # kennzeichen für Transfer in arbeit bis zum zeitzpunkt xxx
                            item['timestamp'] = int(time()) + self.transfer_time
                        elif int(time()) > item['timestamp']:
                            # da war was, die zeit ist um
                            self.log.info("transfer channel %s (%s) to %s...done" % (channel, item['name'], item['state']) )
                            self.__set_channel_off(item)
                            # und kennzeichnen dass keine Aktion mehr kommt
                            item['timestamp'] = None
            finally:
                SwitchThread.lock.release()
            sleep(1)

    def quit(self):
        self.isRunning = False

    def set_channel_updown(self, channel: str, direction: str):
        ret_val = False
        if direction == 'up' or direction == 'down':
            try:
                SwitchThread.lock.acquire()
                # gibt es den channel?
                if channel in self.channels:
                    # gib mir den channel als eintrag
                    item = self.channels[channel]
                    # ist der channel gerade unbenutzt?
                    if item['timestamp'] is None:
                        # ja, kann ich machen, ist nicht im Transfer
                        # ich teste nicht, ob der gewümschte Status schon da ist
                        # weil ich das nicht mit der hardware vergleichen kann 
                        # (keine Sensoren....)
                        # also setze den gewünschten Status
                        item['state'] = direction
                        # setzte das Zeichen zum Beginn des Transfers
                        item['timestamp'] = 0
                        ret_val = True
            finally:
                SwitchThread.lock.release()
        return ret_val

    def set_transfer_time(self, _transfer_time):
        self.transfer_time = _transfer_time

    def __set_channel_on(self, item: object):
        """
        Schalte den Schalter für UP oder DOWN an
        """
        if item['state'] == 'up':
            GPIO.setup(item['up_bcm_num'], GPIO.OUT, initial=GPIO.LOW)
        else:
            GPIO.setup(item['down_bcm_num'], GPIO.OUT, initial=GPIO.LOW)

    def __set_channel_off(self, item: object):
        """
        Schalte beide Schalter für UP oder DOWN aus
        """
        GPIO.setup(item['up_bcm_num'], GPIO.IN)
        GPIO.setup(item['down_bcm_num'], GPIO.IN)

    def config_gpio(self):
        # konfiguriere GPIO nach config
        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        try:
            SwitchThread.lock.acquire()        
            for channel, item in self.channels.items():
                self.__set_channel_off(item)
        finally:
            SwitchThread.lock.release()

