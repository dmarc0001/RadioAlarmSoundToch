<?php
    #
    # parse die Konfigurationsdatei und erzeuge das config objekt
    #
    
    $configFile = "/var/www/config/alert.ini";
    # scanne mit sections
    #$configObject = parse_ini_file( $configFile, true );

    #
    # zunächst: ich brauche nur den global Bereich, der Rest kommt vom soundtouch date_timezone_get
    #
    $temp_configObject = parse_ini_file( $configFile, true );
    if( isset($temp_configObject['global']))
    {
        $configObject = $temp_configObject['global'];
    }


    #print_r( $temp_configObject );
    #print_r( $configObject );

?>


