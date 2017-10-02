<?php
    # 09/2017 D. Marciniak
    #
    # Das Script wird nicht direkt vom Benutzer sondern via JavaScript aus der 
    # Webseite aufgerufen und gibt Informationen via JSON zurück, bzw führt 
    # Weckeraktionen aus und gibt Erfolg oder Misserefolg zurück (als JSON String)
    #
    # Konfiguration (config.php) muss vom AUFRUFER GELESEN WORDEN SEIN lesen
    
    if( ! isset ($configObject) )
    {
      include_once "/var/www/html/config/config.php";
    }

    #
    # die Adresse und den Port des soundtouchdaemons holen
    #
    $daddr = $configObject['server_addr'];
    $dport = $configObject['server_port'];
    $dtimeout = getTimeoput($configObject);

     #
    # bestimme aus der Konfiguration den Wert für automatischen Refresh
    # der Wert sol in sekunden zurück gegeben werden
    #
    function getTimeoput( $configArr )
    {
      $regexSec = '/^(\d+)s$/';
      $regexMin = '/^(\d+)m$/';
      $regexHour = '/^(\d+)h$/';
      $timeout_str  = $configArr['network_timeout']; 
      if(preg_match( $regexSec , $timeout_str ))
      {
        # Sekunden
        return( intval(preg_replace($regexSec , '\\1', $timeout_str)));
      }
      if(preg_match( $regexMin , $timeout_str ))
      {
        # Minuten
        return( intval(preg_replace($regexMin , '\\1', $timeout_str))*60);
      }
      if(preg_match( $regexHour , $timeout_str ))
      {
        # Minuten
        return( intval(preg_replace($regexHour , '\\1', $timeout_str))*60*60);
      }
      return($timeout_str);
    }
    
    #
    # Die Funktioen sendet UDP Message an den soundtouch daemon (alarm_clock_bose.py)
    # und erwartet 8 Sekunden lang eine antwort.
    # Dann gibt sie entweder diese Antwort oder eine Fehlermeldung als JSON Objekt zurück
    #
    function sendMessage( $request, $addr, $port, $timeout )
    {
        # und schön geduldig warten
        $recMessage = "";
        $time_to_fail = 0;
        $stat = FALSE;
        # 
        # debugging
        #
        $socket = socket_create(AF_INET, SOCK_DGRAM, SOL_UDP);
        $len = strlen($request);
        # und ab damit
        socket_sendto( $socket, $request, $len, 0, $addr, $port );
        # warte auf Ergebnis...
        $message = "";
        $time_to_fail = time() + $timeout;
        $stat = FALSE;
        while( $time_to_fail > time() && $stat == FALSE)
        {
            $stat = socket_recvfrom( $socket , $message , 2048, MSG_DONTWAIT, $addr, $port );
            # TODO: $stat ist anzahl, $message ist statusmeldung
        }
        socket_close($socket);
        if( $stat == FALSE)
        {
            return( json_encode(array('error' => 'wrong connection')));
        }
        else
        {
            return($message);
        }   
    }

   
?>