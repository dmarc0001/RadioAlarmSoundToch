# -*- coding: utf-8 -*-
#
from libsoundtouch import soundtouch_device
from libsoundtouch.utils import Source, Type

device = soundtouch_device('192.168.1.1')  # Manual configuration
device.power_on()

# Config object
print(device.config.name)

# Status object
# device.status() will do an HTTP request.
# Try to cache this value if needed.
status = device.status()
print(status.source)
print(status.artist + " - " + status.track)
device.pause()
device.next_track()
device.play()

# Media Playback
# device.play_media(source, location, account, media_type)
# account and media_type are optionals

# Radio
device.play_media(Source.INTERNET_RADIO, '4712')  # Studio Brussel

# Spotify
spot_user_id = ''  # Should be filled in with your Spotify userID
# This userID can be found by playing Spotify on the
# connected SoundTouch speaker, and calling
# device.status().content_item.source_account
device.play_media(Source.SPOTIFY,
                  'spotify:track:5J59VOgvclrhLDYUoH5OaW',
                  spot_user_id)  # Bazart - Goud

# Local music (Windows media player, Itunes)
# Account ID can be found by playing local music on the
# connected Soundtouch speaker, and calling
# device.status().content_item.source_account
account_id = device.status().content_item.source_account
device.play_media(Source.LOCAL_MUSIC,
                  'album:1',
                  account_id,
                  Type.ALBUM)

# Play an HTTP URL (not HTTPS)
device.play_url('http://fqdn/file.mp3')

# Volume object
# device.volume() will do an HTTP request.
# Try to cache this value if needed.
volume = device.volume()
print(volume.actual)
print(volume.muted)
device.set_volume(30)  # 0..100

# Presets object
# device.presets() will do an HTTP request.
# Try to cache this value if needed.
presets = device.presets()
print(presets[0].name)
print(presets[0].source)
# Play preset 0
device.select_preset(presets[0])

# ZoneStatus object
# device.zone_status() will do an HTTP request.
# Try to cache this value if needed.
zone_status = device.zone_status()
print(zone_status.master_id)
print(len(zone_status.slaves))
