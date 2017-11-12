<?php
  # starte zuerst eine Session, später geht das nicht mehr
  session_start();
  #
  # 11/2017 D. Marciniak
  #
  # Das Script wird nicht direkt vom Benutzer sondern via JavaScript aus der 
  # Webseite aufgerufen 
  #

  # Konfiguration bearbeiten
  include_once "tools/daemon_comm.php";
  # header einfügen
  include "inc/std_headers.php";   
  #erst mal vom Fehler ausgehen
  $showErrorPage = true;
  $alertNote = 'NAMENLOS';

  if( isset($_GET["alert"]) )
  {
      #
      # Information abfordern
      #
      $whichAlert = trim($_GET["alert"]);
      if( strcmp($whichAlert, 'new') != 0 )
      {
        #
        # erfrage die aktuelle Konfiguration, falls es den Alarm gibt
        # vom soundtouch date_timezone_get
        #
        $request = array('get' => array($whichAlert));
        # sende an daemon und warte
        $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
        # Antwort ist ein JSON array mit einem Eintrag (ist ja nur einer angefordert)
        $answerAlert = json_decode( $response, true );
        # TODO: wenn $answerAlert[0] error ist
        if( ! isset($answerAlert['error']) )
        {
          $alertConfig = $answerAlert[$whichAlert];
          $showErrorPage = false;
          if( isset($alertConfig['note']) )
          {
            $alertNote = $alertConfig['note'];
          }
        }
      }
      # 
      # verfügbare geräte abfragen
      #
      $request = array('get' => array('devices'));
      # sende an daemon und warte
      $response = sendMessage( json_encode($request), $daddr, $dport, $dtimeout );
      # Antwort ist ein JSON array mit einem Eintrag (ist ja nur einer angefordert)
      $answerDevices = json_decode( $response, true );
      if( ! isset($answerDevices['error']) )
      {
        $showErrorPage = false;
      }  
  }
  #
  # Nornal oder Fehler?
  #
  if( ! $showErrorPage )
  {
?>
  <body>
    <div data-role="page" id="edit-page" data-dialog="true" data-overlay-theme="<?php echo $configObject['gui_theme']; ?>" 
         data-theme="<?php echo $configObject['gui_theme']; ?>">
      <input type="hidden" id="alert-name" value="<?php echo $whichAlert; ?>" /> 
      <div data-role="header">
        <!-- /header -->
        <h1><?php echo $alertNote; ?></h1>
      </div>
      
      <div role="main" class="ui-content">
        <!-- content -->
        <div class="ui-grid-solo">
          <div class="ui-block-a">
            <!-- Name des alarms -->
            <label for="alert-note">Weckername</label>
            <input type="text" data-clear-btn="true" name="alert-note" id="alert-note" value="<?php echo $alertNote; ?>" />
            <!-- Uhrzeit -->
            <div>Weckzeit</div>
            <input type="text" id="time-picker" data-role="datebox" 
              data-options='{"mode": "timeflipbox",  "usePlaceholder": "Weckzeit", "overrideDateFormat": "%H:%M", "showInitialValue": "true", "useLang":"de" }'>
            </input>
          
            <!-- an welchem Datum - dann ist das einmalig -->
            <div>Weckdatum</div>
            <input type="text" id="date-picker" data-role="datebox" 
              data-options='{"mode": "calbox", "overrideDateFormat": "%d.%m.%Y", "usePlaceholder": "Datum", 
                "afterToday": "true", "useClearButton": "true", "showInitialValue": "true", "useLang":"de" }'>
            </input>
            
            <!-- an welchen Wochentagen - wenn kein Datum gesetzt ist -->
            <div data-role="collapsible" data-mini="false" data-collapsed="true" 
              data-collapsed-icon="carat-d" data-expanded-icon="carat-u" data-iconpos="right">
              <h4>Wochentage</h4>
              <form>
                <fieldset data-role="controlgroup-1">
                  <input type="checkbox" name="cb-monday" id="cb-monday" />
                  <label for="cb-monday">Montag</label>
                  <input type="checkbox" name="cb-tuesday" id="cb-tuesday" />
                  <label for="cb-tuesday">Dienstag</label>
                  <input type="checkbox" name="cb-wednesday" id="cb-wednesday" />
                  <label for="cb-wednesday">Mittwoch</label>
                  <input type="checkbox" name="cb-thursday" id="cb-thursday" />
                  <label for="cb-thursday">Donnerstag</label>
                  <input type="checkbox" name="cb-friday" id="cb-friday" />
                  <label for="cb-friday">Freitag</label>
                  <input type="checkbox" name="cb-saturday" id="cb-saturday" />
                  <label for="cb-saturday">Samstag</label>
                  <input type="checkbox" name="cb-sunday" id="cb-sunday" />
                  <label for="cb-sunday">Sonntag</label>
                </fieldset>
              </form>
            </div>
            
            <!-- Was soll gespielt werden - zunächst nur PRESET -->
            <div data-role="collapsible" data-mini="false" data-collapsed="true" 
              data-collapsed-icon="carat-d" data-expanded-icon="carat-u" data-iconpos="right">
              <h4>Sender</h4>
              <form>
                <input type="radio" name="rad-presets" id="rad-preset-1" />
                <label for="rad-preset-1">STATION 1</label>
                <input type="radio" name="rad-presets" id="rad-preset-2" />
                <label for="rad-preset-2">STATION 2</label>
                <input type="radio" name="rad-presets" id="rad-preset-3" />
                <label for="rad-preset-3">STATION 3</label>
                <input type="radio" name="rad-presets" id="rad-preset-4" />
                <label for="rad-preset-4">STATION 4</label>
                <input type="radio" name="rad-presets" id="rad-preset-5" />
                <label for="rad-preset-5">STATION 5</label>
                <input type="radio" name="rad-presets" id="rad-preset-6" />
                <label for="rad-preset-6">STATION 6</label>
              </form>
            </div>

            <!-- welche Geräte -->
            <div data-role="collapsible" data-mini="false" data-collapsed="true" 
              data-collapsed-icon="carat-d" data-expanded-icon="carat-u" data-iconpos="right">
              <h4>Geräte</h4>
              <form>
                <fieldset id="devicesgroup" data-role="controlgroup-2">
<?php
  # 
  # lies vom Daemon die verfügbaren Geräte ein
  #
  foreach( $answerDevices as $devName => $propertys )
  {
    $insertCount = 18;
    $devId = strtolower(str_replace(" ", '_', $devName));
    printf( '%'.$insertCount.'s<input type="checkbox" name="alert-device" id="%s" real_name="%s" />'."\n", ' ', $devId, $devName );
    printf( '%'.$insertCount.'s<label for="%s">%s</label>'."\n", ' ', $devId, $devName );    
  }
?>
                </fieldset>
              </form>
            </div>
            
            <!-- Lautstärke -->
            <form>
              <label for="volume-sl">Lautstärke</label>
              <input type="range" name="volume-sl" id="volume-sl" min="0" max="100" value="1" data-highlight="true" data-popup-enabled="true" />
              <!-- sanft wecken? -->
              <input type="checkbox" name="raise_vol" id="raise_vol" />
              <label for="raise_vol">Sanft wecken</label>
              <!-- Weckdauer -->
              <label for="alert-duration">Weckdauer</label>
              <input type="range" name="alert-duration" id="alert-duration" min="5" max="60" value="50" data-highlight="true" data-popup-enabled="true" />
            </form>
          </div>
        </div>
        <div class="ui-grid-solo">
          <div class="ui-block-a">
          <hr />
          </div>
        </div>

        <!-- Daten sichern -->
        <div class="ui-grid-solo">
          <div class="ui-block-a">
            <a href="index.php" id="save-alert" data-role="button" class="ui-shadow ui-btn ui-corner-all " data-transition="flip">SICHERN...</a>
          </div>
        </div>
        <!-- zurück ohne Speichern -->
        <div class="ui-grid-solo">
          <div class="ui-block-a">
            <a href="index.php" data-role="button" data-rel="back" class="ui-shadow ui-btn ui-corner-all " data-transition="flip">ABBRUCH</a>
          </div>
        </div>
        <!-- content -->
      </div>
      
      <div data-role="footer">
        <h4>BOSE Sound Touch Geräte</h4>
      </div><!-- /footer -->
    </div><!-- /page -->
  </body>
<?php
  }
  else
  {
    // Fehlerseite, kein Parameter
?>
  <body>
    <div data-role="page" id="edit-page" data-dialog="true" data-overlay-theme="d" data-theme="d">
      <div data-role="header">
        <!-- /header -->
        <h1>FEHLER</h1>
      </div>
      
      <div role="main" class="ui-content">
        <!-- content -->
        <div class="ui-grid-solo">
          <div class="ui-block-a">
            <h3><?php print_r($answerAlert['error']); ?></h3>
          </div>
        </div>
        <hr />

        <!-- Zurück -->
        <div class="ui-grid-solo">
          <div class="ui-block-a">
            <a href="index.php" data-role="button" data-rel="back" class="ui-shadow ui-btn ui-corner-all " data-transition="flip">ZURÜCK</a>
          </div>
        </div>
        <!-- content -->
      </div>
      
      <div data-role="footer">
        <h4>BOSE Sound Touch Geräte</h4>
      </div><!-- /footer -->
    </div><!-- /page -->
  </body>
<?php
  }
?>
</html>
