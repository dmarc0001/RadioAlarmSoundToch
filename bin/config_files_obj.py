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
from threading import Lock

config_file = '../config/alert.ini'


class ConfigFileObj:
    enclosing_dquotes = re.compile(r"(^\"|\"$)")
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
            c_items = dict()
            for item in items:
                name = item[0]
                val = item[1]
                #val = re.sub(ConfigFileObj.enclosing_dquotes, "", item[1])
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
        ConfigFileObj.config_lock.release()
        return self.config

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
            self.log.debug("write_config_file...")
        else:
            print("write_config_file...")
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
            if self.log is not None:
                self.log.debug("create section [{}]...".format(section))
            else:
                print("create section [{}]...".format(section))
            parser[section] = self.config[section]
        ConfigFileObj.config_lock.release()
        #
        # datei schreiben, zuerst alte umbenennen
        #
        dir_name = os.path.dirname(self.config_file)
        new_filename = "{}/{}-{}".format(dir_name, strftime("%Y%m%d%H%M%S"), os.path.basename(self.config_file))
        if self.log is not None:
            self.log.debug("rename config file to {} ...".format(new_filename))
        else:
            print("rename config file to {} ...".format(new_filename))
        os.rename(self.config_file, new_filename)
        if self.log is not None:
            self.log.debug("rename config file to {} ...OK".format(new_filename))
        else:
            print("rename config file to {} ...OK".format(new_filename))
        #
        # eine Datei zum schreiben öffnen
        #
        if self.log is not None:
            self.log.debug("write to {} ...".format(self.config_file))
        else:
            print("write to {} ...".format(self.config_file))
        with open(self.config_file, 'w') as configfile:
            parser.write(configfile)
        configfile.close()
        if self.log is not None:
            self.log.debug("write to {} ...OK".format(self.config_file))
        else:
            print("write to {} ...OK".format(self.config_file))
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
