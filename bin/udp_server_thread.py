#!/usr/bin/python3
# -*- coding: utf-8 -*-
#

from time import sleep, time
from threading import Thread, Lock
import logging
import logging.handlers
import signal
import re
import socket
import json
from config_files_obj import ConfigFileObj

"""
Modul implementiert einen UDP Server welcher auf einem Port auf Verbindungen lauscht unf Kommandos 
entgegennimmt.

Zweck ist es, vom Webserver (dessen scripten) Anfragen zu empfangen und darauf zu antworten

Dies stellt eine Schnitstelle zwischen Webserver und Soundsystem dar.

TODO: Die Konfiguration sollte vom Webserver hier ausgelesen werden 
"""


class RadioCommandServer(Thread):
    """
    Objekt zur Kommunikation zwischen den Programmen des Webserver und dem Daeomon für die Radios
    """

    def __init__(self, _log: logging.Logger, _config: dict = None, _devices_callback = None ):
        """
        Der Konstruktor des Thread
        :param _log: logobjekt
        :param _config das Config Objekt
        """
        Thread.__init__(self)
        self.lock = Lock()
        self.log = _log
        self.config = _config
        self.available_devices_callback = _devices_callback
        self.s_socket = None
        self.on_config_change = None
        self.is_running = False
        # self.is_socket_usable = True
        self.log.debug("instantiate RadioCommandServer...")

    def __del__(self):
        """
        Der Destruktor des Thread, aufräumarbeiten
        :return: None
        """
        self.log.debug("thread destructor...")
        self.log.debug("thread destructor...OK")

    def set_on_config_change(self, callback):
        """
        Setzte Callback bei veränderungen der Konfiguration
        :param callback: Funktion für den Rückruf
        """
        self.on_config_change = callback

    def clear_on_config_change(self):
        """
        Lösche den Rückruf bei Konfigänderungen
        """
        self.on_config_change = None

    def run(self):
        """
        die (überladene) Hauptroutine des Threads, läuft bis jemand das anders entscheidet
        :return: None
        """
        self.is_running = True
        # erzeuge Socket oder beende den Thread
        self.log.debug("udp thread start running...")
        self.__make_udp_socket()
        #
        # ab ins Vergnügen, wenn ein socket da ist
        #
        while self.is_running:
            # if self.is_socket_usable:
            # erwarte Datenpakete
            try:
                # maximal 4 k Daten empfangen
                data, address = self.s_socket.recvfrom(4096)
                self.log.debug("recived {} bytes from {}".format(len(data), address))
                if not self.is_running:
                    break;
                #
                if data:
                    response = self.__commandparser(data)
                    if not self.is_running:
                        break;
                    # TODO: sent_count prüfen
                    sent_count = self.s_socket.sendto(response, address)
                    self.log.debug("send echo to {}".format(address))
            except socket.timeout:
                if not self.is_running:
                    break;
                pass
            sleep(.6)
        self.on_config_change = None
        self.__clear_udp_socket()
        self.log.debug("udp thread stop running...")

    def quit(self):
        """
        Gibt von aussen die Anweisung den Thread zu beenden
        :return:
        """
        # TODO: callbacks löschen
        self.is_running = False
        self.clear_on_config_change()

    def __commandparser(self, data):
        """
        Parse Kommando und gib Antwort als Binary String
        data: binary String
        """
        # zum bearbeiten einen String daraus machen
        cmdstr = data.decode('utf-8')
        self.log.info("cmd: %s" % cmdstr)
        # json parsen und Objekt daraus machen
        cmd = json.loads(cmdstr)
        #
        # ist es ein GET Kommando?
        #
        if 'get' in cmd:
            self.log.debug("get cmd recognized...")
            return self.__get_cmd_parse(cmd['get'])
        elif 'set' in cmd:
            self.log.debug("get cmd recognized...")
            return self.__set_cmd_parse(cmd['set'])
        else:
            self.log.warning("unknown command recived!")
            return json.dumps({'error': 'unknown command or not implemented yet'}).encode(encoding='utf-8')
            # ENDE __commandparser

    def __get_cmd_parse(self, _cmd: dict):
        """
        Ein GET Kommando empfangen, hier bearbeiten
        :param _cmd: JSON
        :return:
        """
        _answers = dict()
        match_pattern = re.compile('^alert-\d{2}$', re.IGNORECASE)
        # TODO: Was wurde gefragt? hier erst mal alles zurück geben
        for sitem in _cmd:
            #
            # welche Anforderung war es
            #
            if 'config' in sitem:
                # bei all geht es schnell
                response = None
                try:
                    ConfigFileObj.config_lock.acquire()
                    response = json.dumps(self.config).encode(encoding='utf-8')
                finally:
                    ConfigFileObj.config_lock.release()
                    return response
            elif 'all' in sitem:
                # bei all nur die alarme, nicht global
                ConfigFileObj.config_lock.acquire()
                for section in self.config:
                    if re.match(match_pattern, section):
                        if self.config[section] is not None:
                            _answers[section] = self.config[section]
                ConfigFileObj.config_lock.release()
                # Alle verfügbaren eingefügt
            elif 'devices' in sitem:
                # alle verfügbaren Geräte finden und melden
                _devices = self.available_devices_callback()
                if _devices is not None:
                    for device in _devices:
                        # für jedes Gerät einen Datensatz machen
                        dev_info = dict()
                        dev_info['name'] = device.config.name
                        dev_info['type'] = device.config.type
                        dev_info['host'] = device.host
                        _answers[device.config.name] = dev_info
                    del _devices
            elif re.match(match_pattern, sitem):
                # passt in das Muster
                self.log.debug("*** found: {} ***".format(sitem))
                ConfigFileObj.config_lock.acquire()
                if self.config[sitem] is not None:
                    self.log.debug("*** add: {} ***".format(sitem))
                    _answers[sitem] = self.config[sitem]
                ConfigFileObj.config_lock.release()
            else:
                self.log.warning("get command not implemented or none alerts match request")
                return json.dumps({'error': 'get command not implemented or none alerts match request'}).encode(encoding='utf-8')
        # ende alle Kommandoeinträge
        # jetz Ergebnis zurück schicken
        return json.dumps(_answers).encode(encoding='utf-8')

    def __set_cmd_parse(self, _cmd: dict):
        """
        Ein SET Kommando empfangen, hier bearbeiten
        :param _cmd: das Kommando als JSON Objekt
        :return:
        """
        is_successful = True
        for sitem in _cmd:
            #
            # alle sets durch
            # {"set":[{"alert":"alert-04","enable":"true"}, {"alert":"alert-03","enable":"true"}]}
            #
            alert_name = sitem['alert']
            self.log.debug("found alert {} with set commands".format(alert_name))
            #
            # nun alle Eigenschaften durch
            #
            for al_command in sitem:
                if al_command == 'alert':
                    continue
                if al_command == 'enable':
                    # einen alarm erlauben oder verbieten
                    self.log.debug( "change enable state for alert {} to {}".format(alert_name, sitem[al_command]))
                    ConfigFileObj.config_lock.acquire()
                    self.config[alert_name][al_command] = sitem[al_command]
                    ConfigFileObj.config_lock.release()
                else:
                    self.log.warning("set al_command {} not implemented yet".format(al_command))
                    return json.dumps({'error': 'unknown set al_command {}...'.format(al_command)}).encode(encoding='utf-8')
            # ende der kommandos per alarm
        # ende der alarme
        if is_successful:
            # es scheint alles geklappt zu haben
            self.log.debug("set command for alarm(s) successful!")
            if self.on_config_change is not None:
                self.on_config_change(int(time()))
            return json.dumps({'ok': 'sucsessful commands done'}).encode(encoding='utf-8')
        else:
            # etwas lief schief
            self.log.warning("an error has occurred")
            return json.dumps({'error': 'an error has occurred'}).encode(encoding='utf-8')
        # ENDE __set_cmd_parse

    def __make_udp_socket(self):
        """
        erzeuge den UDP Socket für den Thread
        :return:
        """
        # Guck mal ob das passt
        ConfigFileObj.config_lock.acquire()
        if int(self.config['global']['server_port']) < 1024:
            self.log.error("not an valid port configured, no udp server startet! Program end...")
            self.is_running = False
            ConfigFileObj.config_lock.release()
            return False
        else:
            self.log.debug("UDP server on addr: %s:%s" % (
                self.config['global']['server_addr'], self.config['global']['server_port']))
            self.log.info("try to make udp server socket...")
            try:
                self.s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                bind_addr = (self.config['global']['server_addr'], int(self.config['global']['server_port']))
                self.s_socket.bind(bind_addr)
                self.s_socket.settimeout(1)
            except OSError as msg:
                self.log.fatal("exception while socket binding: %s, ABORT!" % msg)
                self.is_running = False
                ConfigFileObj.config_lock.release()
                return False
            self.log.info("try to make udp server socket...OK")
            ConfigFileObj.config_lock.release()
            return True
            # fertig

    def __clear_udp_socket(self):
        """
        Lösche den Socket...
        :return:
        """
        if self.s_socket is not None:
            try:
                self.log.debug("close udp socket...")
                self.s_socket.close()
                self.s_socket = None
            finally:
                self.log.debug("close udp socket...OK")
        return None


def main():
    log = logging.getLogger("udpServer")
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(module)s: %(message)s", '%Y%m%d %H:%M:%S')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    from config_files_obj import ConfigFileObj
    #
    # config
    #
    cf_ob = ConfigFileObj(log, '../config/alert.ini')
    alerts = cf_ob.config_object
    s_thread = RadioCommandServer(log, alerts)
    signal.signal(signal.SIGINT, lambda sig, frame: s_thread.quit())
    s_thread.start()
    log.info("wait for thread end...")
    s_thread.join()


if __name__ == '__main__':
    main()
