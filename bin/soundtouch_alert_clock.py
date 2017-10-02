#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import signal
import os
from time import sleep, time
import re
from config_files_obj import ConfigFileObj
from radio_alerts import RadioAlerts
from udp_server_thread import RadioCommandServer
from libsoundtouch import discover_devices

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

Die Weckzeiten entnimmt der Daemon einer Config-Datei, die er zyklisch ausliest (oder
auf Benachrichtigung vom Webserver dass Änderungen gemacht wurden)

Ereignisse registriert er zunächst und gibt diese bei Anforerung an den Webserver

"""

config_file = "../config/alert.ini"


class SoundTouchAlertClock:
    DEFAULT_LOGFILE = "alert_clock.log"
    DEFAULT_LOGLEVEL = logging.DEBUG
    DEFAULT_CONFIGCHECK = 20

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
        self.current_config_modify_time = 0
        self.console_log = False
        self.loglevel = SoundTouchAlertClock.DEFAULT_LOGLEVEL
        self.timezone = 'UTC'
        self.available_devices = []
        self.alert_in_progress = None
        self.available_devices_timestamp = 0
        self.alerts = []
        self.udp_serverthread = None
        #
        # Konfiguration lesen
        #
        self.__configure_objects()
        self.log.info("instantiate SoundTouchAlertClock in {}...".format(__file__))
        self.is_running = True
        self.udp_serverthread = RadioCommandServer(self.log, self.config)
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
        self.current_config_modify_time = self.config_modify_time
        #
        while self.is_running:
            #
            # konfig neu testen?
            #
            if self.current_config_modify_time > self.config_modify_time:
                # Ok, da müsste was getan werden!
                self.log.info("config changes detected...")
                self.__configure_objects()
                self.current_config_modify_time = self.config_modify_time
                sleep(1)
            if self.alert_in_progress is None:
                # es läuft kein Alarm, also prüfe
                # ist ein Alarm vorhanden und ist einer in der nahen Zukunft?
                # (wenn ja, Radios suchen und testen ob verfügbar)
                #
                for c_alert in self.alerts:
                    # wiel lange / kein Alarm
                    time_to_alert = c_alert.sec_to_alert(3, 10)
                    if time_to_alert is not None and not c_alert.alert_prepeairing():
                        # der Alarm naht und ist noch nicht vorbereitet
                        # gib bescheid: wird vorbereitet
                        c_alert.alert_prepeairing(True)
                        self.log.debug("alert in {} sec detected".format(time_to_alert))
                        # versuche eine Liste mit den Zielgeräten zu bekommen
                        alert_devices = self.__are_devices_availvible(c_alert.alert_devices)
                        if len(alert_devices) == 0:
                            # keine Gerätre gefunden => Alarm abblasen
                            self.log.fatal("no devices for playing alert found! Alert abort")
                            c_alert.alert_prepeairing(False)
                            c_alert.alert_done(True)
                            continue
                        # ok, geräte sind bereit
                        #
            else:
                # ein Alarm läuft, prüfe ob er beendet ist
                pass
            #
            # und zuletzt: hat sich die Config Datei verändert?
            #
            if int(time()) > self.next_config_check:
                self.log.debug("interval for check for config changes reached, check modify time...")
                self.next_config_check = int(time()) + SoundTouchAlertClock.DEFAULT_CONFIGCHECK
                # check mal, ob sich die Modify Zeit des Configfiles verändert hat
                self.current_config_modify_time = self.__read_mod_time()
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

    def __are_devices_availvible(self, _alert_devices: list):
        """
        Prüfe ob Geräte aus der Liste im Netzwerk sind
        :param _alert_devices: Liste mit Namen gewünschten Geräten
        :return: Liste der davon verfügbaren Geräte als SoundTouchDevice
        """
        avail_list = []
        for device in _alert_devices:
            if self.__exist_device_in_network(device):
                avail_list.append(device)
        return avail_list

    def __find_available_devices(self):
        """
        Durchsuche das LAN nach BOSE Geräten
        :return: Anzahl gefundener Geräte
        """
        self.log.debug("search available al_devices")
        # alle eventuell vorhandenen löschen
        self.available_devices.clear()
        #
        # finde Geräte im Netzwerk
        #
        self.available_devices = discover_devices(timeout=3)  # Default timeout is 5 seconds
        self.available_devices_timestamp = int(time())
        return len(self.available_devices)

    def __exist_device_in_network(self, _to_find: str):
        """
        Gib das Gerät mit dem Namen XXX als Geräteobjekt zurück, falls vorhanden
        :param _to_find: Name des Gerätes
        :return: GEräteobjekt oder None
        """
        if self.available_devices_timestamp + 300 < int(time()):
            # Liste zu alt, erneuere sie
            if self.__find_available_devices() == 0:
                # keine Geräte, dann ist hier ENDE GeLÄNDE
                return False
        # aktuelle Liste existiert
        # Pattern für Verglcih compilieren
        match_pattern = re.compile('^' + _to_find + '$', re.IGNORECASE)
        # finde raus ob es das gerät gibt
        for device in self.available_devices:
            self.log.debug("discovered device: {}, Type: {}, host: {}".format(device.config.name, device.config.type,
                                                                              device.host))
            if re.match(match_pattern, device.config.name):
                self.log.debug("destination device found!")
                return device
        return None

    def __on_config_change(self, _timestamp: int):
        """
        Callback, dass die Config geändert wurde
        :param _timestamp:
        """
        self.log.info("config from command changed, write to file...")
        if self.config_read_obj is not None:
            self.config_read_obj.write_config_file()
        # zeitstempel setzten, sonst liest er das nochmal ein
        self.config_modify_time = self.__read_mod_time()
        self.current_config_modify_time = self.config_modify_time

    def reload_conifg(self):
        """
        Konfiguration via SIGNAL USR1 reload (wenn der Webserver was gemacht hat)
        :return: nix
        """
        if self.is_running:
            self.__configure_objects()
        return None

    def __read_mod_time(self):
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
        self.config_modify_time = self.__read_mod_time()
        if self.config_read_obj is None:
            self.config_read_obj = ConfigFileObj(self.log, self.config_file)
        else:
            self.config_read_obj.read_configfile(self.config_file)
        self.config = self.config_read_obj.config_object
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
        self.alerts.clear()
        regex_alert = re.compile(r'^alert-\d{2}$')
        for section in self.config:
            if not regex_alert.match(section):
                continue
            # es ist ein alert...
            self.log.debug("create RadioAlerts {}...".format(section))
            alert = RadioAlerts(self.log, self.config[section])
            self.alerts.append(alert)
            self.log.debug("create RadioAlerts {}...OK".format(section))
        #
        # thread mit neuer config versorgen
        #
        if self.udp_serverthread is not None:
            self.udp_serverthread.set_config(self.config)
        # ENDE

    @staticmethod
    def str2bool(_val: str):
        return _val.lower() in ('yes', 'true', 't', '1')

    def volume_listener(self, volume):
        """
        Lautstärke geändert
        :param volume: neue Lautstärke
        """
        self.log.debug("change volume to: {} mute: {}".format(volume.actual, volume.muted))

    def status_listener(self, status):
        """
        Status update
        :param status: neuer Status
        """
        self.log.debug("change status, track: {}".format(status.track))

    def preset_listener(self, presets):
        """
        Presets geändertt
        :param presets: neue Presets
        """
        for preset in presets:
            self.log.debug("change presets, name: {}".format(preset.name))

    def zone_status_listener(self, zone_status):
        """
        Zohne geändert (mehrere Lautsprecher zusammen als zohne)
        :param zone_status: neue Zohne
        """
        if zone_status:
            self.log.debug("new zone {}".format(zone_status.master_id))
        else:
            self.log.debug('no Zone')

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
        f_handler = logging.handlers.RotatingFileHandler(
            _logfile,
            maxBytes=5000000,
            backupCount=5
        )
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
