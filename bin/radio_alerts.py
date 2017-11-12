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
    regex_sec = re.compile('^(\d+)s$/', re.IGNORECASE)
    regex_min = re.compile('^(\d+)m$', re.IGNORECASE)
    regex_std = re.compile('^(\d+)h$', re.IGNORECASE)
    regex_val = re.compile('^(\d+).*$', re.IGNORECASE)
    regex_date = re.compile('^\d{4}-\d{2}-\d{2}$')
    regex_time = re.compile('^\d{2}:\d{2}')

    def __init__(self, _log: logging.Logger, _alert: dict):
        self.log = _log
        self.al_done = False  # Alarm abgearbeitet?
        self.al_prepairing = False  # Alarm wird bearbeitet
        self.al_working_timestamp = False # alarm spielt gerade
        self.al_enable = True
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
        self.al_enable = self.str2bool(_alert.get('enable', 'true'))
        self.al_note = self.str2bool(_alert.get('note', 'unknown'))
        self.al_source = _alert.get('source', None)
        self.al_location = _alert.get('location', None)
        self.al_source_account = _alert.get('source_account', None)
        self.al_volume_incr = self.str2bool(_alert.get('raise_vol', 'false'))
        self.al_volume = int(_alert.get('volume', '21'))
        _date = _alert.get('date', None)
        _days = _alert.get('days', None)
        _time = _alert.get('time', None)
        _devices = _alert.get('devices', None)
        if _alert.get('duration', None) is not None:
            _duration = _alert.get('duration')
            if isinstance(_duration, str):
                # stelle sicher dass dies auch wirklich als STRING übergeben wird
                self.al_duration = RadioAlerts.__get_alert_duration(_alert.get('duration'))
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
            try:
                adate = datetime.strptime(_date.strip(), '%Y-%m-%d')
                self.al_date = adate.date()
                self.al_weekdays = None
                self.log.info("alert is once at {}".format(_date))
            except ValueError as err:
                self.log.fatal("can not parse datestring {} - {}".format(_date, err))
                raise Exception("can not parse datestring {}".format(_date))
        else:
            # Wochentage erst mal testen
            # wochentage (mo,th,we,th,fr,sa,su) | dayly  oder _date is not None  dann ONCE
            self.log.debug("RadioAlerts: compute al_weekdays (or everyday). given string: {}...".format(_days))
            _weekdays = _days.split(',')
            self.al_weekdays = []
            # wochentage (mo,th,we,th,fr,sa,su) | daily | once
            reg_ex = re.compile('mo|tu|we|th|fr|sa|su', re.IGNORECASE)
            for day in _weekdays:
                day = day.strip()
                if day == 'daily':
                    # taeglich. Alles löschen und neu initialisieren
                    self.log.info("dayly alert detected!")
                    self.al_weekdays = [7]
                    break
                if re.match(reg_ex, day):
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
        #
        # Zeit des Alarms, festes Format: "HH.MM"
        #
        if _time is not None:
            _time = _time.strip()
        if _time is not None and RadioAlerts.regex_time.match(_time):
            self.log.debug("time ({}) found. test if correct...".format(_time))
            try:
                atime = datetime.strptime(_time, '%H:%M')
                self.log.debug("time is correct to {}...".format(_time))
            except ValueError as err:
                self.log.fatal("can not parse timestring {} - {}".format(_date, err))
                self.log.warning("time is NOT correct, set to 06:00...")
                atime = datetime.strptime('06:00', '%H:%M')
            self.al_time = atime.time()
        else:
            self.al_time = datetime.strptime('06:00', '%H:%M').time()
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
        if self.al_date is not None:
            # ok, einmalige Sache, ist das Datum in der Zukunft?
            if self.al_date < datetime.now().date():
                # in der Zukunft, Abstand berechnen
                # erzeuge Datum und Uhrzeit am heutigen Tag
                dest_datetime = datetime.combine(self.al_date, self.al_time)
                # mache einen Timestamp daraus
                dest_timestramp = int(dest_datetime.timestamp())
                # und wie ist datum/zeit genau jetzt?
                now_timestaqmp = int(time())
                time_diff = dest_timestramp - now_timestaqmp
                # ist der Alarm vergangenheit?
                if time_diff < -600:
                    # sorge dafür, dass das erledigt ist
                    self.al_done = True
                if min_sec_future < time_diff < max_sec_future:
                    # in max 60 Sekunden in der Zukunft
                    self.log.debug("once event less than {} sec in the future...".format(max_sec_future))
                    return time_diff
                else:
                    return None
                    # einmalig erst mal abgearbeitet
        # Kein Datum gegeben, könnte als täglich oder an bestimmten Tagen sein
        # dieser wochentag oder täglich?
        # 7 stehr hier für täglich
        curr_day_number = datetime.now().weekday()
        if 7 in self.al_weekdays or curr_day_number in self.al_weekdays:
            # jeden Tag oder dieser Wochentag, also guck mal wie die Differenz ist
            # erzeuge die Uhrzeit am heutigen Tag
            dest_datetime = datetime.combine(datetime.now().date(), self.al_time)
            # mache einen Timestamp für den alarmzeitpunkt
            dest_timestramp = int(dest_datetime.timestamp())
            # und wie ist datum/zeit genau jetzt?
            now_timestaqmp = int(time())
            time_diff = dest_timestramp - now_timestaqmp
            if -1800 < time_diff < -300 and not self.al_done:
                # nach 5 minuten über der zeit als erledigt bezeichnen
                self.al_done = True
            if time_diff < -1800 and self.al_done:
                # nach 30 Minuten wieder zulassen
                self.al_done = False
            if min_sec_future < time_diff < max_sec_future and not self.al_done:
                # in max 60 Sekunden in der Zukunft, wenn noch nicht erledigt
                self.log.debug("repeatable event less than {} sec in the future...".format(max_sec_future))
                return time_diff
            else:
                return None
        # weder einmalig noch wiederholung, dann ...und tschüss
        # self.log.debug("not an repeatable or an single alert, return with None...")
        return None

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
        return _val.lower() in ('yes', 'true', 't', '1')

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
