#!/usr/bin/python3
# -*- coding: utf-8 -*-

from time import time, sleep, strftime
from configparser import ConfigParser
import logging
import logging.handlers
import json
import hashlib
import os
import re
import shutil
from threading import Lock

config_file = '../config/alert.ini'


class ConfigFileObj:
    enclosing_dquotes = re.compile(r"(^\"|\"$)")
    regex_global = re.compile(r'^global$', re.IGNORECASE)
    CONFIG_LOCK = Lock()

    def __init__(self, _log: logging.Logger, _file_name: str):
        self.log = _log
        self.config_file = _file_name
        self.config_modify_time = None
        self.config = dict()
        self.dict_hash = None
        if self.log is not None:
            self.log.info("read config file {}...".format(self.config_file))
        else:
            print("read config file {}...".format(self.config_file))
        self.config = self.read_configfile(self.config_file)
        # konfig als hash um zu merken wenn was verändert wurde
        self.dict_hash = self.__get_hashstr(self.config)
        if self.log is not None:
            self.log.debug("current config hash: '{}'".format(self.dict_hash))
        else:
            print("current config hash: '{}'".format(self.dict_hash))

    def reload_configfile(self):
        return self.read_configfile(self.config_file)

    def read_configfile(self, _file_name: str = None):
        """
        Lies config ein (wenn dateiname gegeben ist) und gib config-Objekt zurück
        :param _file_name:
        :return:
        """
        new_config = dict()
        self.config_file = _file_name
        # merke mir die Bearbeitungszeit
        fileinfo = os.stat(self.config_file)
        self.config_modify_time = fileinfo.st_mtime
        parser = ConfigParser()
        parser.read(self.config_file)
        sections = parser.sections()
        for section in sections:
            if self.log is not None:
                self.log.debug('section "[{}]" found...'.format(section))
            else:
                print('section "[{}]" found...'.format(section))
            items = parser.items(section)
            # erstelle eine leere vordefinierte Sektion
            if ConfigFileObj.regex_global.match(section):
                c_items = ConfigFileObj.__make_default_config()
            else:
                c_items = ConfigFileObj.__make_default_entrys()
            # lese einträge...    
            for item in items:
                name = item[0]
                val = item[1]
                if self.log is not None:
                    self.log.debug("  [{}] => '{}' = '{}'".format(section, name, val))
                else:
                    print("  [{}] => '{}' = '{}'".format(section, name, val))
                c_items[name] = val
            new_config[section] = c_items
        if ConfigFileObj.CONFIG_LOCK.acquire(timeout=1.0):
            seclist = list(self.config.keys())
            for section in seclist:
                del self.config[section]
            for section in new_config:
                self.config[section] = new_config[section]
            ConfigFileObj.CONFIG_LOCK.release()
        else:
            self.log.warning("Can't lock CONFIG_LOCK! (read configfile)")
        return self.config

    def read_avail_devices(self):
        """
        Lese verfügbare soundtouch geräte aus externer Datei in
        :return: Liste mit verfügbaren soundtouch Devices
        """
        _devices = dict()
        # gibt es eine Datei dafür?
        if self.config['global']['devices_file'] is None:
            if self.log is not None:
                self.log.error("not an file for soundtouch devices found in config!")
                self.log.error("please insert in section [global] an key 'devices_file'")
            else:
                print("not an file for soundtouch devices found in config!")
                print("please insert in section [global] an key 'devices_file'")
            return _devices
        #
        # jetzt lies die Datei aus und stelle eine Konfiguration zur Verfügung
        #
        parser = ConfigParser()
        parser.read(self.config['global']['devices_file'])
        sections = parser.sections()
        for section in sections:
            if self.log is not None:
                self.log.debug('device (section in config file)  "[{}]" found...'.format(section))
            items = parser.items(section)
            _complete_item = ConfigFileObj.__make_default_deviceitem()
            for item in items:
                name = item[0]
                val = item[1]
                if self.log is not None:
                    self.log.debug("  [{}] => '{}' = '{}'".format(section, name, val))
                _complete_item[name] = val
            _devices[section] = _complete_item
        return _devices

    @staticmethod
    def __make_default_deviceitem():
        _item = dict()
        _item['name'] = 'unknown'
        _item['host'] = '127.0.0.1'
        _item['port'] = '8090'
        _item['type'] = 'unknown'
        return _item

    @staticmethod
    def get_empty_configitem():
        return ConfigFileObj.__make_default_entrys()

    @staticmethod
    def __make_default_entrys():
        _items = dict()
        _items['enable'] = 'false'
        _items['time'] = '06:00'
        _items['days'] = 'all'
        _items['date'] = None
        _items['source'] = 'PRESET_1'
        _items['raise_vol'] = 'false'
        _items['volume'] = '23'
        _items['devices'] = None
        _items['source_account'] = None
        _items['note'] = 'standart ALARM'
        _items['type'] = None
        _items['location'] = None
        _items['duration'] = '50m'
        return _items

    @staticmethod
    def __make_default_config():
        _items = dict()
        _items['loglevel'] = 'warning'
        _items['server_addr'] = 'localhost'
        _items['network_timeout'] = '10s'
        _items['timezone'] = 'UTC + 02:00'
        _items['gui_theme'] = 'b'
        _items['server_port'] = '26106'
        _items['console_log'] = 'True'
        _items['autorefresh'] = '5s'
        _items['logfile'] = '/var/log/alarm_clock.log'
        return _items

    @staticmethod
    def __get_hashstr(_config_object: dict):
        """
        Errechne die MD5 Summe eines configobjektes zum Vergleich
        :param _config_object: dasa objekt zum vergleich
        :return: HEX Ausgabe des Hashwertes
        """
        hashobj = hashlib.md5()
        json_str = json.dumps(_config_object, sort_keys=True).encode('utf-8')
        hashobj.update(json_str)
        dig = hashobj.hexdigest()
        return dig
        # return hashobj.update(json.dumps(_config_object, sort_keys=True).encode('utf-8')).hexdigest()

    def write_config_file(self, _force: bool = False):
        """
        Schreibe das configfile auf Disk (mit sicherungskopie)
        :param _force: bei True immer schreiben, egal ob änderungen oder nicht
        :return: True bei OK
        TODO: Eigentümer zu www-data setzten
        """
        if self.log is not None:
            self.log.debug("called write_config_file...")
        if not _force:
            if ConfigFileObj.CONFIG_LOCK.acquire(timeout=1.0):
                curr_hash = self.__get_hashstr(self.config)
                ConfigFileObj.CONFIG_LOCK.release()
            else:
                self.log.warning("Can't lock CONFIG_LOCK! (write config file)")
            if self.log is not None:
                self.log.info("HASH curr: {}".format(curr_hash))
                self.log.info("HASH orig: {}".format(self.dict_hash))
            if self.dict_hash == curr_hash:
                if self.log is not None:
                    self.log.debug("write_config_file...OK (not required)")
                return True
        #
        # configparser erzeugen zum schreiben in die datei
        #
        parser = ConfigParser()
        # das config-objekct wieder in ein parserobj konvertieren
        if ConfigFileObj.CONFIG_LOCK.acquire(timeout=2.0):
            for section in sorted(self.config):
                if self.log is not None:
                    self.log.debug("create section [{}]...".format(section))
                else:
                    print("create section [{}]...".format(section))
                # eliminiere None als Value
                _tmp_section = self.config[section]
                for key in _tmp_section.keys():
                    if _tmp_section[key] is None:
                        _tmp_section[key] = " "
                # Sektion einfügen
                parser[section] = _tmp_section
            ConfigFileObj.CONFIG_LOCK.release()
        else:
            self.log.warning("Can't lock CONFIG_LOCK! (write config file)")
        #
        # eine neue Datei zum schreiben öffnen und schreiben
        #
        _new_file = "{}.new".format(self.config_file)
        if self.log is not None:
            self.log.debug("write to {} ...".format(_new_file))
        else:
            print("write to {} ...".format(_new_file))
        try:
            with open(_new_file, 'w') as configfile:
                parser.write(configfile)
            configfile.close()
            if self.log is not None:
                self.log.debug("write to {} ...OK".format(_new_file))
            else:
                print("write to {} ...OK".format(_new_file))
        except PermissionError:
            if self.log is not None:
                self.log.debug("write to {} ...permission error! Check file/directory permisions.".format(_new_file))
            else:
                print("write to {} ...permission error! Check file/directory permisions.".format(_new_file))
        #
        # die alte configdatei in sicherung kopieren
        #
        dir_name = os.path.dirname(self.config_file)
        # neuer Dateiname:
        new_filename = "{}/{}-{}".format(dir_name, strftime("%Y%m%d%H%M%S"), os.path.basename(self.config_file))
        # kopieren!
        if self.log is not None:
            self.log.debug("copy config file to {} ...".format(new_filename))
        else:
            print("copy config file to {} ...".format(new_filename))
        try:
            shutil.copyfile(self.config_file, new_filename)
        except PermissionError:
            if self.log is not None:
                self.log.debug("write to {} ...permission error! Check file/directory permisions.".format(new_filename))
            else:
                print("write to {} ...permission error! Check file/directory permisions.".format(new_filename))
        #
        # jetzt die neue config über die alte kopieren
        #
        if self.log is not None:
            self.log.debug("copy new config file to {} ...".format(self.config_file))
        else:
            print("copy new config file to {} ...".format(self.config_file))
        try:
            shutil.copyfile(_new_file, self.config_file)
        except PermissionError:
            if self.log is not None:
                self.log.debug(
                    "write to {} ...permission error! Check file/directory permisions.".format(self.config_file))
            else:
                print("write to {} ...permission error! Check file/directory permisions.".format(self.config_file))
        #
        # lösche die alte "new" datei
        #
        if self.log is not None:
            self.log.debug("remove temporary new config file {} ...".format(_new_file))
        else:
            print("remove temporary new config file to {} ...".format(_new_file))
        try:
            os.remove(_new_file)
        except PermissionError:
            if self.log is not None:
                self.log.debug("write to {} ...permission error! Check file/directory permisions.".format(_new_file))
            else:
                print("write to {} ...permission error! Check file/directory permisions.".format(_new_file))
        #
        # hash und version setzen
        #
        self.dict_hash = self.__get_hashstr(self.config)
        return True

    @property
    def config_object(self):
        return self.config

    @property
    def config_hash(self):
        return self.dict_hash


def main():
    log = logging.getLogger("config_file_obj")
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(module)s: %(message)s", '%Y%m%d %H:%M:%S')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    c_fileobj = ConfigFileObj(log, config_file)
    #
    c_obj = c_fileobj.config_object

    for section_name in c_obj:
        log.debug("readout SECTION [{}]".format(section_name))
        items = c_obj[section_name]
        for itemname in items:
            log.debug(" [{}], '{}' = '{}'".format(section_name, itemname, items[itemname]))
    log.info("config ready.\n\n\n")
    sleep(1)

    log.info("try write without force...")
    c_fileobj.write_config_file()
    log.info("try write without force...OK")
    log.info("\n\n\n")
    sleep(3)

    log.info("try write without force after change...")
    c_obj['alert-01']['enable'] = 'false'
    c_fileobj.write_config_file()
    log.info("try write without force after change...OK")
    log.info("\n\n\n")
    sleep(3)

    log.info("try write with force after change...")
    c_obj['alert-01']['enable'] = 'true'
    c_fileobj.write_config_file()
    log.info("try write with force after change...OK")


if __name__ == '__main__':
    main()
