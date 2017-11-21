#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import logging.handlers
from time import sleep, time
import re
from radio_alerts import RadioAlerts
from libsoundtouch.device import SoundTouchDevice
from libsoundtouch.utils import Source
from threading import Thread, Lock

__author__ = 'Dirk Marciniak'
__copyright__ = 'Copyright 2017'
__license__ = 'GPL'
__version__ = '0.1'


class SoundtouchPlayObject(Thread):
    re_preset = re.compile(r'^PRESET_[123456]$')
    re_inetradio = re.compile(r'INTERNET_RADIO|TUNEIN')
    re_amazon = re.compile(r'^AMAZON$')
    re_standby = re.compile(r'^STANDBY$')

    def __init__(self, _log: logging.Logger, _avail_devices: dict, _alert: RadioAlerts):
        Thread.__init__(self)
        self.log = _log
        self.alert = _alert
        self.soundtouch_devices = []
        self.master_device = None
        self.slave_devices = []
        self.is_playing = False
        self.is_switchoff = True
        self.duration = _alert.alert_duration_secounds
        self.curr_vol = 0
        self.alert_volume_incr = self.alert.alert_volume_incr
        self.play_source = None
        self.play_station = None
        self.zone_status = None
        self.callback_volume_lock = Lock()
        self.status_listener_lock = Lock()
        self.zone_listener_lock = Lock()
        #
        self.log.debug("create object...")
        #
        # Schnittmenge der gefundenen und der geforderten Devices machen
        #
        self.log.debug("device source is {}...".format(self.play_source))
        for device_name in self.alert.alert_devices:
            device = self.__exist_device_in_list(device_name, _avail_devices)
            if device is not None:
                self.soundtouch_devices.append(device)
                self.log.debug("found device {} to play...".format(device['name']))
        # sind jetzt Geräte vorhanden?
        if len(self.soundtouch_devices) > 1:
            self.log.info("multiple devices for alert, try multiroom...")
        else:
            self.log.debug("try start one device...")

    def __del__(self):
        """
        Destruktor...
        :return:
        """
        self.log.debug("delete object...")

    def run(self):
        """
        Das Gerät einschalten(falls noch nicht passiert), sender wählen
        :return:
        """
        self.is_playing = True
        self.log.debug("start thread...")
        #
        # neues Gerätreobjekt aus dem ersten Gerät machen
        # und anschalten
        #
        self.master_device = self.__create_sound_device()
        if self.master_device is None:
            self.log.error("Failure while checking master device! thread was endet...")
            return
        self.zone_status = self.master_device.zone_status(True)
        #
        # Sender wählen
        #
        self.__tune_channel()
        #
        # Lautstärke
        #
        __dest_vol = self.alert.alert_volume
        self.curr_vol = __dest_vol
        # fade in oder nicht
        if not self.alert_volume_incr:
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
        __current_time = int(time())
        __time_to_off = self.duration + __current_time
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
        # jetzt noch merken was der abspielt, damit ich veränderungen bemerke
        #
        self.play_source = self.master_device.status().source
        self.play_station = self.master_device.status().station_name
        #
        # Benachrichtigungen EIN
        #
        self.master_device.add_status_listener(self.__status_listener)
        self.master_device.add_volume_listener(self.__volume_listener)
        self.master_device.add_zone_status_listener(self.__zone_status_listener)
        self.master_device.start_notification()
        #
        # Lautstärke einblenden
        #
        if self.alert_volume_incr:
            self.__fade_in(0, __dest_vol)
            self.log.debug("volume is ok, wait for alarm end...")
        #
        # Spielen, bis der Alarm zuende ist
        #
        while self.is_playing and __time_to_off > int(time()):
            sleep(1.6)
            wait_time = int(__time_to_off - int(time()))
            self.log.debug("device {} alert running for {} seconds".format(self.master_device.config.name, wait_time))
        #
        # wenn wieder ausgeschaltet werden soll
        #
        if self.is_switchoff:
            self.log.debug("switch off device....")
            #
            # wieder ausblenden oder abschalten
            #
            if self.alert_volume_incr:
                self.__fade_out(self.master_device.volume().actual, 0)
            #
            # aussschalten
            #
            self.power_off()
            self.alert.alert_thread = None
            self.alert.alert_working_timestamp = False
            sleep(.6)
            #
            # noch eine Lautstärke einstellen für nächstes Einschalten
            #
            self.master_device.set_volume(__dest_vol)
            for slave in self.slave_devices:
                slave.set_volume(__dest_vol)
        else:
            self.log.debug("NOT switch off device....")
        # auf jeden fall das hier
        self.master_device.clear_status_listener()
        self.master_device.clear_volume_listeners()
        self.master_device.clear_zone_status_listeners()
        # ACHTUNG in der library verändert
        try:
            self.master_device.stop_notification()
        except (RuntimeError, NameError, TypeError):
            self.log.error("the library libsoundtouch.device ist edit from this author," +
                           "he addet the function 'stop_notification()' to the source")
        self.alert.alert_working_timestamp = 0
        self.alert.alert_done = True
        self.log.debug("thread was endet...")

    def __exist_device_in_list(self, _name_to_find: str, _avail_list: dict):
        """
        Gib das Gerät mit dem Namen XXX als Geräteobjekt zurück, falls vorhanden
        :param _name_to_find: Name des Gerätes
        :param _avail_list: Liste in welcher gesucht wird
        :return: Geräteobjekt oder None
        """
        # aktuelle Liste existiert
        # Pattern für Vergleich compilieren
        match_pattern = re.compile('^' + _name_to_find + '$', re.IGNORECASE)
        # finde raus ob es das gerät gibt
        for devname, device in _avail_list.items():
            if re.match(match_pattern, devname):
                self.log.debug("destination device found!")
                return device
        self.log.debug("destination device NOT found!")
        return None

    def __create_sound_device(self):
        """
        Erzeuge ein Objekt ggf auch mit Zohne
        :return: OK oder nicht
        """
        # TODO: vorhandene Zohnen berücksichtigen oder auch löschen
        master_device = None
        count_devices = 0
        for device in self.soundtouch_devices:
            hostname = device['host']
            portname = device['port']
            # wenn kein Master da ist, erst mal das Master Gerät machen
            if master_device is None:
                master_device = SoundTouchDevice(host=hostname, port=portname)
                self.log.debug("switch on master device {}".format(device['name']))
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
        sleep(.6)
        #
        # es kann eine exception geben, versuche es ein paar mal in diesem Fall
        #
        curr_stat = None
        curr_stat_count = 0
        while curr_stat is None and curr_stat_count < 4:
            curr_stat_count += 1
            try:
                curr_stat = master_device.status().source
            except:
                sleep(.6)
                pass
        #
        # da passiert was, was nicht sein soll
        #
        if curr_stat is None:
            self.log.warning("can't receive play status from master device...")
            # Rückkehr mit Fehlermeldung
            return None
        else:
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
        self.curr_vol = _from
        __dest_vol = _to
        # TODO: konstante zeit, dafür die Schritte nd die Dauer errechnen
        while self.is_playing and (self.curr_vol < __dest_vol) and self.alert_volume_incr:
            self.log.debug("volume: {}...".format(self.curr_vol))
            self.curr_vol = self.curr_vol + 2
            self.master_device.set_volume(self.curr_vol)
            for slave in self.slave_devices:
                slave.set_volume(self.curr_vol)
            sleep(1.20)
        # ende

    def __fade_out(self, _from, _to):
        """
        Lautstärke langsam absenken
        :param _from:
        :param _to:
        """
        self.curr_vol = _from
        __dest_vol = _to
        while self.is_playing and (self.curr_vol > __dest_vol) and self.curr_vol > 0:
            self.log.debug("volume: {}...".format(self.curr_vol))
            self.curr_vol = self.curr_vol - 3
            if self.curr_vol < 0:
                self.curr_vol = 0
            self.master_device.set_volume(self.curr_vol)
            for slave in self.slave_devices:
                slave.set_volume(self.curr_vol)
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
        if SoundtouchPlayObject.re_preset.match(self.alert.alert_source):
            # Ich tune zu einem PRESET, erst mal die Nummer finden
            preset_num = int(re.search('^PRESET_([123456789])$', self.alert.al_source).group(1)) - 1
            presets = self.master_device.presets()
            self.log.info("switch to PRESET {}: {} ({})".format(preset_num + 1, presets[preset_num].name,
                                                                presets[preset_num].source))
            # Play preset
            self.master_device.select_preset(presets[preset_num])
        elif SoundtouchPlayObject.re_inetradio.match(self.alert.alert_source):
            # internetradio spielen
            self.log.info("switch to INTERNETE_RADIO|TUNEIN, channel number {}".format(self.alert.alert_location))
            self.master_device.play_media(Source.INTERNET_RADIO, self.alert.alert_location)
            self.log.info(
                "switch to INTERNETE_RADIO|TUNEIN, station {}".format(self.master_device.status().station_name))
        # AMAZON geht noch nicht :(
        # elif SoundtouchPlayObject.re_amazon.match(self.alert.alert_source):
        else:
            # damit überhaupt was spielt:
            self.log.error("non an valid media requested, play default PRESET_1")
            preset_num = 0
            presets = self.master_device.presets()
            self.log.info(
                "switch to PRESET {}: {} ({})".format(preset_num + 1, presets[preset_num].name,
                                                      presets[preset_num].source))
            # Play preset
            self.master_device.select_preset(presets[preset_num])

    def power_off(self):
        """
        Alles wieder ausschalten
        :return:
        """
        self.log.debug("switch off device(s)...")
        if self.zone_status is not None and len(self.slave_devices) > 0:
            self.master_device.remove_zone_slave(self.slave_devices)
        self.master_device.clear_zone_status_listeners()
        self.master_device.power_off()

    def __zone_status_listener(self, zone_status):
        """
        Callback welcher den Status der Playzohne berichtet
        :param zone_status:
        :return:
        """
        self.zone_listener_lock.acquire()
        if zone_status:
            self.log.info(zone_status.master_id)
            if zone_status.master_id != self.zone_status.master_id:
                # ID verändert, thread ist alle
                self.log.info("ZoneID is now {}".format(zone_status.master_id))
                self.zone_status.master_id = zone_status.master_id
                self.is_playing = False
                self.is_switchoff = False
        else:
            self.log.info('not more an Zone')
            # lösche slaves
            self.slave_devices.clear()
        self.zone_listener_lock.release()

    def __volume_listener(self, volume):
        """
        Listener für Volume änderung ==> fading abschalten

        :param volume: neue Lautstärke
        :return: NIX
        """
        # ändert sich die Lautstärke ohne fading...
        self.callback_volume_lock.acquire()
        play_volume = volume.actual
        self.log.debug("volume changed to: {}, alert current is {}".format(play_volume, self.curr_vol))
        if play_volume != self.curr_vol and self.alert_volume_incr:
            # ups, der user fingert daran rum
            self.alert_volume_incr = False
            self.log.warning("user has manual changed volume, switch fading off (for this alert only)...")
        self.callback_volume_lock.release()

    def __status_listener(self, status):
        """
        Listener für Status änderung ==> Gerät "vergessen"

        :param volume: status
        :return: NIX
        """
        # self.log.info("status changed to: {}".format(status.source))
        # wenn der Status sich ändert (nach STANDBY)
        self.status_listener_lock.acquire()
        play_source = status.source
        play_station = status.station_name
        if play_source is not None:
            # gibt es was zu berichten (STANDBY?)
            if play_source is not None and SoundtouchPlayObject.re_standby.match(play_source):
                # Gerät auf STANDBY, das war es dann
                self.log.warning("device manual switched to STANDBY, stop thread...")
                self.is_playing = False
                self.status_listener_lock.release()
                return
            # ist station und source vorhanden?
            if play_station is not None:
                if self.play_source != play_source or self.play_station != play_station:
                    # da wurde rumgemacht....
                    self.log.info(
                        "station name changed to: {} / source changed to {}".format(status.station_name, play_source))
                    # da wurde dran rumgemacht, Thread beenden, User das Feld überlassen
                    self.log.warning("device manual switched to {}, stop thread...".format(play_station))
                    self.is_playing = False
                    self.is_switchoff = False
        self.status_listener_lock.release()


def main():
    """Hauptprogramm"""
    my_alert = 'alert-00'
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
    cf_ob = ConfigFileObj(log, '../config/test.ini')
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
    log.debug("delete SoundtouchPlayObject Object...")
    del spo
    log.debug("delete RadioAlerts Object...")
    del al
    log.debug("===============\n\n")
    exit(0)


if __name__ == '__main__':
    main()

    #
    # Änderungen in der library SoundTouchDevice:
    #
    #        self._device_info_updated_listeners = []
    #        # dmarcini
    #        self.ws_thread = None
    #
    #    def __init_config(self):
    #        response = requests.get(
    #            "http://" + self._host + ":" + str(self._port) + "/info")
    #        dom = minidom.parseString(response.text)
    #        self._config = Config(dom)#
    #
    #    def __del__(self):
    #        # dmarcini
    #        if self.ws_thread is not None:
    #            self._ws_client.close()
    #
    #    def start_notification(self):
    #        """Start Websocket connection."""
    #        self._ws_client = websocket.WebSocketApp(
    #            "ws://{0}:{1}/".format(self._host, self._ws_port),
    #            on_message=self._on_message,
    #            subprotocols=['gabbo'])
    #        self.ws_thread = WebSocketThread(self._ws_client)
    #        self.ws_thread.start()
    #
    #    def stop_notification(self):
    #        if self.ws_thread is not None:
    #            self._ws_client.close()
    #
