<?php
    # starte zuerst eine Session, später geht das nicht mehr
    session_start();
    # lies die Konfiguration ein
    include_once "config/config.php";
    include_once "tools/daemon_comm.php";

    include "inc/std_headers.php";

    #
    # bestimme aus der Konfiguration den Wert für automatischen Refresh
    # der Wert sol in sekunden zurück gegeben werden
    #
    function getAutoRefresh( $configArr )
    {
      $regexSec = '/^(\d+)s$/';
      $regexMin = '/^(\d+)m$/';
      $regexHour = '/^(\d+)h$/';
      $a_refresh_str = $configArr['autorefresh']; 
      if(preg_match( $regexSec , $a_refresh_str ))
      {
        # Sekunden
        return( intval(preg_replace($regexSec , '\\1', $a_refresh_str)));
      }
      if(preg_match( $regexMin , $a_refresh_str ))
      {
        # Minuten
        return( intval(preg_replace($regexMin , '\\1', $a_refresh_str))*60);
      }
      if(preg_match( $regexHour , $a_refresh_str ))
      {
        # Minuten
        return( intval(preg_replace($regexHour , '\\1', $a_refresh_str))*60*60);
      }
      return($a_refresh_str);
    }


    #
    # gib einen Weckereintrag aus
    #
    function printAlertBlock( $configArr )
    {
      #
      # zunächst mal starres Layout mit zwei Spalten
      #
      # mit zwei Spalten im GRID ist das a und b
      $blockArr = array('a', 'b');
      $blockNr = 0;
      # beginne mit Nummer 0
      $alertNumber = 0;
      # rein optisch, leerzeichen erzeugen für das debuggen übersichtlicher
      $insertCount = 10;
      # eröffne das Gitter (CSS-Grid)
      printf( "\n%".$insertCount.'s<div class="ui-grid-b ui-responsive">' . "\n", " ");
      # weiter einrücken
      $insertCount += 2;
      #
      # die Alarme aus der Knofiguration lesen
      #
      $alerts = preg_grep( "/^alert-\d+$/", array_keys( $configArr ) );
      # 
      # Alle Geräte via foreach durchackern
      #
      sort($alerts);
      foreach( $alerts as $alert )
      {
        # switchnummer aus der Kanalnummer extraieren
        $alertNumber = intval( str_replace( "alert-", "", $alert ) );
        #
        # filter_var($configArr[$alert]['enable'], FILTER_VALIDATE_BOOLEAN) )
        # welcher Block (Spalte)
        $blockName = $blockArr[$blockNr];
        printf( "%".$insertCount."s<div class=\"ui-block-%s\">\n", " ", $blockName);
        $insertCount += 2;
        printf( "%".$insertCount."s<hr class=\"alert-border\"/>\n", " ");
        printf( "%".$insertCount."s<label for=\"alert-%02d\">%s</label>\n", " ", $alertNumber, $configArr[$alert]['note']);
        printf( "%".$insertCount.'s<input type="checkbox" data-role="flipswitch" name="alert-%02d" id="alert-%02d" data-on-text="AN" data-off-text="AUS" data-wrapper-class="custom-label-flipswitch" />'."\n", " ", $alertNumber, $alertNumber );
        printf( "%".$insertCount.'s<a href="al_edit.php?alert=alert-%02d" role="button" id="edit-alert-%02d" class="ui-shadow ui-btn ui-corner-all ui-btn-inline ui-mini" data-transition="flip">bearbeiten</a>'."\n", " ", $alertNumber, $alertNumber );
        printf( "%".$insertCount."s<br />\n", " " );
        # Uhrzeit
        printf( "%".$insertCount."s<div class=\"leftcol\">Weckzeit</div>\n", " ", $alertNumber );
        printf( "%".$insertCount."s<div class=\"rightcol\" id=\"times-%02d\">%s</div>\n", " ", $alertNumber, $configArr[$alert]['alert_time'] );
        printf( "%".$insertCount."s<br />\n", " " );
        # Tage / immer / einmalig
        if( isset( $configArr[$alert]['alert_date'] ) )
        {
          # ein einmaliger Alarm
          printf( "%".$insertCount."s<div class=\"leftcol\">Weckdatum</div>\n", " ", $alertNumber );
          printf( "%".$insertCount."s<div class=\"rightcol\" id=\"once-%02d\">%s</div>\n", " ", $alertNumber, $configArr[$alert]['alert_date'] );
          printf( "%".$insertCount."s<br />\n", " " );
        }
        else
        {
          # täglich oder wochentage
          printf( "%".$insertCount."s<div class=\"leftcol\">Weckdatum</div>\n", " ", $alertNumber );
          # TODO: wochentage
          printf( "%".$insertCount."s<div class=\"rightcol\" id=\"once-%02d\">%s</div>\n", " ", $alertNumber, $configArr[$alert]['days'] );
          printf( "%".$insertCount."s<br />\n", " " );
        }
        printf( "%".$insertCount."s<br />\n", " ");          
        $insertCount -= 2;  
        printf( "%".$insertCount."s</div>\n", " ");
        $alertNumber++;
        #
        # Blocknummer umschalten
        #
        $blockNr++;
        if( $blockNr >= count($blockArr) )
        {
          $blockNr = 0;
        }
      }
      $insertCount -= 2;
      # switchblöcke ENDE
      # schließe das Gitter (CSS-Grid)
      printf( '%'.$insertCount."s</div>\n\n", " ");
    }

    #
    # erfrage die aktuelle Konfiguration vom soundtouch
    #
    $request = array('get' => array('config'));
    # sende an daemon und warte
    $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
    $progConfigObject = json_decode( $response, true );
?>
  <body>
    <div data-role="page" id="index-page" data-theme="<?php echo $configObject['gui_theme']; ?>" >
      <input type="hidden" id="autorefresh" value="<?php echo getAutoRefresh($configObject); ?>" /> 

      <div data-role="header">
        <!-- /header -->
        <h1>Unser Radiowecker</h1>
      </div>
    
      <div role="main" class="ui-content">
          <!-- content -->
          <?php
            if( isset( $progConfigObject['error'] ))
            {
              echo "          <h1 style=\"color:red;\">ERROR: ".$progConfigObject['error']."</h1>\n";
            }
            else
            {
              printAlertBlock( $progConfigObject );
            }
          ?>
          <!-- alle Wecker auf AUS -->
          <div class="ui-grid-solo">
            <div class="ui-block-a">
              <input type="button" id="all-alerts-off" value="ALLE AUS" />
            </div>
          </div>
          <!-- schalte für alle ZU -->
          <div class="ui-grid-solo">
              <div class="ui-block-a">
                <input type="button" id="all-alerts-on" value="ALLE AN" />
              </div>
          </div>
          <hr />
          Petra und Dirk RADIOWECKER
          <!-- content -->
    </div>
    
      <div data-role="footer">
        <h4>BOSE Sound Touch Geräte</h4>
      </div><!-- /footer -->
    </div><!-- /page -->
  </body>
</html>