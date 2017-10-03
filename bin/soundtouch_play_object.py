#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import logging.handlers
from time import sleep, time
import re
from radio_alerts import RadioAlerts
from libsoundtouch.device import SoundTouchDevice
from libsoundtouch.utils import Source, Type
from threading import Thread

__author__ = 'Dirk Marciniak'
__copyright__ = 'Copyright 2017'
__license__ = 'GPL'
__version__ = '0.1'


class SoundtouchPlayObject(Thread):
    re_preset = re.compile(r'^PRESET_[123456]$')
    re_inetradio = re.compile(r'INTERNET_RADIO|TUNEIN')
    re_amazon = re.compile(r'^AMAZON$')

    def __init__(self, _log: logging.Logger, _avail_devices: list, _alert: RadioAlerts):
        Thread.__init__(self)
        self.log = _log
        self.alert = _alert
        self.soundbar_devices = []
        self.master_device = None
        self.slave_devices = []
        self.is_playing = False
        self.duration = _alert.alert_duration
        #
        # schnittmenge der gefundenen und der geforderten Devices machen
        #
        for device in _avail_devices:
            self.log.debug("check avaivible device '{}' if in alert list...".format(device.config.name))
            if device.config.name.lower() in self.alert.alert_devices:
                self.log.debug(
                    "found avaivible device '{}' if in alert list, append..".format(device.config.name.lower()))
                self.soundbar_devices.append(device)
        # sind jetzt Geräte vorhanden?
        if len(self.soundbar_devices) > 1:
            self.log.info("multiple devices for alert, try multiroom...")
        else:
            self.log.debug("try start one device...")

    def __del__(self):
        """
        Destruktor...
        :return:
        """

    def run(self):
        """
        Das Gerät einschalten(falls noch nicht passiert), sender wählen
        :return:
        """
        self.is_playing = True
        #
        # neues Gerätreobjekt aus dem ersten Gerät machen
        # und anschalten
        #
        self.master_device = self.__create_sound_device()
        #
        # Sender wählen
        #
        self.__tune_channel()
        #
        # Lautstärke
        #
        __dest_vol = self.alert.alert_volume
        # fade in oder nicht
        if not self.alert.alert_volume_incr:
            # soll gleich losbrüllen
            self.master_device.set_volume(__dest_vol)
            for slave in self.slave_devices:
                slave.set_volume(__dest_vol)
        else:
            # soll langsam ansteigen...
            self.master_device.set_volume(0)
            for slave in self.slave_devices:
                slave.set_volume(0)
        # vorbereitung ist vorbei...
        self.alert.alert_prepairing = False
        #
        # setze die zeit, wann der Alarm ausgeschaltet wird
        #
        __time_to_off = int(time()) + self.duration
        #
        # buffering abwarten
        #
        curr_stat = self.master_device.status().play_status
        while self.is_playing and __time_to_off > int(time()) and curr_stat != 'PLAY_STATE':
            sleep(.8)
            curr_stat = self.master_device.status().play_status
            self.log.debug("wait while buffering, state: {}...".format(curr_stat))
        sleep(.8)
        #
        # Lautstärke einblenden
        #
        if self.alert.alert_volume_incr:
            self.__fade_in(0, __dest_vol)
            self.log.debug("volume is ok, wait for alarm end...")
        #
        # Spielen, bis der Alarm zuende ist
        # TODO: callback via websocket bei power off oder senderwechsel alarm für das Gerät beenden
        while self.is_playing and __time_to_off > int(time()):
            sleep(.5)
            self.log.debug("wait now: {} to:{} diff {}".format(int(time()), __time_to_off, __time_to_off - int(time())))
        #
        # wieder ausblenden oder abschalten
        #
        if self.alert.alert_volume_incr:
            self.__fade_out(self.master_device.volume().actual, 0)
        #
        # aussschalten
        #
        self.power_off()
        self.alert.alert_thread = None
        self.alert.self.al_working = False
        sleep(.6)
        #
        # noch eine Lautstärke einstellen für nächstes Einschalten
        #
        self.master_device.set_volume(__dest_vol)
        for slave in self.slave_devices:
            slave.set_volume(__dest_vol)

    def __create_sound_device(self):
        """
        Erzeuge ein Objekt ggf auch mit Zohne
        :return: OK oder nicht
        """
        # TODO: vorhandene Zohnen berücksichtigen oder auch löschen
        master_device = None
        count_devices = 0
        for device in self.soundbar_devices:
            hostname = device.host
            portname = device.port
            # wenn kein Master da ist, erst mal das Master Gerät machen
            if master_device is None:
                master_device = SoundTouchDevice(host=hostname, port=portname)
                self.log.debug("switch on master device {}".format(device.config.name))
                master_device.add_zone_status_listener(self.__zone_status_listener)
                master_device.power_on()
                curr_stat = master_device.status().source
                while curr_stat == 'STANDBY':
                    self.log.debug("wait for weakup master device...")
                    sleep(.4)
                    curr_stat = master_device.status().source
            else:
                slave = SoundTouchDevice(host=hostname, port=portname)
                slave.power_on()
                self.slave_devices.append(slave)
                # ist eine Zohne notwendig?
                if count_devices == 1:
                    # es ist der erste sklave, also erzeuge Zohne
                    master_device.create_zone([slave])
                else:
                    # Zohne vorhanden, einen Sklaven dazu
                    master_device.add_zone_slave([slave])
            count_devices += 1
        curr_stat = master_device.status().source
        while curr_stat == 'STANDBY':
            self.log.debug("wait for weakup master device...")
            sleep(.4)
            curr_stat = master_device.status().source
        return master_device

    def __fade_in(self, _from: int, _to: int):
        """
        Lautstärke langsam aufdrehen (0..100)
        :param _from: von welcher Lautstärke
        :param _to: bis welche Lautstärke
        """
        __curr_vol = _from
        __dest_vol = _to
        while self.is_playing and (__curr_vol < __dest_vol):
            self.log.debug("volume: {}...".format(__curr_vol))
            __curr_vol = __curr_vol + 2
            self.master_device.set_volume(__curr_vol)
            for slave in self.slave_devices:
                slave.set_volume(__curr_vol)
            sleep(.90)
            # ende

    def __fade_out(self, _from, _to):
        """
        Lautstärke langsam absenken
        :param _from:
        :param _to:
        """
        __curr_vol = _from
        __dest_vol = _to
        while self.is_playing and (__curr_vol > __dest_vol) and __curr_vol > 0:
            self.log.debug("volume: {}...".format(__curr_vol))
            __curr_vol = __curr_vol - 3
            if __curr_vol < 0:
                __curr_vol = 0
            self.master_device.set_volume(__curr_vol)
            for slave in self.slave_devices:
                slave.set_volume(__curr_vol)
            sleep(.40)
            # ende

    def __tune_channel(self):
        """
        Stelle den richtigen Sender ein
        :return: True bei OK
        """
        #
        # welche Sorte Sender?
        #

        # erst das ganz einfache: PRESETS
        if SoundtouchPlayObject.re_preset.match(self.alert.al_source):
            # Ich tune zu einem PRESET, erst mal die Nummer finden
            preset_num = int(re.search('^PRESET_([123456789])$', self.alert.al_source).group(1)) - 1
            presets = self.master_device.presets()
            self.log.info("switch to PRESET {}: {} ({})".format(preset_num+1, presets[preset_num].name, presets[preset_num].source))
            # Play preset
            self.master_device.select_preset(presets[preset_num])
        elif SoundtouchPlayObject.re_inetradio.match(self.alert.al_source):
            # internetradio spielen
            self.log.info("switch to INTERNETE_RADIO|TUNEIN, channel number {}".format(self.alert.al_location))
            self.master_device.play_media(Source.INTERNET_RADIO, self.alert.al_location)
            self.log.info("switch to INTERNETE_RADIO|TUNEIN, station {}".format(self.master_device.status().station_name))
        # AMAZON geht noch nicht :(
        #elif SoundtouchPlayObject.re_amazon.match(self.alert.al_source):
        #    # ich will einen AMAZON Kanal spielen
        #    self.master_device.play_media(Source.AMAZON, self.alert.al_location, self.alert.al_source_account, Type.TRACKLIST)
        #    self.log.info("switch to AMAZON, station {}".format(self.master_device.status().station_name))
        else:
            # damit überhaupt was spielt:
            self.log.error("non an valid media requested, play default PRESET_1")
            preset_num = 0
            presets = self.master_device.presets()
            self.log.info(
                "switch to PRESET {}: {} ({})".format(preset_num + 1, presets[preset_num].name, presets[preset_num].source))
            # Play preset
            self.master_device.select_preset(presets[preset_num])

    def power_off(self):
        """
        Alles wieder ausschalten
        :return:
        """
        self.log.debug("switch off device(s)...")
        if len(self.slave_devices) > 0:
            self.master_device.remove_zone_slave(self.slave_devices)
        self.master_device.clear_zone_status_listeners()
        self.master_device.power_off()

    def __zone_status_listener(self, zone_status):
        """
        Callback welcher den Status der Playzohne berichtet
        :param zone_status:
        :return:
        """
        if zone_status:
            self.log.info(zone_status.master_id)
        else:
            self.log.info('no Zone')


def main():
    """Hauptprogramm"""
    my_alert = 'alert-02'
    from libsoundtouch import discover_devices
    from config_files_obj import ConfigFileObj
    from time import sleep
    log = logging.getLogger("s")
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(module)s: %(message)s", '%Y%m%d %H:%M:%S')
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(formatter)
    log.addHandler(c_handler)
    #
    # config
    #
    cf_ob = ConfigFileObj(log, '../config/alert.ini')
    alerts = cf_ob.config_object
    #
    log.debug("discover devices in network...")
    devices = discover_devices(timeout=3)
    log.debug(my_alert)
    al = RadioAlerts(log, alerts[my_alert])
    spo = SoundtouchPlayObject(log, devices, al)
    log.debug("start device(s)...")
    spo.start()
    log.debug("join thread...")
    spo.join()
    sleep(.3)
    del spo
    del al
    log.debug("===============\n\n")


if __name__ == '__main__':
    main()
