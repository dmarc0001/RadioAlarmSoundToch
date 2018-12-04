#!/usr/bin/python3
# -*- coding: utf-8 -*-

from datetime import datetime
from time import time
import re
import logging
import logging.handlers

__author__ = 'Dirk Marciniak'
__copyright__ = 'Copyright 2017'
__license__ = 'GPL'
__version__ = '0.1'


class RadioAlerts:
    DEFAULT_ALERT_DURATION = 60 * 60
    regex_sec = re.compile(r'^(\d+)s$/', re.IGNORECASE)
    regex_min = re.compile(r'^(\d+)m$', re.IGNORECASE)
    regex_std = re.compile(r'^(\d+)h$', re.IGNORECASE)
    regex_val = re.compile(r'^(\d+).*$', re.IGNORECASE)
    regex_date = re.compile(r'^\d{2,4}[-\.]\d{2}[-ß.]\d{2,4}$')
    regex_date_de = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')
    regex_date_int = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    regex_time = re.compile(r'^\d{2}:\d{2}')
    regex_wekkdays = re.compile(r'^mo|tu|we|th|fr|sa|su$', re.IGNORECASE)
    regex_space = re.compile(r'\s+');

    def __init__(self, _log: logging.Logger, _config_section: dict, _alert: str):
        self.log = _log
        self.al_alert = _alert
        self.al_done = False  # Alarm abgearbeitet?
        self.al_prepairing = False  # Alarm wird bearbeitet
        self.al_working_timestamp = False  # alarm spielt gerade
        self.al_enabled = True
        self.al_weekdays = None
        self.al_volume = 0
        self.al_volume_incr = False
        self.al_date = None
        self.al_time = None
        self.al_source = None
        self.al_location = None
        self.al_source_account = None
        self.al_type = None
        self.al_devices = []
        self.al_note = None
        self.al_duration = RadioAlerts.DEFAULT_ALERT_DURATION
        self.al_alert_thread = None  # wenn self.al_working_timestamp dann hier der Thread
        #
        self.log.debug("RadioAlerts is instantiating...")
        #
        # Plausibilität prüfen
        #
        self.al_enabled = self.str2bool(_config_section.get('enable', 'true'))
        self.al_note = _config_section.get('note', 'unknown')
        self.al_source = _config_section.get('source', None)
        self.al_location = _config_section.get('location', None)
        self.al_source_account = _config_section.get('source_account', None)
        self.al_volume_incr = self.str2bool(_config_section.get('raise_vol', 'false'))
        self.al_volume = int(_config_section.get('volume', '21'))
        _date = _config_section.get('date', None)
        _days = _config_section.get('days', None)
        _time = _config_section.get('time', None)
        _devices = _config_section.get('devices', None)
        if _config_section.get('duration', None) is not None:
            _duration = _config_section.get('duration')
            if isinstance(_duration, str):
                # stelle sicher dass dies auch wirklich als STRING übergeben wird
                self.al_duration = RadioAlerts.__get_alert_duration(_config_section.get('duration'))
            else:
                self.al_duration = _duration
        else:
            self.al_duration = RadioAlerts.DEFAULT_ALERT_DURATION
        #
        # Datum, wenn vorhanden, Datum hat festes Format YYYY-MM-DD
        #
        if _date is not None:
            _date = _date.strip()
        if _date is not None and RadioAlerts.regex_date.match(_date):
            # es ist ein einmaliger Alarm an einem Datum
            # also keine Wochentage
            self.log.debug("RadioAlert: date is given {}".format(_date))
            # deutsches Datumsformat?
            try:
                if RadioAlerts.regex_date_de.match(_date):
                    adate = datetime.strptime(_date.strip(), '%d.%m.%Y')
                # oder internationales Datumsformat?
                elif RadioAlerts.regex_date_int.match(_date):
                    adate = datetime.strptime(_date.strip(), '%Y-%m-%d')
                else:
                    adate = None
                    self.log.warning("can not parse datestring {}".format(_date))
            except ValueError as err:
                self.log.fatal("can not parse datestring {} - {}".format(_date, err))
                raise Exception("can not parse datestring {}".format(_date))
            if adate is not None:
                self.al_date = adate.date()
                self.al_weekdays = None
                self.log.debug("alert is once at {}".format(_date))
            else:
                # versuche mal statt dessen Wochentage
                self.__compute_weekdays(_days)
        else:
            # versuche Wochentage
            self.__compute_weekdays(_days)
        #
        # Zeit des Alarms, festes Format: "HH.MM"
        #
        if _time is not None:
            self.__set_time_from_string(_time)
        #
        # etwas debugging
        #
        self.log.debug("alert source is: {}".format(self.al_source))
        self.log.debug("alert volume is: {}".format(self.al_volume))
        self.log.debug("alert is raising: {}".format(self.al_volume_incr))
        # Geräte
        _devices_list = _devices.split(',')
        if len(_devices_list) > 0:
            self.log.debug("al_devices to alert: {}".format(_devices))
            for dev in _devices_list:
                self.al_devices.append(dev.strip())
        else:
            self.al_devices.append("all")
            self.log.debug("al_devices to alert: ALL")
        self.log.debug("RadioAlerts is instantiating...OK")

    def sec_to_alert(self, min_sec_future: int = 0, max_sec_future: int = 60):
        """
        Wie viele Sekunden zum alert?
        :param: min_sec_future wie weit in die zukunft mindestens (auch negativ erlaubt
        :param: max_sec_future wie weit in die Zukunft maximal?
        :return: Anzahl Sekunden zum nächsten Alarm, falls der Abstand geringer ist als 60 Minuten, sonst None
        """
        # belege die wichtigen Daten vor
        dest_datetime = None
        time_diff = None
        #
        now_datetime = datetime.now()
        if self.al_date is not None:
            # ok, einmalige Sache, ist das Datum HEUTE?
            if self.al_date == now_datetime.date():
                # ja, heute, ist das noch in der Zukunft
                # erzeuge Datum und Uhrzeit am heutigen Tag
                # Die Alarmzeit ist hiermit festgelegt
                dest_datetime = datetime.combine(now_datetime.date(), self.al_time)
            else:
                return None
        else:
            # Kein Datum gegeben, könnte als täglich oder an bestimmten Tagen sein
            # dieser wochentag oder täglich?
            # 7 stehr hier für täglich
            if self.al_weekdays is None:
                # weder Datum noch Wochentag ==> Fetter Fehler
                self.log.error("alert {} has not an date and not an weekday! ABORT".format(self.al_alert))
                return None
            # welcher Wochentag ist heute?
            curr_day_number = now_datetime.weekday()
            if 7 in self.al_weekdays or curr_day_number in self.al_weekdays:
                # jeden Tag oder dieser Wochentag ist ein Treffer, also könnte es Alarm geben
                dest_datetime = datetime.combine(now_datetime.date(), self.al_time)
            else:
                return None
        #
        # an dieser Stelle sollte ein eindeutiger Alarmzeitpunkt feststehen
        # d.h dest_datetime sollte erzeugt sein
        #
        if dest_datetime is None:
            # das ist ein schwerer Fehler
            self.log.error("datetime computing was None == programm error! call developer!")
            return None
        if now_datetime == dest_datetime:
            # genau jetzt
            return 0
        if now_datetime < dest_datetime:
            # noch VOR der Zeit
            time_diff = (dest_datetime - now_datetime).seconds
        else:
            # 0 ist erledigt (oben) kann also nur noch
            # NACH der Zeit sein...
            time_diff = 0 - (now_datetime - dest_datetime).seconds
        if time_diff is None:
            # schwerer Fehler!
            self.log.error("time diff computing was None == programm error! call developer!")
            return None
        #
        # mal sehen, wie gross die Diferenz ist
        #
        if -1800 < time_diff < -300 and not self.al_done:
            # nach 5 minuten über der zeit als erledigt bezeichnen
            self.al_done = True
        if time_diff < -1800 and self.al_done:
            # nach 30 Minuten wieder zulassen
            self.al_done = False
        if min_sec_future < time_diff < max_sec_future and not self.al_done:
            # in max 60 Sekunden in der Zukunft, wenn noch nicht erledigt
            self.log.debug("alert event less than {} ({}) sec in the future...".format(max_sec_future,time_diff))
            return time_diff
        else:
            return None

    def __compute_weekdays(self, _days: str):
        """
        Finde Wochentage aus der Konfiguration
        :return: NIX
        """
        # Wochentage erst mal testen
        # wochentage (mo,th,we,th,fr,sa,su) | dayly  oder _date is not None  dann ONCE
        _days_fitted = RadioAlerts.regex_space.sub('', _days )
        self.log.debug("RadioAlerts: compute al_weekdays (or everyday). given string: {}...".format(_days_fitted))
        _weekdays = _days_fitted.split(',')
        self.al_weekdays = []
        # wochentage (mo,th,we,th,fr,sa,su) | daily | once
        for day in _weekdays:
            day = day.strip() # eigentlich redundant, da oben alle spaces gekillt wurden
            if day == 'daily':
                # taeglich. Alles löschen und neu initialisieren
                self.log.info("dayly alert detected!")
                self.al_weekdays.append(7)
                break
            if re.match(RadioAlerts.regex_wekkdays, day):
                # Wochentag passt, zufügen
                if day == 'mo':
                    self.al_weekdays.append(0)
                elif day == 'tu':
                    self.al_weekdays.append(1)
                elif day == 'we':
                    self.al_weekdays.append(2)
                elif day == 'th':
                    self.al_weekdays.append(3)
                elif day == 'fr':
                    self.al_weekdays.append(4)
                elif day == 'sa':
                    self.al_weekdays.append(5)
                elif day == 'su':
                    self.al_weekdays.append(6)
                else:
                    continue
                self.log.debug("alert at {} detected.".format(day))

    def __set_time_from_string(self, _ti: str):
        _time = _ti.strip()
        if _time is not None and RadioAlerts.regex_time.match(_time):
            try:
                atime = datetime.strptime(_time, '%H:%M')
                self.log.debug("time is correct to {}...".format(_time))
            except ValueError as err:
                self.log.fatal("can not parse timestring {} - {}".format(_time, err))
                self.log.warning("time is NOT correct, set to 06:00...")
                atime = datetime.strptime('06:00', '%H:%M')
            self.al_time = atime.time()
        else:
            self.al_time = datetime.strptime('06:00', '%H:%M').time()

    @staticmethod
    def __get_alert_duration(_dur_str: str):
        """
        gib die gewünschte Dauer des Alarms zurück
        :return:
        """
        if _dur_str is None:
            return RadioAlerts.DEFAULT_ALARM_DURATION
        if re.match(RadioAlerts.regex_sec, _dur_str):
            m = re.match(RadioAlerts.regex_sec, _dur_str)
            return int(m.group(1))
        if re.match(RadioAlerts.regex_min, _dur_str):
            m = re.match(RadioAlerts.regex_min, _dur_str)
            return int(m.group(1)) * 60
        if re.match(RadioAlerts.regex_std, _dur_str):
            m = re.match(RadioAlerts.regex_std, _dur_str)
            return int(m.group(1)) * 60 * 60
        if re.match(RadioAlerts.regex_val, _dur_str):
            m = re.match(RadioAlerts.regex_val, _dur_str)
            return int(m.group(1))
        return RadioAlerts.DEFAULT_ALARM_DURATION

    @staticmethod
    def str2bool(_val: str):
        if type(_val) is str:
            return _val.lower() in ('yes', 'true', 't', '1')
        if type(_val) is bool:
            return _val

    @property
    def alert_enabled(self):
        return (self.al_enabled)

    @alert_enabled.setter
    def alert_enabled(self, _en):
        self.al_enabled = _en

    @property
    def alert_thread(self):
        return self.al_alert_thread

    @alert_thread.setter
    def alert_thread(self, _alert_thread):
        self.al_alert_thread = _alert_thread

    @property
    def alert_working_timestamp(self):
        return self.al_working_timestamp

    @alert_working_timestamp.setter
    def alert_working_timestamp(self, _is_working: int):
        self.al_working_timestamp = _is_working

    @property
    def alert_duration_secounds(self):
        """
        Alarmdauer des alarms in sekunden zurückgeben
        :return:
        """
        return self.al_duration

    @property
    def alert_done(self):
        """
        Gib zurück ob Alarm erst mal abgearbeitet ist
        :return: ist der Alarm bearbeitet
        """
        return self.al_done

    @alert_done.setter
    def alert_done(self, _is_done: bool):
        """
        Setzte den Marker, dass der Alarm abgearbeitet ist
        :param _is_done: Marker
        :return: Nix
        """
        self.al_done = _is_done

    @property
    def alert_prepeairing(self):
        """
        wird der Alarm bereits vorbereitet?
        :return: True wenn ja
        """
        return self.al_prepairing

    @alert_prepeairing.setter
    def alert_prepeairing(self, _is_prepairing: bool):
        """
        Setzte oder lösche den Status der Vorbereitung
        :param _is_prepairing: neuer Wert
        :return: neuer Wert
        """
        self.al_prepairing = _is_prepairing

    @property
    def alert_source(self):
        """
        Gib die Source für das Radio zurück
        :return: Source als str
        """
        return self.al_source

    @property
    def alert_devices(self):
        return self.al_devices

    @property
    def alert_time(self):
        return self.al_time

    @property
    def alert_date(self):
        return self.al_date

    @property
    def alert_note(self):
        return self.al_note

    @alert_note.setter
    def alert_note(self, _note: str):
        if _note is not None:
            self.al_note = _note
        else:
            self.al_note = "alert {}".format(self.al_note)

    @property
    def alert_volume(self):
        return self.al_volume

    @property
    def alert_volume_incr(self):
        return self.al_volume_incr

    @property
    def alert_location(self):
        return self.al_location

    @property
    def alert_time(self):
        return self.al_time

    @alert_time.setter
    def alert_time(self, _ti: str):
        self.__set_time_from_string(_ti)

    @property
    def alert_alert(self):
        return self.al_alert


def main():
    """Hauptprogramm"""
    from config_files_obj import ConfigFileObj
    from time import sleep
    log = logging.getLogger("config")
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(module)s: %(message)s", '%Y%m%d %H:%M:%S')
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(formatter)
    log.addHandler(c_handler)
    #
    # config
    #
    cf_ob = ConfigFileObj(log, '../config/test.ini')
    alerts = cf_ob.config_object
    log.debug("alert 00")
    al = RadioAlerts(log, alerts['alert-00'])
    log.info("time to next alert: {}".format(al.sec_to_alert(max_sec_future=120)))
    for devname in al.alert_devices:
        log.info("device: '{}'".format(devname))
    log.debug("===============\n\n")
    sleep(2)
    del al


if __name__ == '__main__':
    main()
