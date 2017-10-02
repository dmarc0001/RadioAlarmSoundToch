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
    if( isset($_GET["getstate"]) )
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
            # hier können mehrere "Channels" mit Komma getrennt
            # angegeen worden sein, packe in ein array
            #
            $relArray = explode(",", $whichAlerts);
            $getArray = array();
            foreach( $relArray as $alert )
            {
                $getArray[] = array('alert' => $alert );
            }
            #
            # erzeuge die datenstruktur für eine Anfrage beim Relaisdaemon
            #
            $request = array('get' => $getArray );
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
            # erzeuge die Datenstruktur für das Kommando an den Relaisaemon
            #
            $request = array('set' => $getArray );
            #
            # sende das Kommando an den Relaisserver, 
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
    else
    {
        #
        # keine bekannte Anforderung eingetroffen, ignorieren und 
        # Fehlermeldung an den Abender schicken
        #
        $response = array('error' => 'wrong request');
        echo json_encode($response);
        return;
    }
?>