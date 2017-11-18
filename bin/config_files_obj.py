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
    config_lock = Lock()

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
            for item in items:
                name = item[0]
                val = item[1]
                if self.log is not None:
                    self.log.debug("  [{}] => '{}' = '{}'".format(section, name, val))
                else:
                    print("  [{}] => '{}' = '{}'".format(section, name, val))
                c_items[name] = val
            new_config[section] = c_items
        ConfigFileObj.config_lock.acquire()
        seclist = list(self.config.keys())
        for section in seclist:
            del self.config[section]
        for section in new_config:
            self.config[section] = new_config[section]
        v_items = dict()
        v_items['version'] = int(time())
        self.config['version'] = v_items
        ConfigFileObj.config_lock.release()
        return self.config

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
            ConfigFileObj.config_lock.acquire()
            curr_hash = self.__get_hashstr(self.config)
            ConfigFileObj.config_lock.release()
            if self.log is not None:
                self.log.info("HASH curr: {}".format(curr_hash))
                self.log.info("HASH orig: {}".format(self.dict_hash))
            if self.dict_hash == curr_hash:
                if self.log is not None:
                    self.log.debug("write_config_file...OK (not requiered)")
                return True
        #
        # configparser erzeugen zum schreiben in die datei
        #
        parser = ConfigParser()
        # das config-objekct wieder in ein parserobj konvertieren
        ConfigFileObj.config_lock.acquire()
        for section in sorted(self.config):
            if section == 'version':
                # version auslassen, nicht speichern
                continue
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
        ConfigFileObj.config_lock.release()
        #
        # eine neue Datei zum schreiben öffnen und schreiben
        #
        _new_file = "{}.new".format(self.config_file)
        if self.log is not None:
            self.log.debug("write to {} ...".format(_new_file))
        else:
            print("write to {} ...".format(_new_file))
        with open(_new_file, 'w') as configfile:
            parser.write(configfile)
        configfile.close()
        if self.log is not None:
            self.log.debug("write to {} ...OK".format(_new_file))
        else:
            print("write to {} ...OK".format(_new_file))
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
        shutil.copyfile(self.config_file, new_filename )
        #
        # jetzt die neue config über die alte kopieren
        #
        if self.log is not None:
            self.log.debug("copy new config file to {} ...".format(self.config_file))
        else:
            print("copy new config file to {} ...".format(self.config_file))
        shutil.copyfile(_new_file, self.config_file)
        #
        # lösche die alte "new" datei
        #
        if self.log is not None:
            self.log.debug("remove temporary new config file {} ...".format(_new_file))
        else:
            print("remove temporary new config file to {} ...".format(_new_file))
        os.remove(_new_file)
        #
        self.dict_hash = self.__get_hashstr(self.config)
        return True

    @property
    def config_object(self):
        return self.config


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
