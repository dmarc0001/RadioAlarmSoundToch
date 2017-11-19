#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import logging.handlers
from time import time, sleep, strftime
from configparser import ConfigParser
import re
import os
import shutil
from libsoundtouch import discover_devices
from libsoundtouch.device import SoundTouchDevice
from libsoundtouch.utils import Source

__author__ = 'Dirk Marciniak'
__copyright__ = 'Copyright 2017'
__license__ = 'GPL'
__version__ = '0.1'

config_file = "/var/www/config/alert.ini"


class SoundtouchDiscoverDevices:
    DEFAULT_LOGFILE = "alert_clock.log"
    DEFAULT_DEVICESFILE = "avaivible_devices"
    DEFAULT_LOGLEVEL = logging.DEBUG
    enclosing_dquotes = re.compile(r"(^\"|\"$)")
    regex_global = re.compile(r'^global$', re.IGNORECASE)

    def __init__(self, _config_file: str):
        """
        Der Konstruktor
        :param _config_file: Konfiguration lesen
        """
        self.config_file = _config_file
        self.logfile = SoundtouchDiscoverDevices.DEFAULT_LOGFILE
        self.loglevel = SoundtouchDiscoverDevices.DEFAULT_LOGLEVEL
        self.devices_file = SoundtouchDiscoverDevices.DEFAULT_DEVICESFILE
        self.loglevel_name = 'DEBUG'
        self.__read_config()
        self.log = self.__make_logger(self.logfile, self.loglevel)
        self.log.info("create SoundtouchDiscoverDevices...")
        self.log.debug("logfile: {}".format(self.logfile))
        self.log.debug("loglevel: {}, {}".format(self.loglevel_name, self.loglevel))
        self.log.debug("devices file: {}".format(self.devices_file))

    def __del__(self):
        """
        Der Destruktor
        :return:
        """
        if self.log is not None:
            self.log.info("delete SoundtouchDiscoverDevices...")

    def discover(self):
        """
        Finde Soundtouch geräte und schreibe dies in einer Datei nieder
        :return:
        """
        self.log.debug("search for available soundtouch devices...")
        #
        # finde Geräte im Netzwerk ergibt ein array
        #
        _available_dev = discover_devices(timeout=15)  # Default timeout is 15 seconds
        self.log.info("search for available soundtouch devices ends with {} found devices".format(
            len(_available_dev)))
        #
        # und nun in eine Datei schreiben
        #
        devconfig = dict()
        for device in _available_dev:
            _item = self.__make_configitem(device)
            devconfig[device.config.name] = _item
        #
        # schreiben
        #
        self.__write_config(devconfig)

    @staticmethod
    def __make_configitem(_dev: object):
        _item = SoundtouchDiscoverDevices.__make_default_item()
        _item['name'] = _dev.config.name
        _item['host'] = _dev.host
        _item['port'] = _dev.port
        _item['type'] = _dev.config.type
        return _item

    @staticmethod
    def __make_default_item():
        _item = dict()
        _item['name'] = 'unknown'
        _item['host'] = '127.0.0.1'
        _item['port'] = '8090'
        _item['type'] = 'unknown'
        return _item

    def __write_config(self, _devconfig: dict):
        """
        Schreibe die Geräte-Konfigdatei
        :param _devconfig: Konfigurationsobjekt
        :return: Erfolgreich ist True
        """
        parser = ConfigParser()
        for section in sorted(_devconfig):
            self.log.debug("create device section [{}]...".format(section))
            # eliminiere None als Value
            _tmp_section = _devconfig[section]
            for key in _tmp_section.keys():
                if _tmp_section[key] is None:
                    _tmp_section[key] = " "
            # Sektion in den Parser einfügen
            parser[section] = _tmp_section
        #
        # eine neue Datei zum schreiben öffnen und schreiben
        #
        _new_file = "{}.new".format(self.devices_file)
        self.log.debug("write to {} ...".format(_new_file))
        with open(_new_file, 'w') as configfile:
            parser.write(configfile)
        configfile.close()
        self.log.debug("write to {} ...OK".format(_new_file))
        #
        # jetzt die neue config über die alte kopieren
        #
        if self.log is not None:
            self.log.debug("copy new config file to {} ...".format(self.devices_file))
        else:
            print("copy new config file to {} ...".format(self.devices_file))
        shutil.copyfile(_new_file, self.devices_file)
        #
        # lösche die alte "new" datei
        #
        if self.log is not None:
            self.log.debug("remove temporary new config file {} ...".format(_new_file))
        else:
            print("remove temporary new config file to {} ...".format(_new_file))
        os.remove(_new_file)
        #
        return True

    def __read_config(self):
        """
        Lese den Namen und den Ort des Logfiles aus der Konfiguration und speicher ihn
        in einer Objektglobalen Variable
        :return: nix
        """
        parser = ConfigParser()
        parser.read(self.config_file)
        # Versuch 1 der vorgesehene Name
        _logfile = parser["global"]["logfile2"]
        if _logfile is not None and len(_logfile) > 3:
            self.logfile = _logfile
        else:
            # Versuch 2 der daemon Logfilename
            _logfile = parser["global"]["logfile"]
            if _logfile is not None and len(_logfile) > 3:
                self.logfile = _logfile
        # zurück ob gefunden oder nicht. Wenn nicht bleibt der DEFAULT Wert
        #
        # Loglevel noch versuchen
        #
        _level = parser['global']['loglevel']
        self.loglevel_name = _level
        if _level == 'debug':
            self.loglevel = logging.DEBUG
        elif _level == 'info':
            self.loglevel = logging.INFO
        elif _level == 'warning':
            self.loglevel = logging.WARN
        elif _level == 'error':
            self.loglevel = logging.ERROR
        elif _level == 'critical':
            self.loglevel = logging.CRITICAL
        else:
            self.loglevel = logging.INFO
        # in welche Datei die gefundenen Geräte schreiben?
        _devices_file = parser['global']['devices_file']
        if _devices_file is not None and len(_devices_file) > 3:
            self.devices_file = _devices_file
        return

    @staticmethod
    def __make_logger(_logfile: str, _my_loglevel):
        """
        Erzeuge den Logger
        :param _logfile: Name des Logfiles
        :param _my_loglevel: Loglevel für das Programm
        :return: Loggerobjekt
        """
        log = logging.getLogger("alert_clock_bose")
        log.setLevel(_my_loglevel)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(module)s: %(message)s", '%Y%m%d %H:%M:%S')
        f_handler = logging.handlers.RotatingFileHandler(_logfile, maxBytes=5000000, backupCount=5)
        f_handler.setFormatter(formatter)
        if _my_loglevel == logging.DEBUG:
            c_handler = logging.StreamHandler()
            c_handler.setFormatter(formatter)
            log.addHandler(c_handler)
        log.addHandler(f_handler)
        return log


def main():
    """Hauptprogramm"""
    """Hauptprogramm"""
    discover_obj = SoundtouchDiscoverDevices(config_file)
    discover_obj.discover()
    sleep(.7)
    del discover_obj
    exit(0)


if __name__ == '__main__':
    main()
