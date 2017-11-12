<?php
    # 09/2017 D. Marciniak
    #
    # Das Script wird nicht direkt vom Benutzer sondern via JavaScript aus der 
    # Webseite aufgerufen und gibt Informationen via JSON zurück, bzw führt 
    # Weckeraktionen aus und gibt Erfolg oder Misserefolg zurück (als JSON String)
    #

    # Konfiguration lesen
    #include_once "../config/config.php";
    include_once "daemon_comm.php";

    #
    # Hier beginnt die Abarbeitung, zunächst die Unterscheidung ob
    # Information oder Aktion
    #
    if( isset($_GET["getconfigid"]))
    {
        #
        # frage nach der config-id (wird immer nach dem Einlesen oder der Änderung der Config gesetzt)
        #
        $request = array('get' => array('config-id'));
        #
        # stele die Anfrage beim Server und gib Antwort oder Fehler zurück
        # dafür noch (on-the-fly) aus der Datenstruktur einen JSON String machen
        #
        $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
        #
        # sende das Ergebnis (JSON String) an den Aufrufer zurück
        #
        echo $response;
        return;
    }
    elseif( isset($_GET["getstate"]) )
    {
        #
        # Information abfordern
        #
        $whichAlerts = $_GET["getstate"];
        #
        # Anfragearray aus dem Anfragestring erzeugen
        #
        if( $whichAlerts == 'all' )
        {
            # 
            # da ist das einfach: nur ein Eintrag, aber alle abfragen
            # erzeuge die datenstruktur für eine Anfrage beim Relaisdaemon
            #
            $request = array('get' => array('all'));
        }
        else
        {
            #
            # hier können mehrere "Alarme" mit Komma getrennt
            # angegeen worden sein, packe in ein array
            #
            $relArray = explode(",", $whichAlerts);
            $request = array('get' => $relArray );
        }
        #
        # stele die Anfrage beim Server und gib Antwort oder Fehler zurück
        # dafür noch (on-the-fly) aus der Datenstruktur einen JSON String machen
        #
        $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
        #
        # sende das Ergebnis (JSON String) an den Aufrufer zurück
        #
        echo $response;
        return;
    }
    elseif( isset($_GET['getdevices']))
    {
        $request = array('get' => array('devices'));
        # stele die Anfrage beim Server und gib Antwort oder Fehler zurück
        # dafür noch (on-the-fly) aus der Datenstruktur einen JSON String machen
        #
        $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
        #
        # sende das Ergebnis (JSON String) an den Aufrufer zurück
        #
        echo $response;
        return;
    }
    elseif( isset($_GET["setstate"]) )
    {
        # 
        # Aktion, schalte etwas an den Relais herum
        # Aber nur, wenn der gewünschte Status angegeben wurde
        #
        if( isset($_GET["enable"]) )
        {
            #
            # erfrage welche Channels und welcher Status
            #
            $whichState = $_GET["enable"];
            $wichAlerts = $_GET["setstate"];
            # 
            # erzeuge die Liste der Kanäle
            #
            $relArray = explode(",", $wichAlerts);
            $getArray = array();
            foreach( $relArray as $alert )
            {
                $getArray[] = array('alert' => $alert, 'enable' => $whichState );
            }
            #
            # erzeuge die Datenstruktur für das Kommando an den Daemon
            #
            $request = array('set' => $getArray );
            #
            # sende das Kommando an den Daemon, 
            # konvertiere dabei die Datenstruktur on-the-fly in JSON String vor dem aufruf
            #
            $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
            #
            # sende das Ergebnis an den Aufrufer zurück
            echo $response;
            return;
        }
        else
        {
            #
            # es ist kein Status angegeben worden
            # formuliere eine Fehlermeldung 
            #
            $response = array('error' => 'set state without state');
            #Sende die Fehlermeldung an den Aufrufer zurück
            echo json_encode($response);
            return;
        }
    }
    elseif( isset($_GET["edit-alert"]) )
    {
        /*
        alert-xx

        -devices = bad radio
        -date = 
        -time = 21:34
        -source = PRESET_1
        -raise_vol = true
        source_account = 
        note = Dirks Reset Test 2
        type = 
        location = 
        duration = 
        -volume = 35
        -days = mo,tu,we,th,fr
        */
        $whichAlert = $_GET["edit-alert"];
        unset($alert_devices);
        unset($alert_enable);
        unset($alert_time);
        unset($alert_days);
        unset($alert_date);
        unset($alert_source);
        unset($alert_raise_vol);
        unset($alert_volume);
        unset($alert_note);
        unset($alert_duration_secounds);
        unset($alert_source_account);
        unset($alert_type);
        unset($alert_location);

        $alertEdArray = array();
        $editArray = array();
        $editArray['alert'] = $whichAlert;
        # die Zeit setzten?
        if(isset($_GET["alert_time"])) 
        { 
            $alert_time = $_GET["alert_time"]; 
        }
        # die Weckertage setzten?
        if(isset($_GET["alert_days"]))
        {
            $alert_days =  $_GET["alert_days"];
        }
        # ist ein Datum gesetzt (TODO: impliziert dass wochentage gelöscht werden)
        if(isset($_GET["alert_date"]))
        {
            $alert_date = $_GET["alert_date"];
            if(preg_match( '/null/', $alert_date))
            {
              unset($alert_date);  
            }
            else
            {
              unset($alert_days);
            }
        }
        # welche SOURCE wird gesetzt (TODO: momentan nur PRESETS)
        if(isset($_GET["alert_source"]))
        {
            if( preg_match('/^PRESET_[123456]$/', $_GET["alert_source"]))
            {
                $alert_source = $_GET["alert_source"];
            }
            // TODO: abhängig von der source noch andere Parameter...
        }
        # soll die Lautstärke langsam hochgedrecht werden?
        if(isset($_GET['alert_raise_vol']))
        {
            $alert_raise_vol = $_GET['alert_raise_vol'];
        }
        # welche alarmlautstärke
        if(isset($_GET['alert_volume']))
        {
            $alert_volume = $_GET['alert_volume'];
        }
        # welcher name des Alarms
        if(isset($_GET['alert_note']))
        {
            $alert_note = $_GET['alert_note'];
        }
        # und noch den namen des Alarms
        if(isset($_GET['alert_devices']))
        {
            $alert_devices = $_GET['alert_devices'];
        }
        if(isset($_GET['alert_source_account']))
        {
            $alert_source_account = $_GET['alert_source_account'];
        }
        if(isset($_GET['alert_type']))
        {
            $alert_type = $_GET['alert_type'];
        }
        if(isset($_GET['alert_location']))
        {
            $alert_location = $_GET['alert_location'];
        }
        if(isset($_GET['alert_duration_secounds']))
        {
            $alert_duration_secounds = $_GET['alert_duration_secounds'];
        }
        #
        # jetzt Logik für die Plausibilität
        #
        # keine Geräte, kein alarm
        if( isset($alert_devices) and strlen($alert_devices) == 0 )
        {
            $alert_enable = 'false';
        }
        # ...

        #
        # zu sendendes Array zusammenbauen
        #
        if(isset($alert_enable)) {$editArray['enable'] = $alert_enable;}
        if(isset($alert_time)) {$editArray['time'] = $alert_time;}
        if(isset($alert_days)) {$editArray['days']= $alert_days;}
        if(isset($alert_date)) {$editArray['date'] = $alert_date;}
        if(isset($alert_source)) {$editArray['source'] = $alert_source;}
        if(isset($alert_raise_vol)) {$editArray['raise_vol'] = $alert_raise_vol;}
        if(isset($alert_volume)) {$editArray['volume'] = $alert_volume;}
        if(isset($alert_devices)) {$editArray['devices'] = $alert_devices;}
        if(isset($alert_source_account)) {$editArray['source_account'] = $alert_source_account;}
        if(isset($alert_note)) {$editArray['note'] = $alert_note;}
        if(isset($alert_type)) {$editArray['type'] = $alert_type;}
        if(isset($alert_location)) {$editArray['location'] = $alert_location;}
        if(isset($alert_duration_secounds)) {$editArray['duration'] = $alert_duration_secounds;}
        #
        # erzeuge die Datenstruktur für das Kommando an den Daemon
        #
        $alertEdArray[] = $editArray;
        $request = array('set' => $alertEdArray );
        #
        # sende das Kommando an den Daemon, 
        # konvertiere dabei die Datenstruktur on-the-fly in JSON String vor dem aufruf
        #
        $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
        #
        # sende das Ergebnis an den Aufrufer zurück
        echo $response;
        return;
    }
    elseif(isset($_GET['delete-alert']))
    {
        $whichAlert = $_GET['delete-alert'];
        $delArray = array();
        $delArr[] = array('alert' => $whichAlert );
        $request = array('delete' => $delArr );
        #
        # sende das Kommando an den Server
        # konvertiere dabei die Datenstruktur on-the-fly in JSON String vor dem Aufruf
        #
        $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
        #
        # sende das Ergebnis an den Aufrufer zurück
        echo $response;
        return;
    }
    else
    {
        #
        # keine bekannte Anforderung eingetroffen, ignorieren und 
        # Fehlermeldung an den Abender schicken
        #
        $response = array('error' => 'wrong request to http-server');
        echo json_encode($response);
        return;
    }
?>