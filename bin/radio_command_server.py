#!/usr/bin/python3
# -*- coding: utf-8 -*-
#

from time import sleep, time
from threading import Thread, Lock
import logging
import logging.handlers
import hashlib
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

    def __init__(self, _log: logging.Logger, _config: dict = None, _devices_callback=None):
        """
        Der Konstruktor des Thread
        :param _log: logobjekt
        :param _config das Config Objekt
        """
        Thread.__init__(self)
        self.command_lock = Lock()
        self.log = _log
        self.config = _config
        self.available_devices_callback = _devices_callback
        self.s_socket = None
        self.on_config_change = None
        self.is_running = False
        self.config_hash = dict()
        self.config_hash['version'] = self.__get_hashstr(self.config)
        # self.is_socket_usable = True
        self.log.debug("instantiate RadioCommandServer...")

    def __del__(self):
        """
        Der Destruktor des Thread, aufräumarbeiten
        :return: None
        """
        self.log.debug("thread destructor...")
        self.log.debug("thread destructor...OK")

    def set_new_config(self, _config: dict ):
        """
        übergibt eine neue, neu eingelesene Konfiguration
        :param _config: Konfig-Objekt
        :return:
        """
        self.config = _config
        self.config_hash['version'] = self.__get_hashstr(self.config)

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
                    # den Teil hier schützen
                    self.command_lock.acquire()
                    response = self.__commandparser(data)
                    if not self.is_running:
                        # schutz beenden
                        self.command_lock.release()
                        break;
                    sent_count = self.s_socket.sendto(response, address)
                    # Schutz beenden
                    self.command_lock.release()
                    self.log.debug("send echo to {}, {} bytes...".format(address, sent_count))
                    # Warnung wenn das nicht so hinhaut
                    if sent_count != len(response):
                        self.log.warning("there is an difference in lenght between to sent data and sendet data! " +
                                         "to send: {} bytes, sendet: {} bytes".format(len(response), sent_count))
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
        self.is_running = False
        # lösche callbacks
        self.clear_on_config_change()

    def __commandparser(self, data):
        """
        Parse Kommando und gib Antwort als Binary String
        :data binary String
        :return binary string
        """
        # zum bearbeiten einen String daraus machen
        cmdstr = data.decode('utf-8')
        self.log.debug("cmd: %s" % cmdstr)
        # json parsen und dictonary Objekt daraus machen
        cmd = json.loads(cmdstr)
        #
        # ist es ein GET Kommando?
        #
        if 'get' in cmd:
            self.log.debug("get cmd recognized...")
            return self.__get_cmd_parse(cmd['get'])
        elif 'set' in cmd:
            self.log.debug("set cmd recognized...")
            return self.__set_cmd_parse(cmd['set'])
        elif 'delete' in cmd:
            self.log.debug("DELETE cmd recognized...")
            return self.__delete_cmd_parse(cmd['delete'])
        else:
            self.log.warning("unknown command recived! Data: <{}>".format(cmdstr))
            return json.dumps({'error': 'unknown command or not implemented yet'}).encode(encoding='utf-8')
            # ENDE __commandparser

    def __get_cmd_parse(self, _cmd: dict):
        """
        Ein GET Kommando empfangen, hier bearbeiten
        :param _cmd: ein dictonary mit Daten
        :return binary string (JSON)
        """
        _answers = dict()
        match_pattern = re.compile('^alert-\d{2}$', re.IGNORECASE)
        for sitem in _cmd:
            #
            # welche Anforderung war es
            #
            if 'config-id' in sitem:
                # welche version der CONFIG liegt vor (Änderung???)
                ConfigFileObj.config_lock.acquire()
                response = json.dumps(self.config_hash).encode(encoding='utf-8')
                ConfigFileObj.config_lock.release()
                return response
            elif 'config' in sitem:
                # Alarm und der Rest Konfiguration
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
                    for devname, device in _devices.items():
                        # für jedes Gerät einen Datensatz machen
                        dev_info = dict()
                        dev_info['name'] = device['name']
                        dev_info['type'] = device['type']
                        dev_info['host'] = device['host']
                        _answers[devname] = dev_info
                    del _devices
            elif 'new' in sitem:
                # neuen Eintrag vorbereiten
                self.log.info("get a NEW alert config")
                new_item = ConfigFileObj.get_empty_configitem()
                alert_num = self.__get_free_alert_number()
                if alert_num is None:
                    self.log.error("get new config item failed, not free alert number found!")
                    return json.dumps({'error': 'get new config item failed, not free alertnumber found!'}).encode(
                        encoding='utf-8')
                #
                # erzeuge neuen Eintrag in der Config
                #
                alert_name = "alert-{num:02d}".format(num=alert_num)
                # keinen Namen vergeben
                del new_item['note']
                # einen neuen, sonst nicht genutzten Eintrag
                new_item['new-alert'] = alert_name
                # NULL vermeiden (wg. JavaScripts in der GUI)
                new_item['date'] = " "
                new_item['devices'] = " "
                # der Name des Eintrages:
                _answers["new"] = new_item
            elif re.match(match_pattern, sitem):
                # passt in das Muster (alle "sonstigen" alarme)
                ConfigFileObj.config_lock.acquire()
                try:
                    if self.config[sitem] is not None:
                        self.log.debug("add: {} to config" .format(sitem))
                        _answers[sitem] = self.config[sitem]
                except KeyError:
                    self.log.error("unknown (new?) alert to ask: {}".format(sitem))
                    self.config_hash['version'] = self.__get_hashstr(self.config)
                finally:
                    ConfigFileObj.config_lock.release()
            else:
                self.log.warning("get command not implemented or none alerts match request. Data: <{}>".format(sitem))
                return json.dumps({'error': 'get command not implemented or none alerts match request'}).encode(
                    encoding='utf-8')
        # ende alle Kommandoeinträge
        # jetz Ergebnis zurück schicken
        return json.dumps(_answers).encode(encoding='utf-8')

    def __set_cmd_parse(self, _cmd: dict):
        """
        Ein SET Kommando empfangen, hier bearbeiten
        :param _cmd: das Kommando als JSON Objekt
        :return:
        """
        for sitem in _cmd:
            #
            # alle sets durch
            # {"set":[{"alert":"alert-04","enable":"true", ...}, {"alert":"alert-03","enable":"true", ...}]}
            #
            alert_name = sitem['alert']
            if alert_name not in self.config:
                # da ist ein NEUNER Alarm angekommen == NEW
                self.log.debug("found NEW alert {} with set commands".format(alert_name))
                _alert = ConfigFileObj.get_empty_configitem()
                ConfigFileObj.config_lock.acquire()
                self.config[alert_name] = _alert
                ConfigFileObj.config_lock.release()
            else:
                # EDIT Alarm
                self.log.debug("found alert {} with set commands".format(alert_name))
            #
            # nun alle Eigenschaften durch
            #
            ConfigFileObj.config_lock.acquire()
            for set_command in sitem:
                if set_command == 'alert':
                    continue
                # eine  Einstellung schreiben
                self.log.debug("set property {} to {} for alert {}".format(set_command, sitem[set_command], alert_name))
                if sitem[set_command] == 'null':
                    self.config[alert_name][set_command] = " "
                else:
                    self.config[alert_name][set_command] = sitem[set_command]
            ConfigFileObj.config_lock.release()
            # ende der kommandos per alarm
        # ende der alarme
        # es scheint alles geklappt zu haben
        # noch schnell den aktuellen hashwert berechnen (besser als version)
        self.config_hash['version'] = self.__get_hashstr(self.config)
        self.log.debug("set command for alert(s) successful!")
        # callback, wenn erforderlich
        if self.on_config_change is not None:
            self.log.debug("call on_config_change...")
            self.on_config_change(int(time()))
        return json.dumps({'ok': 'sucsessful commands done'}).encode(encoding='utf-8')
        # ENDE __set_cmd_parse

    def __get_free_alert_number(self):
        """
        suche die nächste freie Alarmnummer fur neuen alarm
        :return:
        """
        exist_alerts = dict()
        # alle existierenden in ein dict
        for section in self.config:
            exist_alerts[section] = True
        #
        # jetzt das erste finden, welches NICHT existiert
        #
        for idx in range(1, 99):
            alert_num = "alert-{num:02d}".format(num=idx)
            # ist der key noch nicht vorhanden?
            if alert_num not in exist_alerts:
                # der ist noch frei
                return idx
        return None

    def __delete_cmd_parse(self, _cmd: dict):
        """
        Ein DELETE Kommando empfangen, hier bearbeiten
        :param _cmd: das Kommando als dictonary Objekt
        :return: ergebnis als JSON binary string
        """
        for sitem in _cmd:
            #
            # alle sets durch
            # {"delete":[{"alert":"alert-04"}]}
            #
            alert_name = sitem['alert']
            self.log.debug("found alert {} with DELETE command".format(alert_name))
            if alert_name in self.config:
                ConfigFileObj.config_lock.acquire()
                del self.config[alert_name]
                ConfigFileObj.config_lock.release()
                self.config_hash['version'] = self.__get_hashstr(self.config)
                if self.on_config_change is not None:
                    self.on_config_change(int(time()))
                return json.dumps({'ok': "alert {} is deleted in config...".format(alert_name)}).encode(
                    encoding='utf-8')
            else:
                self.log.fatal("to delete alert {} is not found in config...".format(alert_name))
                return json.dumps({'error': "to delete alert {} is not found in config...".format(alert_name)}).encode(
                    encoding='utf-8')
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
