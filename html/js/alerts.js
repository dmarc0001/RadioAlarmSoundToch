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
  
}

//
// initialisiere die EDIT Page
//
function initEditPage()
{
  console.debug("init edit page bindings...");
  $('input:text#date-picker').bind('datebox', function (e, passed)
  {
    console.debug('New Date Shown: ' + passed.shownDate);
    console.debug('Date Selected: ' + passed.selectedDate);
  });
  $('input:text#time-picker').bind('datebox', function (e, passed)
  {
    console.debug('New Date Shown: ' + passed.shownDate);
    console.debug('Date Selected: ' + passed.selectedDate);
  });
}

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
// Stoppe den Refresh Timer für dei INDEX Seite
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
//
function recStatusDataFunc(data)
{
  //
  // bei diesem response ist die Verschachtelung der Objekte 2 Ebenen
  // Ebene 1 == key: section/alert, value: Objekt mit Werteparen
  // Ebene 2 == key: Wertename: value: Wert
  //
  console.debug("recived data from statusrequest...")
  // prüfe für alle Kanäle, ob da noch was im transfer ist
  var isInTransfer = false;
  //
  // zunächst ebene 1 durchlaufen, die Kanalnamen
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
        console.debug("recived status: '" + alert_name + "' found. Checkk for update...");
        // Ebene 2, für den Kanal das Objekt der Wertepaare durchlaufen
        updateAlertSlider(alert_name, alertProps);
        updateAlertTimeStamp(alert_name, alertProps);
      }
    }
  );
  console.debug("recived data from statusrequest...DONE.")
}

//
// setze oder ändere Weckzeit
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
// setze wenn verändert den Sliderstatus
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


