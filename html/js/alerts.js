//
// Steuerung der Weckerfunkion von der Website aus
//
var timerInterval = 5000;
var timerIsRunning = false;
var alert_status = '/tools/alerts.php';
var ignoreTrigger = false;
var regexTrue = /true|yes|1|on/;
var timerId = null;

//
// jQuery Mobile: wenn PAGE geänder ist, ausführen...
//
$(document).on('pagecontainershow', changePageAction);

//
// Funktion regelt (wegen des Seiten/DOM Caching von JQuery) die Scripte
// aktiviert die aktuelle und deaktiviert die andere(n) scriptteile
//
function changePageAction(event, ui)
{
  var fromPage = 'none';
  var toPage = 'none';
  //
  // gibt es vorher und oder nachher
  //
  if (ui.toPage != undefined)
  {
    if (ui.toPage[0] != undefined)
    {
      toPage = ui.toPage[0].id;
    }  
  }  
  if (ui.fromPage != undefined)
  {
    if (ui.fromPage[0] != undefined)
    {
      fromPage = ui.fromPage[0].id;
    }  
  }  
  console.log("Changed from Page: " + fromPage + " to Page: " + toPage);
  //
  // zuerst Sachen erledigen, wenn eich eine Seite verlassen habe
  //
  if( fromPage == 'index-page')
  {
    // Auf der Index-Page ein paar Sachen deaktivieren
    //
  }
  else if(fromPage == 'edit-page')
  {
    // auf der EDIT Seite (Dialog) ein paar Sachen aufräumen
    console.debug("deactivate any things on the edit page...");
  }
  //
  // Jetzt die Sachen erledigen, wenn ich die Seite betreten habe
  //
  if(toPage == 'index-page')
  {
    // Auf der Index-Page ein paar Sachen aktivieren
    //
    console.debug("deactivate any things on the index page...");
    initIndexPage();
    startRefreshTimer();
  }
  else if(toPage == 'edit-page')
  {
    console.debug("deactivate any things on the index page...");
    if (timerId != null)
    {
      stopRefreshTimer();
    }      
    // auf der EDIT Seite (Dialog) ein paar Sachen aktivieren
    console.debug("deactivate any things on the edit page...");
    initEditPage();
  } 
  else if(toPage == 'delete-page')
  {
    console.debug("deactivate any things on the index page...");
    if (timerId != null)
    {
      stopRefreshTimer();
    }      
    // auf der EDIT Seite (Dialog) ein paar Sachen aktivieren
    console.debug("deactivate any things on the edit page...");
    initDeletePage();
  }
}

/*#############################################################################
####                                                                       ####
#### INDEX Page für ALARME                                                 ####
####                                                                       ####
#############################################################################*/

//
// initialisiere die INDEX Page
//
function initIndexPage()
{
  console.log("reread alert status via timer ...");
  timerFunc();
  console.log("reread alert status via timer ...OK");

  console.log("init events for all alerts...");
  $('input:button#all-alerts-off').click(switchOffAlerts);
  $('input:button#all-alerts-on').click(switchOnAlerts);
  console.log("init events for all alerts...OK");

  console.log("init events for sigle alerts...");
  $('input:checkbox[id*=alert-]').change(switchAlert);
  console.log("init events for sigle alerts...OK");
}

//
// Starte / Restarte den Refresh Timer für die INDEX Page
//
function startRefreshTimer()
{
  console.debug("initialize autorefresh timer...");
  //
  // ist der hidden input in index.php lesbar
  //
  if ($('input#autorefresh').val() != null)
  {
    if (($('input#autorefresh').val() * 1000) > 2500)
    {
      // kürzer als 2,5 sekunden ist mir zu schnell
      // sonst eben der Vorgabewert
      timerInterval = $('input#autorefresh').val() * 1000;
    }
  }
  console.log("timer loop is " + timerInterval + "ms...");
  console.debug("initialize autorefresh timer...OK");
  if (timerId == null)
  {
    console.log("start timer loop..");
    timerId = setInterval(timerFunc, timerInterval);
    console.log("start timer loop..OK");    
  }  
}

//
// Stoppe den Refresh Timer für die INDEX Seite
//
function stopRefreshTimer()
{
  if (timerId != null)
  {
    console.log("deactivate timer...");
    clearInterval(timerId);
    timerId = null;
  }  
}

//
// Schalte (wenn erforderlich) Alle Alarme an oder aus 
//
function switchOnOffAlert(switch_to)
{
  console.debug("Switch Alert to " + switch_to + "...");
  // Alle checkoxen mid der ID alert-*
  var alArr = $('input:checkbox[id*=alert-]');
  var alNames = '';
  $.each(
    // für jeden einzelnen Alarm durchführen
    alArr, function (i, val)
    {
      var stateBevore = $(val).is(':checked');
      if ($(val).is(':checked') != switch_to)
      {
        // ich muss umschalten
        // setzte die checkbox und löse dann klick und change für die GUI aus um
        // der GUI Nacharbeiten zu gestatten (sonst ist nix zu sehen)
        // ausserdem kann so pysisch die INI geändert werden
        ignoreTrigger = true
        // während dieser Aktion die Events ignorieren, da die Bibliothek 
        // die events (change...) auch selber mehrfach abfeuert
        // das führt zu multiplen aufrufen der Funktion
        $(val).prop('checked', switch_to).trigger('click');
        // change event selber auslösen
        $(val).prop('checked', switch_to).trigger('change');
        ignoreTrigger = false
      }
      //
      // noch eine kommagetrennte Liste mit den Alarmnamen
      //
      if (alNames.length == 0)
      {
        // der erste Wert
        alNames = $(val).attr('id');
      }  
      else
      {
        alNames = alNames + "," + $(val).attr('id');
      }  
    }
  )
  // Jetzt noch dem Server Bescheid stoßen
  console.debug("switchOnOffAlert: '" + alNames + "' to " + switch_to );
  var requestData = { 'setstate': alNames, 'enable': switch_to };
  //
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,           /* die URL */
    requestData,            /* die GET Parameter */
    setStatusDataFunc       /* die "success" Funktion */
  );
  // nochmal sicherstellen dass es geklappt hat
  setTimeout(timerFunc, 500);
  console.debug("Switch Alert to " + switch_to + "...OK");
}

//
// Schalte alle Alarme auf einmal an
//
function switchOnAlerts()
{
  switchOnOffAlert(true);
}

//
// schalte alle Alarme auf einmal AUS
//
function switchOffAlerts()
{
  switchOnOffAlert(false);
}

//
// Event, wenn ein Schalter für Alarm verändert wurde
//
function switchAlert()
{
  if (!ignoreTrigger)
  {
    var newState = "false";
    if ($(this).is(':checked'))
    {
      newState = 'true';
    }
    var alSwitch = $(this).attr('id');
    console.log("ALERT " + alSwitch + " to state: " + newState);
    var requestData = { 'setstate': alSwitch, 'enable': newState };
    //
    // JSON URL aufrufen
    //
    $.getJSON(
      alert_status,           /* die URL */
      requestData,          /* die GET Parameter */
      setStatusDataFunc     /* die "success" Funktion */
    );
  }  
}

//
// die AJAX "success" Funktion wen Ergebnis von SET empfangen wurde
//
function setStatusDataFunc(data)
{
  $.each(data,
    // anonyme Funktion für jedes Paar antwort, kommentar
    function (answer, note)
    {
      console.debug("response: <" + answer + ">, note <" + note + ">");
    }
  );
}

//
// regelmäßiges Update der Slider für die alerts
// (kann ja auch von anderem Clienten verändert werden)
//
function timerFunc()
{
  if (timerIsRunning )
  {
    return;
  }
  timerIsRunning = true;
  console.log("run timerFunc() to reload timer data...");
  //
  // anfrageparameter bauen
  //
  var requestData = { 'getstate': 'all' };
  //
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,           /* die URL */
    requestData,            /* die GET Parameter */
    recStatusDataFunc       /* die "success" Funktion */
  );
  timerIsRunning = false;
}

//
// die AJAX "success" Funktion wenn Statusdaten empfangen wurden
// TODO: wird ein Alarm zugefügt oder entfernt seite komplett neu laden
//
function recStatusDataFunc(data)
{
  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from statusrequest...")
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, alertProps des Objektes "data" via "each" aufgerufen
    function (alert_name, alertProps)
    {
      if (alert_name == 'error')
      {
        console.error("while timerFunc(): error recived!");
      }
      else
      {
        console.debug("recived status: '" + alert_name + "' found. Check for update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        updateAlertSlider(alert_name, alertProps);
        updateAlertTimeStamp(alert_name, alertProps);
      }
    }
  );
  console.debug("recived data from statusrequest...DONE.")
}

//
// setze oder ändere in der INDEX GUI
//
function updateAlertTimeStamp(alert_name, propertys)
{
  // welcher Eintrag ist es
  console.info("alert_name: " + alert_name + ", elem: " + alert_name.replace('alert', 'times'));
  var currAlertTimeElem = $('div#' + alert_name.replace('alert', 'times'));
  var currAlertDateElem = $('div#' + alert_name.replace('alert', 'once'));
  //
  // so, jetzt überlegen was passieren soll
  // Zeit...
  //
  if( currAlertTimeElem.html() != propertys['alert_time'])
  {
    // ok, ich verändere den Wert mal
    console.info("alert_time_name: " + alert_name + ", change content from : " + currAlertTimeElem.html() + " to : " + propertys['alert_time']);
    currAlertTimeElem.text(propertys['alert_time']);
  }
  //
  // Datum
  //
  if( currAlertDateElem.html() != propertys['alert_date'])
  {
    // ok, ich verändere den Wert mal
    console.info("alert_date_name: " + alert_name + ", change content from : " + currAlertDateElem.html() + " to : " + propertys['alert_date']);
    currAlertDateElem.text(propertys['alert_date']);
  }
}

//
// setze wenn verändert den Sliderstatus in der INDEX Gui
//
function updateAlertSlider(alert_name, propertys)
{
  // welcher ist das?
  var currSlider = $('input#' + alert_name);
  //
  // so, jetzt überlegen was passieren soll
  //
  var alarmIsActive = regexTrue.test(propertys['enable']);
  //
  // wenn enable verändert ist
  //
  if (currSlider.is(':checked') != alarmIsActive)
  {
    console.log("switch for " + alert_name + " was changed, trigger switch...");
    ignoreTrigger = true
    currSlider.prop('checked', !alarmIsActive).trigger('click');
    ignoreTrigger = false
  }
  //
  // TODO: Weckzeit, Weckdatum, Titel (note) verändert
  // oder Tiemr dazu/entfernt
  //
}

/*#############################################################################
####                                                                       ####
#### EDIT Page für ALARME                                                  ####
####                                                                       ####
#############################################################################*/

//
// initialisiere die EDIT Page
//
function initEditPage()
{
  var alertName = $('input#alert-name').val();
  console.debug('edit page for alert: ' + alertName);
  console.debug("init edit page bindings...");
  //
  // Funktion beim setzten eines Datums
  //
  $('input:text#date-picker').bind('datebox', function (event, passed)
  {
    if( passed.method != undefined && passed.method == 'set')
    {
      console.debug('new DATE set: value: ' + passed.value);
    }
    else if ( passed.method != undefined && passed.method == 'clear')
    {
      console.debug('DATE CLEAR');
    }
    /*
    var date = $('input:text#date-picker').datebox('getTheDate');
    var datestr = date.getFullYear() + "-" + date.getMonth() + "-" + date.getDate();
    var datestr2 = date.toJSON()
    console.debug("datestring: " +  datestr );
    console.debug("datestring JSON: " +  datestr2 );
    */
  });
  //
  // Funktion beim setzten einer Zeit
  //
  $('input:text#time-picker').bind('datebox', function (event, passed)
  {
    if( passed.method != undefined && passed.method == 'set')
    {
      console.debug('new TIME set: value: ' + passed.value);
    }
    /*
    var date = $('input:text#time-picker').datebox('getTheDate');
    var datestr = date.getFullYear() + "-" + date.getMonth() + "-" + date.getDate();
    var datestr2 = date.toJSON()
    console.debug("timestring: " +  datestr );
    console.debug("timestring JSON: " +  datestr2 );
    */
  });
  // 
  // Initiiere das Update der Werte in der EDIT GUI
  // (ASYNCRON)
  //
  updateEditGUI(alertName);
  //
  // Funktion beim klick auf SICHERN
  //
  $('a#save-alert').click(saveAlertValues);
}

//
// hole die aktuellen Einstellugnen des Alarms
//
function updateEditGUI(alertName)
{
  console.log('ask alert properties (' + alertName + ')...');
  //
  // anfrageparameter bauen
  //
  //var alertArr = Array([alertName, ' ']);
  var requestData = { 'getstate': alertName };
  //
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,           /* die URL */
    requestData,            /* die GET Parameter */
    recAlertStatusData      /* die "success" Funktion */
  );
}

//
// Die Funktion, welche beim Empfang der Daten für den alarm 
// aufgerufen wird
//
function recAlertStatusData(data)
{
  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from statusrequest...")
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen, kann hie reigentlichn ur der eine, gesuchte sein
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, alertProps des Objektes "data" via "each" aufgerufen
    function (alert_name, propertys)
    {
      if (alert_name == 'error')
      {
        console.error("while updateEditGUI(): error recived!");
      }
      else
      {
        console.debug("recived status: '" + alert_name + "' found. Update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        $('input#time-picker').datebox('setTheDate', propertys['alert_time'] /*'formatted string'*/);
        $('input#date-picker').datebox('setTheDate', propertys['alert_date'] /*'formatted string'*/);
        //
        // Wochentage durchlaufen
        // 
        daysArr = propertys['days'].split(',');
        // Jetzt für alle Tage prüfen und setzen
        var d_checked = false;
        // Montag
        if( $.inArray('mo', daysArr) > -1 ) {d_checked = true;} else { d_checked = false; }
        $('input#cb-monday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        // Dienstag
        if( $.inArray('tu', daysArr) ) {d_checked = true;} else { d_checked = false;}
        $('input#cb-tuesday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        // Mittwoch
        if( $.inArray('we', daysArr) ) {d_checked = true;} else { d_checked = false;}
        $('input#cb-wednesday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        // Donnerstag
        if( $.inArray('th', daysArr) ) {d_checked = true;} else { d_checked = false;}
        $('input#cb-thursday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        // Freitag
        if( $.inArray('fr', daysArr) ) {d_checked = true;} else { d_checked = false;}
        $('input#cb-friday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        // Samstag
        if( $.inArray('sa', daysArr) ) {d_checked = true;} else { d_checked = false;}
        $('input#cb-saturday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        // Sonntag
        if( $.inArray('so', daysArr) ) {d_checked = true;} else { d_checked = false;}
        $('input#cb-sunday').attr('checked', 'checked', d_checked).checkboxradio('refresh');
        //
        // Jetzt Sender wählen, vorerst geht nur PRESET_1 bis PRESET_6
        // ist RADIO, sollte also immer nur einer aktiviert sein
        //
        var editSource = propertys['source'];
        if( editSource.match(/^PRESET_[123456]$/))
        {
          console.debug('source matches PRESET: ' + propertys['source'] );
          if(propertys['source'] == 'PRESET_1') {$('input#rad-preset-1').attr('checked', 'checked', true).checkboxradio('refresh');}
          else if(editSource == 'PRESET_2') {$('input#rad-preset-2').attr('checked', 'checked', true).checkboxradio('refresh');}
          else if(editSource == 'PRESET_3') {$('input#rad-preset-3').attr('checked', 'checked', true).checkboxradio('refresh');}
          else if(editSource == 'PRESET_4') {$('input#rad-preset-4').attr('checked', 'checked', true).checkboxradio('refresh');}
          else if(editSource == 'PRESET_5') {$('input#rad-preset-5').attr('checked', 'checked', true).checkboxradio('refresh');}
          else if(editSource == 'PRESET_6') {$('input#rad-preset-6').attr('checked', 'checked', true).checkboxradio('refresh');}
          }
        else
        {
          console.debug('source: ' + propertys['source'] );
          console.error('not an predefined source in config. others not supported yet. set to preset 1')          
          $('input#rad-preset-1').attr('checked', 'checked', true).checkboxradio('refresh');
        }
        //
        // GERÄTE
        // TODO: das mit den vorhandenen abgleichen
        //
        var availDevicesInputs = $('fieldset#devicesgroup > div > input');
        console.debug("input list: " + availDevicesInputs.length + " elems")
        var tempAlarmDevices = propertys['devices'].split(',');
        var alarmDevices = Array();
        console.debug("devices list: '" + propertys['devices'] + "'")
        for( var idx=0; idx < tempAlarmDevices.length; idx++ )
        {
          alarmDevices[idx] = tempAlarmDevices[idx].trim().replace(" ", "_" );
        }

        //
        // durchsuche die verfügbaren Geräte aus der Seite und 
        // finde heraus ob der alarm ein oder mehrere Geräte davon haben will
        //
        for( var idx = 0; idx < availDevicesInputs.length; idx++ )
        {
          _avDevice = availDevicesInputs[idx];
          _avDeviceId = _avDevice.id;
          var currentDeviceInput = $('fieldset#devicesgroup > div > input'+ _avDeviceId);
          if($.inArray(_avDeviceId, alarmDevices) > -1 )
          {
            console.debug("Device: " + _avDeviceId + " is in avaivible devices.");
            $('input#'+ _avDeviceId).attr('checked', 'checked', d_checked).checkboxradio('refresh');
          }
          else
          {
            console.debug("Device: " + _avDeviceId + " is NOT in avaivible devices.");
            $('input#'+ _avDeviceId).removeAttr('checked').checkboxradio('refresh');
          }
        }
        //
        // Lautstärke
        //
        $('input#volume-sl').val(propertys['volume']);
        //
        // Lautstärke einblenden oder nicht
        //
        $('input#raise_vol').prop('checked', propertys['raise_vol']);
      }
    }
  );
  console.debug("recived data from statusrequest...DONE.")
}


//
// Funktion zum sichern eines ALARMES
//
function saveAlertValues()
{
  var whichAlert = $('input#alert-name');
  console.debug('ALERT NAME: ' + whichAlert.val()); //$('input#alert-name').val() );
}

/*#############################################################################
####                                                                       ####
#### DELETE Page für ALARME                                                ####
####                                                                       ####
#############################################################################*/

function initDeletePage()
{
  console.log("initDeletePage()...");
  var alertName = $('input#alert-name').val();
  $('a#delete-alert').click(doDeleteAlert);
  updateDeleteGUI(alertName);
}

//
// lösche den Alarm nun wirklich
//
function doDeleteAlert()
{
  var alertName = $('input#alert-name').val();
  //
  // lösche den Alarm von der Konfiguration
  //
  console.log('delete alert ' + alertName + ' from config...');
  deleteAlertFromConfig(alertName);
  console.log('delete alert ' + alertName + ' from config...');
  //
  // lade die INDEX Seite NEU
  //
  console.log('change page to index...');
  $.mobile.changePage("index.php", { transition: "flip", changeHash: true, reloadPage: true } );
  console.log('change page to index...OK');
}

//
// löschen dann den Alarm ndgültig
//
function deleteAlertFromConfig(alertName)
{
  
  console.log('alert delete call (' + alertName + ')...');
  //
  // anfrageparameter bauen
  //
  var requestData = { 'delete-alert': alertName };
  //
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,                 /* die URL */
    requestData,                  /* die GET Parameter */
    recAlertDelete                /* die "success" Funktion */
  );
}

function recAlertDelete(data)
{

  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from deleterequest...")
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen, kann hie reigentlichn ur der eine, gesuchte sein
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, alertProps des Objektes "data" via "each" aufgerufen
    function (alert_name, propertys)
    {
      if (alert_name == 'error')
      {
        console.error("while deleteAlertFromConfig(): error recived!");
      }
      else
      {
        console.debug("delete: '" + alert_name + "' OK");
      }
    }
  );
  console.debug("recived data from deleterequest...")
}


//
// hole die aktuellen Einstellugnen des Alarms
//
function updateDeleteGUI(alertName)
{
  
  console.log('ask alert properties (' + alertName + ')...');
  //
  // anfrageparameter bauen
  //
  var requestData = { 'getstate': alertName };
  //
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,                 /* die URL */
    requestData,                  /* die GET Parameter */
    recAlertDeleteStatusData      /* die "success" Funktion */
  );
}

//
// Die Funktion, welche beim Empfang der Daten für den alarm 
// aufgerufen wird
//
function recAlertDeleteStatusData(data)
{
  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from statusrequest...")
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen, kann hie reigentlichn ur der eine, gesuchte sein
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, alertProps des Objektes "data" via "each" aufgerufen
    function (alert_name, propertys)
    {
      if (alert_name == 'error')
      {
        console.error("while updateDeleteGUI(): error recived!");
      }
      else
      {
        console.debug("recived status: '" + alert_name + "' found. Update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        $('input#delete-alert-time').val(propertys['alert_time']);
        $('input#delete-alert-date').val(propertys['alert_date']);
      }
    }
  );
  console.debug("recived data from statusrequest...DONE.")
}


