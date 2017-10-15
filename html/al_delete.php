<?php
  # starte zuerst eine Session, später geht das nicht mehr
  session_start();
  # 09/2017 D. Marciniak
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

  if( isset($_GET["alert"]) )
  {
      #
      # Information abfordern
      #
      $whichAlert = $_GET["alert"];
      #
      # erfrage die aktuelle Konfiguration vom soundtouch date_timezone_get
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
      }
  }
  #
  # Nornal oder Fehler?
  #
  if( ! $showErrorPage )
  {
?>
  <body>
    <div data-role="page" id="delete-page" data-dialog="true" data-overlay-theme="d" data-theme="d">
      <input type="hidden" id="alert-name" value="<?php echo $whichAlert; ?>" /> 
      <div data-role="header">
        <!-- /header -->
        <h1><?php echo $alertConfig['note']?></h1>
      </div>
      
      <div role="main" class="ui-content">
        <!-- content -->
        <div class="ui-grid-solo">
          <div class="ui-block-a">
            <!-- Uhrzeit -->
            <div>Weckzeit</div>
            <input type="text" id="delete-alert-time" />
          
            <!-- an welchem Datum - dann ist das einmalig -->
            <div>Weckdatum</div>
            <input type="text" id="delete-alert-date" />
            
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
            <a href="#" id="delete-alert" data-role="button" class="ui-shadow ui-btn ui-corner-all " data-transition="flip"><b>L Ö S C H E N...</b></a>
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
