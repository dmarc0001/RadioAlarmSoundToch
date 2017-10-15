//
// Steuerung der Weckerfunkion von der Website aus
//
var timerInterval = 5000;
var timerIsRunning = false;
var alert_status = '/tools/alerts.php';
var alert_index = 'index.php';
var ignoreTrigger = false;
var regexTrue = /true|yes|1|on/;
var timerId = null;
var configId = 0;
var editDate = null;
var regex_date = /^\d{4}-\d{2}-\d{2}$/;
var regex_time = /^\d{2}:\d{2}$/;
var regex_sec = /^(\d+)s$/i;
var regex_min = /^(\d+)m$/i;
var regex_std = /^(\d+)h$/i;
var regex_val = /^(\d+).*$/i;

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
  console.log("init index page...");
  console.debug("reread alert status via timer ...");
  timerFunc();
  console.debug("reread alert status via timer ...OK");

  console.debug("init events for all alerts...");
  $('input:button#make-new-alert').click(makeNewAlert)
  $('input:button#all-alerts-off').click(switchOffAlerts);
  $('input:button#all-alerts-on').click(switchOnAlerts);
  console.debug("init events for all alerts...OK");

  console.debug("init events for sigle alerts...");
  $('input:checkbox[id*=alert-]').change(switchAlert);
  console.debug("init events for sigle alerts...OK");
  console.log("init index page...OK");
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
  console.log("refresh timer loop is " + timerInterval + "ms...");
  console.debug("initialize autorefresh timer...OK");
  if (timerId == null)
  {
    console.debug("start timer loop..");
    timerId = setInterval(timerFunc, timerInterval);
    console.debug("start timer loop..OK");    
  }  
}

//
// Stoppe den Refresh Timer für die INDEX Seite
//
function stopRefreshTimer()
{
  if (timerId != null)
  {
    console.log("deactivate refresh timer...");
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
    console.debug("ALERT " + alSwitch + " to state: " + newState);
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
      console.debug("setstate response: <" + answer + ">, note <" + note + ">");
    }
  );
}

//
// regelmäßig gucken, ob configänderungen entstanden sind
//
function timerFunc()
{
  if (timerIsRunning )
  {
    return;
  }
  timerIsRunning = true;
  console.debug("run timerFunc() to check for reload config...");
  //
  // anfrageparameter bauen
  //
  var requestData = { 'getconfigid': 'true' };
  //
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,           /* die URL */
    requestData,            /* die GET Parameter */
    recCheckUpdateFunc      /* die "success" Funktion */
  );
  timerIsRunning = false;
  console.debug("run timerFunc() to reload config...OK");
}

//
// AJAX Antwortfunktion, ermittelt die aktuelle Version der Config
//
function recCheckUpdateFunc(data)
{
  // configId
  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from config version request...");
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, value des Objektes "data" via "each" aufgerufen
    function(value_name, value)
    {
      if (value_name == 'error')
      {
        console.error("while timerFunc(): error recived!");
      }
      else
      {
        if( configId != value )
        {
          //
          // Oh, da muss was gemacht werden, also komplettes update versuchen
          // TODO: Komplett neuladen oder update?
          //
          console.log("new config id recived (" + value + "). Update GUI...");
          configId = value;
          updateFunc();
        }
      }
    }
  );
  console.debug("recived data from config version request...OK");
}

//
// Update der Slider/Datumsangaben für die alerts
// (kann ja auch von anderem Clienten verändert werden)
//
function updateFunc()
{
  if (timerIsRunning )
  {
    return;
  }
  timerIsRunning = true;
  console.debug("run updateFunc() to reload config data to GUI...");
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
  console.debug("recived data from updateFunc...")
  // 
  // checke ob die alarme weiniger/mehr oder einer komplett verändert ist
  //
  if( hasAlertsCountChanged(data) )
  {
    console.warn("alerts has strong changed, reload complete...");
    loadPageWithoutCache( alert_index );
    return;
  }
  //
  // ich mache doch eher ein update
  // zunächst ebene 1 durchlaufen, die Alarmnamen
  //
  $.each(data,
    // anonyme Funktion für jedes Paar value_name, value des Objektes "data" via "each" aufgerufen
    function (value_name, value)
    {
      if (value_name == 'error')
      {
        console.error("while updateFunc(): error recived!");
        loadPageWithoutCache( alert_index );
        return;
      }
      else
      {
        console.debug("recived status: '" + value_name + "' found. Check for update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        updateAlertSlider(value_name, value);
        updateAlertTimeStamp(value_name, value);
      }
    }
  );
  console.debug("recived data from statusrequest...DONE.")
}

//
// erkenne, ob sich Anzahl oder Namen der Alarme verändert haben
//
function hasAlertsCountChanged( data )
{
  _retValue = false;
  $.each(data,
    // anonyme Funktion für jedes Paar value_name, value des Objektes "data" via "each" aufgerufen
    function (value_name, value)
    {
      if( _retValue )
      {
        // da war schon ein Fehler, den rest kann ich dann sparen
        return;
      }
      if(value_name == 'error')
      {
        console.error("while updateFunc(): error recived!");
        _retValue = true;
        return;
      }
      else
      {
        console.debug("check if is '" + value_name + "' in DOM...");
        if( $('hr#' + value_name).length == 0 )
        {
          console.info("'" + value_name + "' is NOT in DOM, alerts have changed!");
          _retValue = true;
          return;
          }
        console.debug("check if alerts name is changed...");
        if( $('label#' + value_name).length == 0 )
        {
          console.info("label for alert '" + value_name + "' is NOT in DOM, alerts have changed!");
          _retValue = true;
          return;
          }
        if( $('label#' + value_name).html() != value['note'] )
        {
          console.info("label for alert '" + value_name + "' has changed, alerts have changed!");
          _retValue = true;
          return;
        }
      }
    }
  );
  return(_retValue);
}

//
// setze oder ändere in der INDEX GUI
//
function updateAlertTimeStamp(value_name, propertys)
{
  // welcher Eintrag ist es
  console.debug("value_name: " + value_name + ", elem: " + value_name.replace('alert', 'times'));
  var currAlertDateElem = $('div#' + value_name.replace('alert', 'dates'));
  var currAlertTimeElem = $('div#' + value_name.replace('alert', 'times'));
  var currAlertDateTitleElem = $('div#' + value_name.replace('alert', 'dates-title'));
  //
  // so, jetzt überlegen was passieren soll
  // Zeit verändert?
  //
  if( currAlertTimeElem.html() != propertys['time'] ) 
  {
    _timestr = propertys['time'];
    if( propertys['time'].length > 0 && propertys['time'].match(regex_time) )
    {
      // ZEIT, also an verschiedenen Tagen
      console.debug("alert: " + value_name + ", set : " + currAlertTimeElem.html() + " to : " + propertys['time']);
      currAlertTimeElem.text(propertys['time']);
    }
    else
    {
      console.warn("alert: " + value_name + ", has no time in params! display warning!");
      currAlertTimeElem.text('- ??? -');
    }
  }
  //
  // Datum oder Tage?
  //
  if( propertys['date'].length > 0 && propertys['date'].match(regex_date) )
  {
    // DATUM, also auch einmalig
    // teste nicht auf Änderung, einfach neu setzten...
    //
    console.debug("alert: " + value_name + ", set alert date to " +  propertys['date']);
    currAlertDateTitleElem.text('Datum:');
    currAlertDateElem.text(propertys['date']);
    return;
  }
  //
  // dan kann ja nur noch Tage da sein
  //
  if( propertys['days'].length > 1 )
  {
    console.debug("alert: " + value_name + ", set alert days to " +  propertys['days']);
    currAlertDateTitleElem.text('Tage:');
    currAlertDateElem.text(propertys['days']);
    return;
  }
  //
  // NOTFALL, nix zum eintragen
  //
  currAlertDateTitleElem.text('REPEAT:');
  currAlertDateElem.text('- ??? -');
}

//
// setze wenn verändert den Sliderstatus in der INDEX Gui
//
function updateAlertSlider(value_name, propertys)
{
  // welcher ist das?
  var currSlider = $('input#' + value_name);
  //
  // so, jetzt überlegen was passieren soll
  //
  var alarmIsActive = regexTrue.test(propertys['enable']);
  //
  // wenn enable verändert ist
  //
  if (currSlider.is(':checked') != alarmIsActive)
  {
    console.debug("switch for " + value_name + " was changed, trigger switch...");
    ignoreTrigger = true
    currSlider.prop('checked', !alarmIsActive).trigger('click');
    ignoreTrigger = false
  }
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
  console.log('init edit page for alert: ' + alertName + "...");
  console.debug("init edit page bindings...");
  // leeren...
  editDate = null;
  //
  // Funktion beim setzten eines Datums
  //
  $('input:text#date-picker').bind('datebox', function (event, passed)
  {
    if( passed.method != undefined && passed.method == 'set')
    {
      editDate = passed.value;
      console.debug('new DATE set: value: ' + passed.value);
    }
    else if ( passed.method != undefined && passed.method == 'clear')
    {
      // gewärleistet, dass Datum wirklich gelöscht wird
      editDate = null;
      console.debug('DATE CLEAR');
    }
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
  console.log('init edit page for alert: ' + alertName + "...OK");
}

//
// hole die aktuellen Einstellugnen des Alarms
//
function updateEditGUI(alertName)
{
  console.debug('ask alert properties (' + alertName + ')...');
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
  console.debug("recived data from updateEditGUI...")
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen, kann hie reigentlichn ur der eine, gesuchte sein
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, value des Objektes "data" via "each" aufgerufen
    function (value_name, propertys)
    {
      if (value_name == 'error')
      {
        console.error("while updateEditGUI(): error recived!");
      }
      else
      {
        console.debug("recived status: '" + value_name + "' found. Update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        $('input#time-picker').datebox('setTheDate', propertys['time'] );
        if(propertys['date'].length > 4 )
        {
          $('input#date-picker').datebox('setTheDate', propertys['date'] );
        }
        else
        {
          editDate = null;
          $('input#date-picker').val('');
        }
        //
        // Wochentage durchlaufen
        // 
        daysArr = propertys['days'].split(',');

        // Jetzt für alle Tage prüfen und setzen
        // Montag
        if( $.inArray('mo', daysArr) > -1 ) { editCheckboxState( $('input#cb-monday'), true ); } else { editCheckboxState( $('input#cb-monday'), false ); }
        // Dienstag
        if( $.inArray('tu', daysArr) > -1 ) { editCheckboxState( $('input#cb-tuesday'), true ); } else { editCheckboxState( $('input#cb-tuesday'), false ); }
        // Mittwoch
        if( $.inArray('we', daysArr) > -1 ) { editCheckboxState( $('input#cb-wednesday'), true ); } else { editCheckboxState( $('input#cb-wednesday'), false ); }
        // Donnerstag
        if( $.inArray('th', daysArr) > -1 ) { editCheckboxState( $('input#cb-thursday'), true ); } else { editCheckboxState( $('input#cb-thursday'), false ); }
        // Freitag
        if( $.inArray('fr', daysArr) > -1 ) { editCheckboxState( $('input#cb-friday'), true ); } else { editCheckboxState( $('input#cb-friday'), false ); }
        // Samstag
        if( $.inArray('sa', daysArr) > -1 ) { editCheckboxState( $('input#cb-saturday'), true ); } else { editCheckboxState( $('input#cb-saturday'), false ); }
        // Sonntag
        if( $.inArray('su', daysArr) > -1 ) { editCheckboxState( $('input#cb-sunday'), true ); } else { editCheckboxState( $('input#cb-sunday'), false ); }
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
            editCheckboxState( $('input#'+ _avDeviceId), true );
          }
          else
          {
            console.debug("Device: " + _avDeviceId + " is NOT in avaivible devices.");
            editCheckboxState( $('input#'+ _avDeviceId), false );
          }
        }
        //
        // Lautstärke
        //
        $('input#volume-sl').val(propertys['volume']).slider('refresh');
        //
        // Lautstärke einblenden oder nicht
        //
        editCheckboxState( $('input#raise_vol'), propertys['raise_vol'] == 'true' );
        //
        // Dauer des Weckens (5 bis 60 Minuten)
        // Angabe ohne Wert oder s == Sekunden, m Minuten, h stunden
        //
        var currentDuration = getSecondsFromString( propertys['duration'] );
        if( currentDuration < ( 5 * 60 ) )
        {
          // Minimalzeit braucht es ja schon...
          currentDuration = 5 * 60;
        }
        if( currentDuration > ( 60 * 60 ) )
        {
          // maximal eine Stunde bittesehr
          currentDuration = 60 * 60;
        }
        // bereit den slider zu setzten...
        var durationMinutes = currentDuration / 60;
        $('input#alert-duration').val(durationMinutes).slider('refresh');
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
  var propertyArray = new Object();

  console.log('SAVE ALERT: ' + whichAlert.val() + "..."); 
  //
  // Datum und Zeit, falls gesetzt
  //
  var dateTime = $('input#time-picker').datebox('getTheDate');
  propertyArray.alert_time = dateTime.getHours() + ":" + dateTime.getMinutes();
  if( editDate == null )
  {
    propertyArray.alert_date = "null";  
  }
  else
  {
    propertyArray.alert_date = editDate;
  }
  //
  // Wochentage, falls gesetzt
  //
  var weekDays = new Array();
  if( $('input#cb-monday').is(':checked') )
  {
    weekDays.push('mo');
  }
  if( $('input#cb-tuesday').is(':checked') )
  {
    weekDays.push('tu');
  }
  if( $('input#cb-wednesday').is(':checked') )
  {
    weekDays.push('we');
  }
  if( $('input#cb-thursday').is(':checked') )
  {
    weekDays.push('th');
  }
  if( $('input#cb-friday').is(':checked') )
  {
    weekDays.push('fr');
  }
  if( $('input#cb-saturday').is(':checked') )
  {
    weekDays.push('sa');
  }
  if( $('input#cb-sunday').is(':checked') )
  {
    weekDays.push('su');
  }
  propertyArray.alert_days = weekDays.join();
  if( propertyArray.alert_days.length == 0 )
  {
    propertyArray.alert_days = 'null';
  }
  //
  // SOURCE rausfinden
  //
  $("input[name*=rad-presets]:checked").each(
    //
    // Kann bei RADIO ja nur einer sein...
    //
    function () 
    {
      var alertId = $(this).attr('id');
      propertyArray.alert_source = alertId.replace('rad-preset-', 'PRESET_');
    }
  );
  //
  // Geräte herausfinden
  //
  var devicesArray = new Array();
  $('input[name*=alert-device]:checked').each(
    //
    // abgehakt...
    //
    function()
    {
      devicesArray.push($(this).attr('id'));
    }
  );
  propertyArray.alert_devices = devicesArray.join();
  if( propertyArray.alert_devices.length == 0 )
  {
    propertyArray.alert_devices = 'null';
  }
  //
  // alarm volume
  //
  propertyArray.alert_volume = $('#volume-sl').val();
  //
  // ansteigender alarm
  //
  propertyArray.alert_raise_vol = $('input#raise_vol').is(':checked');
  //
  // alarmlänge, der slöider speichert in minuten...
  //
  propertyArray.alert_duration = $('input#alert-duration').val() + "m";
  //
  // anfrageparameter bauen
  //
  propertyArray['edit-alert'] = whichAlert.val();
  console.log("requestData: <" + $.param(propertyArray) + ">");
  requestData = $.param(propertyArray);
  // JSON URL aufrufen
  //
  $.getJSON(
    alert_status,           /* die URL */
    requestData,            /* die GET Parameter */
    recAlertSave            /* die "success" Funktion */
  );
  console.log('SAVE ALERT: ' + whichAlert.val() + "...OK"); 
 
}

//
// Callback Funktion beim sichern eines alarmes
//
function recAlertSave(data)
{
  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from saverequest...")
  //
  // zunächst ebene 1 durchlaufen, die Alarmnamen, kann hie reigentlichn ur der eine, gesuchte sein
  //
  $.each(data,
    // anonyme Funktion für jedes Paar alert, value des Objektes "data" via "each" aufgerufen
    function (value_name, propertys)
    {
      if (value_name == 'error')
      {
        console.error("while saveAlertValues(): error recived!");
      }
      else
      {
        console.debug("save: '" + value_name + "' OK");
      }
    }
  );
  console.debug("recived data from saverequest...OK")
}

/*#############################################################################
####                                                                       ####
#### NEUER ALARM                                                           ####
####                                                                       ####
#############################################################################*/
function makeNewAlert()
{
  console.error('NEW ALERT: not implemented yet');
  alert('neuer ALARM -> rufe edit mit neuem alarm auf...');
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
  console.log("initDeletePage()...OK");
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
  console.debug('delete alert ' + alertName + ' from config...');
  deleteAlertFromConfig(alertName);
  console.debug('delete alert ' + alertName + ' from config...');
  //
  // lade die INDEX Seite NEU
  //
  console.debug('change page to index...');
  loadPageWithoutCache( alert_index );
  console.debug('change page to index...OK');
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
  console.log('alert delete call (' + alertName + ')...OK');
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
    // anonyme Funktion für jedes Paar alert, value des Objektes "data" via "each" aufgerufen
    function (value_name, propertys)
    {
      if (value_name == 'error')
      {
        console.error("while deleteAlertFromConfig(): error recived!");
      }
      else
      {
        console.debug("delete: '" + value_name + "' OK");
      }
    }
  );
  console.debug("recived data from deleterequest...")
}


//
// hole die aktuellen Einstellugnen des Alarms vor dem löschen zur Anzeige
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
  console.log('ask alert properties (' + alertName + ')...OK');
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
    // anonyme Funktion für jedes Paar alert, value des Objektes "data" via "each" aufgerufen
    function (value_name, propertys)
    {
      if (value_name == 'error')
      {
        console.error("while updateDeleteGUI(): error recived!");
      }
      else
      {
        console.debug("recived status: '" + value_name + "' found. Update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        $('input#delete-alert-time').val(propertys['time']);
        $('input#delete-alert-date').val(propertys['date']);
      }
    }
  );
  console.debug("recived data from statusrequest...DONE.")
}


/*#############################################################################
####                                                                       ####
#### UTILITY Funktionen                                                    ####
####                                                                       ####
#############################################################################*/

//
// wechsle ohne caching zur neuen Seite mit transistion
//
function loadPageWithoutCache( pageUrl )
{
  var _nocache = "?nocache=" + Date.now();
  this.document.location.href = pageUrl + _nocache;  
}

//
// Funktion zum setzen/loschen einer Checkbox
//
function editCheckboxState( checkboxElem, newState )
{
  if( newState )
  {
    // checkbox zu CHECKED
    checkboxElem.attr('checked', 'checked', true ).checkboxradio('refresh');
  }
  else
  {
    // checkbox unchcecked
    checkboxElem.removeAttr('checked').checkboxradio('refresh');
  }
}

//
// gib aus einem String a la 30s oder 10m die Sekunden zurück
//
function getSecondsFromString( secStr )
{
  if(secStr.match(regex_sec))
  {
    return(secStr.match(regex_val)[1]); 
  }
  if(secStr.match(regex_min))
  {
    return( secStr.match(regex_val)[1] * 60 ); 
  }
  if(secStr.match(regex_std))
  {
    return(secStr.match(regex_val)[1] * 60 * 60 ); 
  }
  if(secStr.match(regex_val))
  {
    return(secStr); 
  }
  console.error( "time distance string (" + secStr + ") is not an valid string");
  return(0);
}

