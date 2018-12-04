#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import signal
import os
import re
from time import sleep, time
from config_files_obj import ConfigFileObj
from radio_alerts import RadioAlerts
from radio_command_server import RadioCommandServer
from soundtouch_play_object import SoundtouchPlayObject
from threading import Lock, Thread

__author__ = 'Dirk Marciniak'
__copyright__ = 'Copyright 2017'
__license__ = 'GPL'
__version__ = '0.1'

"""
Wecker-Daemon (für BOSE-Radio) zur Kontrolle der alert events und der Radios

Daemon zur Kommunikation mit den BOSE Radios und zur Steuerung
des Weckens

der Daemon lauscht via UDP socket auf Anforderungen von aussen (webserver) auf localhost
nach aussen gibt er Stati und Infos zurück. Eine direkte Steuerung der radios ist erst 
einmal nicht vorgesehen. 
einmal nicht vorgesehen.

Die Weckzeiten entnimmt der Daemon einer Config-Datei, die er zyklisch ausliest (oder
auf Benachrichtigung vom Webserver dass Änderungen gemacht wurden)

Ereignisse registriert er zunächst und gibt diese bei Anforerung an den Webserver

"""

config_file = "../config/alert.ini"


class SoundTouchAlertClock:
    DEFAULT_LOGFILE = "alert_clock.log"
    DEFAULT_LOGLEVEL = logging.DEBUG
    DEFAULT_CONFIGCHECK = 20
    DEFAULT_TIME_TO_FIND_DEVICES = 9000
    REGEX_ALERT = re.compile(r'^alert-\d{2}$')
    DEVICE_LOCK = Lock()
    DISCOVER_LOCK = Lock()
    ALERTS_LOCK = Lock()

    def __init__(self, _config_file: str):
        """
        Konstruktor für den Wecker daemon
        :param _config_file: Konfigurationsdatei
        """
        #
        # voreinstellungen initialisieren
        #
        self.log = None
        self.config_file = _config_file
        self.config_read_obj = None
        self.config = None
        self.config_modify_time = 0
        self.config_last_modify_time = 0
        self.console_log = False
        self.loglevel = SoundTouchAlertClock.DEFAULT_LOGLEVEL
        self.timezone = 'UTC'
        self.available_devices = dict()
        self.alert_in_progress = None
        self.timestamp_to_scan_devices = 0
        self.alerts = []
        self.udp_serverthread = None
        #
        # Konfiguration lesen
        #
        self.__configure_objects()
        self.log.info("instantiate SoundTouchAlertClock in {}...".format(__file__))
        self.is_running = True
        self.udp_serverthread = RadioCommandServer(self.log, self.config, self.__get_available_devices)
        self.udp_serverthread.set_new_config(self.config)
        self.udp_serverthread.start()
        self.udp_serverthread.set_on_config_change(self.__on_config_change)
        self.next_config_check = int(time())  # wann sol das nächste mal die Config getestet werden

    def __del__(self):
        if self.udp_serverthread is not None:
            self.udp_serverthread.clear_on_config_change()
            self.log.info("stop udp_serverthread")
            self.udp_serverthread.quit()
        if self.log is not None:
            self.log.info("delete SoundTouchAlertClock...")

    def quit_app(self):
        self.log.info("app should quit...")
        self.is_running = False

    def run(self):
        """
        Endlos, bis jemand das absagt...
        :return: nix
        """
        self.is_running = True
        self.log.info("daemon starting...")
        # wann sol das nächste mal die Config getestet werden
        # ....
        self.next_config_check = int(time()) + SoundTouchAlertClock.DEFAULT_CONFIGCHECK
        # die aktuelle zeit der letzten änderung merken
        self.config_last_modify_time = self.config_modify_time
        self.udp_serverthread.alert_working = 'none'
        self.alert_in_progress = None
        #
        while self.is_running:
            #
            # ist die letzte Änderug der Konfigurationsdatei neuer als die
            # hier gemerkte Änderungszeit?
            #
            if self.config_last_modify_time > self.config_modify_time:
                # Ok, da müsste was getan werden!
                self.log.info("config changes detected...")
                self.__configure_objects()
                self.config_last_modify_time = self.config_modify_time
                sleep(1)
                continue
            #
            # geräte neu finden? Nur wenn kein Alarm ackert
            #
            if int(time()) > self.timestamp_to_scan_devices and self.alert_in_progress is None:
                # Liste zu alt, erneuere sie, Discovering findet im System separat statt (externer Prozess)
                # setzte die zeit für das nächste mal...
                self.timestamp_to_scan_devices = int(time()) + SoundTouchAlertClock.DEFAULT_TIME_TO_FIND_DEVICES
                # der lock soll von der Threadfunktion selber gelöst werden
                d_thread = Thread(target=self.__find_available_devices)
                d_thread.start()
                continue
            #
            # ist irgend ein Alarm bereits am Ackern?
            #
            if self.alert_in_progress is not None:
                if not self.alert_in_progress.is_alive():
                    # ist er schon hinüber, entferne ihn
                    self.log.debug("remove stopped play thread...")
                    del self.alert_in_progress
                    self.alert_in_progress = None
                    self.udp_serverthread.alert_working = 'none'
                    continue
                if int(time()) > (self.alert_in_progress.time_to_off + 30):
                    # immer noch vorhanden, dann töte und beseitige das Teil
                    if self.alert_in_progress.is_alive():
                        self.log.info("kill play thread and join him while ending...")
                        self.alert_in_progress.device_is_playing = False
                        self.udp_serverthread.alert_working = 'none'
                        self.alert_in_progress.join()
                        self.log.debug("kill play thread ... OK, killed")
                    del self.alert_in_progress
                    self.alert_in_progress = None
                # auf jeden Fall schleife an den Anfang...
                continue
            #
            # jetzt schauen ob da was zu tun ist
            #
            if self.alert_in_progress is None:
                #
                # es läuft kein Alarm, also prüfe
                # ist ein Alarm vorhanden und ist einer in der nahen Zukunft?
                # (wenn ja, Radios suchen und testen ob verfügbar)
                #
                if SoundTouchAlertClock.ALERTS_LOCK.acquire(timeout=1.0):
                    for c_alert in self.alerts:
                        # alarm enable?
                        if not c_alert.alert_enabled:
                            # self.log.debug("alert {} is disabled. Continue...".format(c_alert.alert_note))
                            continue
                        # schaue ob ein alarm in X bis Y losgehen soll
                        time_to_alert = c_alert.sec_to_alert(0, 18)
                        if time_to_alert is not None and not c_alert.alert_prepeairing:
                            # der Alarm naht und ist noch nicht vorbereitet
                            # gib bescheid: wird vorbereitet
                            c_alert.alert_prepeairing = True
                            self.log.debug("alert in {} sec detected. process him...".format(time_to_alert))
                            # versuche eine Liste mit den Zielgeräten zu bekommen
                            alert_devices = self.__are_devices_available(c_alert.alert_devices)
                            if len(alert_devices) == 0:
                                # keine Gerätre gefunden => Alarm abblasen
                                self.log.fatal("no devices for playing alert found! Alert abort")
                                c_alert.alert_prepeairing = False
                                c_alert.alert_done = True
                                continue
                            # ok, geräte sind bereit
                            #
                            if c_alert.alert_working_timestamp > 0:
                                self.log.warning("this alert is working... not make an new alert this time")
                                continue
                            # erzeuge einen Weckerthread
                            self.alert_in_progress = SoundtouchPlayObject(self.log, self.__get_available_devices(), c_alert)
                            # markiere JETZT als Startzeitpunkt
                            c_alert.alert_working_timestamp = int(time())
                            c_alert.alert_thread = self.alert_in_progress
                            self.udp_serverthread.alert_working = c_alert.alert_alert
                            self.alert_in_progress.start()
                    SoundTouchAlertClock.ALERTS_LOCK.release()
                else:
                    self.log.crit("Can't lock ALERTS_LOCK! no checking alerts...") 
                # ende if
            else:
                # ein Alarm läuft, prüfe ob er beendet ist
                self.log.debug("alert is working...")
                pass
            #
            # und zuletzt: hat sich die Config Datei verändert?
            #
            if int(time()) > self.next_config_check and self.alert_in_progress is None:
                # self.log.debug("interval for check for config changes reached, check modify time...")
                # wann ist der nächste Check?
                self.next_config_check = int(time()) + SoundTouchAlertClock.DEFAULT_CONFIGCHECK
                # erfrage die Zeit der letzten Änderung der Konfigurationsdatei
                self.config_last_modify_time = self.__read_configfile_mod_time()
            sleep(.8)
        #
        # beendet
        #
        if self.udp_serverthread is not None:
            self.udp_serverthread.clear_on_config_change()
            self.log.info("stop udp_serverthread")
            self.udp_serverthread.quit()
            self.log.info("wait for ending udp-thread...")
            self.udp_serverthread.join()
            self.log.info("wait for ending udp-thread...OK")
            del self.udp_serverthread
            self.udp_serverthread = None
        self.log.info("daemon ending...")
        self.log.info("daemon ending...OK")
        # ENDE

    def __are_devices_available(self, _alert_devices_names: list):
        """
        Prüfe ob Geräte aus der Liste im Netzwerk sind
        :param _alert_devices_names: Liste mit Namen gewünschten Geräten
        :return: Liste der davon verfügbaren Geräte als SoundTouchDevice
        """
        avail_device_list = []
        for device_name in _alert_devices_names:
            device = self.__exist_device_in_network(device_name)
            if device is not None:
                avail_device_list.append(device)
        return avail_device_list

    def __find_available_devices(self):
        """
        Durchsuche das LAN nach BOSE Geräten
        :return: Anzahl gefundener Geräte
        """
        if not SoundTouchAlertClock.DISCOVER_LOCK.acquire(timeout=2.5):
            self.log.warning("CAn't lock DISCOVER_LOCK!")
            return
        try:
            self.log.info("start thread for search available soundtouch devices...")
            #
            # finde Geräte im Netzwerk
            #
            self.log.debug("thread discover soundtouch devices...")
            #
            # gibt es das config objekt (sollte es schon...)
            if self.config_read_obj is None:
            # neu anlegen
                self.config_read_obj = ConfigFileObj(self.log, self.config_file)
            # lese die Daten...
            _available_dev = self.config_read_obj.read_avail_devices()
            if SoundTouchAlertClock.DEVICE_LOCK.acquire(timeout=1.0):
              self.available_devices.clear()
              self.available_devices = _available_dev.copy()
              SoundTouchAlertClock.DEVICE_LOCK.release()
            self.log.info("start thread for search available soundtouch devices ends with {} found devices".format(
                len(self.available_devices)))
        finally:
            SoundTouchAlertClock.DISCOVER_LOCK.release()

    def __get_available_devices(self):
        """
        Gib kopie einer Liste mit verfügbaten Geräte zurück, sofern vorhanden
        :return:
        """
        if SoundTouchAlertClock.DEVICE_LOCK.acquire(timeout=1.0):
            _cp_list = self.available_devices.copy()
            SoundTouchAlertClock.DEVICE_LOCK.release()
            return _cp_list
        else:
            self.log.warnung("Can't lock DEVICE_LOCK! (get availible devices...)")

    def __exist_device_in_network(self, _name_to_find: str):
        """
        Gib das Gerät mit dem Namen XXX als Geräteobjekt zurück, falls vorhanden
        :param _name_to_find: Name des Gerätes
        :return: Geräteobjekt oder None
        """
        # aktuelle Liste existiert
        # Pattern für Vergleich compilieren
        match_pattern = re.compile('^' + _name_to_find + '$', re.IGNORECASE)
        # finde raus ob es das gerät gibt
        if SoundTouchAlertClock.DEVICE_LOCK.acquire(timeout=1.0):
            for devname, device in self.available_devices.items():
                self.log.debug("exist device {} in discovered devices: {}, Type: {}, host: {}".format(_name_to_find,
                                                                                                    device['name'],
                                                                                                    device['type'],
                                                                                                    device['host']))
                if re.match(match_pattern, devname):
                    self.log.debug("destination device found!")
                    SoundTouchAlertClock.DEVICE_LOCK.release()
                    return device
            self.log.debug("destination device NOT found!")
            SoundTouchAlertClock.DEVICE_LOCK.release()
        else:
            self.log.warning("Can't lock DECICE_LOCK! (esist devices in network)")
        return None

    def __on_config_change(self, _timestamp: int):
        """
        Callback, dass die Config geändert wurde
        :param _timestamp:
        """
        self.log.info("callback: config was changed, comes from udp-server...")
        # nächster Check auf Änderugnen später...
        self.next_config_check = int(time()) + SoundTouchAlertClock.DEFAULT_CONFIGCHECK
        if self.config_read_obj is not None:
            self.log.debug("initiate write config to file...")
            self.config_read_obj.write_config_file()
            sleep(.3)
        # zeitstempel der geänderten Datei setzten, sonst liest er das nochmal ein
        # und die Zeit lokale merken
        self.config_last_modify_time = self.__read_configfile_mod_time()
        self.config_last_modify_time = self.config_modify_time
        #######################################################################
        # Alarme neu aus der configuration im RAM einlesen                    #
        #######################################################################
        if not SoundTouchAlertClock.ALERTS_LOCK.acquire(timeout=2.5):
            self.log.warning("Can't lock ALERTS_LOCK! (on config change)")
            return
        # alle alarme entfernen
        self.alerts.clear()
        SoundTouchAlertClock.ALERTS_LOCK.release()
        # und nun neu einlesen
        if ConfigFileObj.CONFIG_LOCK.acquire(timeout=1.0):
            for section in self.config:
                # lies nur die alert-xx Einträge
                if not SoundTouchAlertClock.REGEX_ALERT.match(section):
                    continue
                # es ist ein alert...
                self.log.debug("create RadioAlerts {}...".format(section))
                ConfigFileObj.CONFIG_LOCK.release()
                alert = RadioAlerts(self.log, self.config[section], section)
                ConfigFileObj.CONFIG_LOCK.acquire()
                SoundTouchAlertClock.ALERTS_LOCK.acquire()
                self.alerts.append(alert)
                SoundTouchAlertClock.ALERTS_LOCK.release()
                self.log.debug("create RadioAlerts {}...OK".format(section))
            ConfigFileObj.CONFIG_LOCK.release()
        else:
            self.log.warning("Can't lock ALERTS_LOCK! ()on config change)")

    def reload_conifg(self):
        """
        Konfiguration via SIGNAL USR1 reload (wenn der Webserver was gemacht hat)
        :return: nix
        """
        if self.is_running:
            self.__configure_objects()
        return None

    def __read_configfile_mod_time(self):
        """
        speichere die letzte bearbeitungszeit der Konfiguration
        :return: die Zeit
        """
        # merke mir die Bearbeitungszeit
        fileinfo = os.stat(self.config_file)
        modify_time = fileinfo.st_mtime
        return modify_time

    def __configure_objects(self):
        """
        Konfiguriere das Programm und die Objekte
        :return: None
        """
        # merke mir die Bearbeitungszeit
        self.config_modify_time = self.__read_configfile_mod_time()
        if self.config_read_obj is None:
            self.config_read_obj = ConfigFileObj(self.log, self.config_file)
        else:
            self.config_read_obj.read_configfile(self.config_file)
        self.config = self.config_read_obj.config_object
        # falls ein UDB-Thread existiert
        if self.udp_serverthread is not None:
            self.udp_serverthread.set_new_config(self.config)
        #ConfigFileObj.CONFIG_LOCK.acquire()
        #######################################################################
        # DEFAULT                                                             #
        #######################################################################
        # Loglevel
        level = self.config['global']['loglevel']
        if level == 'debug':
            self.loglevel = logging.DEBUG
        elif level == 'info':
            self.loglevel = logging.INFO
        elif level == 'warning':
            self.loglevel = logging.WARN
        elif level == 'error':
            self.loglevel = logging.ERROR
        elif level == 'critical':
            self.loglevel = logging.CRITICAL
        else:
            self.loglevel = logging.INFO
        print("CONFIG %20s: %s" % ('loglevel', level))
        # Logfile
        logfile = self.config['global']['logfile']
        print("CONFIG %20s: %s" % ('logfile', logfile))
        # Log auch auf die Konsole?
        console_log = self.str2bool(self.config['global']['console_log'])
        print("CONFIG %20s: %s" % ('console log', console_log))
        if self.log is None or self.logfile is None:
            # noch kein logger vorhanden
            self.logfile = logfile
            self.console_log = console_log
            self.log = self.__make_logger(self.logfile, self.loglevel, self.console_log)
        elif self.logfile is not None and (self.logfile != logfile or self.console_log != console_log):
            # da ist ein alter Logger, der neu gemacht werden muss
            del self.log
            # neu machen
            self.logfile = logfile
            self.console_log = console_log
            self.log = self.__make_logger(self.logfile, self.loglevel, self.console_log)
        else:
            self.log.setLevel(self.loglevel)
        # Zeitzohne
        self.timezone = self.config['global']['timezone']
        print("CONFIG %20s: %s" % ('timezone', console_log))
        #######################################################################
        # Alarme einlesen                                                     #
        #######################################################################
        if SoundTouchAlertClock.ALERTS_LOCK.acquire(timeout=1.0):
            self.alerts.clear()
            for section in self.config:
                if not SoundTouchAlertClock.REGEX_ALERT.match(section):
                    continue
                # es ist ein alert...
                self.log.debug("create RadioAlerts {}...".format(section))
                alert = RadioAlerts(self.log, self.config[section], section)
                if ConfigFileObj.CONFIG_LOCK.acquire(timeout=1.0):
                    self.alerts.append(alert)
                    ConfigFileObj.CONFIG_LOCK.release()
                else:
                    self.log.warning("Can't lock CONFIG_LOCK (config alert objects)")
                self.log.debug("create RadioAlerts {}...OK".format(section))
            SoundTouchAlertClock.ALERTS_LOCK.release()
        else:
            self.log.warning("Can't lock ALERTS_LOCK! (config alert objects) ")
        # ENDE

    @staticmethod
    def str2bool(_val: str):
        return _val.lower() in ('yes', 'true', 't', '1')

    @staticmethod
    def __make_logger(_logfile: str, _my_loglevel, _console_log: bool):
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
        if _console_log:
            c_handler = logging.StreamHandler()
            c_handler.setFormatter(formatter)
            log.addHandler(c_handler)
        f_handler.setFormatter(formatter)
        log.addHandler(f_handler)
        return log


def main():
    """Hauptprogramm"""
    a_clock = SoundTouchAlertClock(config_file)
    print("init signalhandler for SIGINT...")
    signal.signal(signal.SIGINT, lambda sig, frame: a_clock.quit_app())
    a_clock.run()
    del a_clock
    print("daemon endet...")


if __name__ == '__main__':
    main()
