// Kleine Helfer der Grundgestaltung (#7). Ohne Skript bleibt alles bedienbar (#281); am Handy
// öffnet das Skript das Menü von links, statt ans Seitenende zu springen.
(function () {
  "use strict";

  // Kurze Seite beim Abmelden (#280): Ihr Formular bringt das Kennungs-Token zu Keycloak und
  // schickt sich sofort selbst ab, damit niemand einen Knopf mehr drücken muss. Ohne Skript
  // bleibt der Knopf. Es steht hier und nicht in der Seite, weil Skripte nur aus Dateien des
  // eigenen Servers kommen sollen (#278). Es steht am Anfang, damit kein
  // Fehler in einem späteren Teil das Abmelden aufhält.
  document.querySelectorAll("form[data-sofort-absenden]").forEach(function (form) {
    form.submit();
  });

  // Handy-Menü: Der Browser hält den Fokus im geöffneten Dialog und schließt ihn mit Escape.
  // Dazu kommen: Schließen-Knopf, Antippen daneben und Rückkehr des Fokus auf „Menü“.
  var menu = document.getElementById("menue");
  var openButton = document.getElementById("menue-auf");
  var closeButton = document.getElementById("menue-zu");
  if (menu && openButton && closeButton && typeof menu.showModal === "function") {
    // Ohne Skript springt „Menü“ ans Seitenende zur Liste (#281). Mit Skript gibt es Sprung und Liste
    // nicht mehr, auch wenn das Skript erst nach dem Sprung kommt; der Knopf tritt an die Stelle des Sprungs.
    var jump = document.getElementById("menue-sprung");
    var listBelow = document.getElementById("menue-unten");
    var jumpHadFocus = jump && jump === document.activeElement;
    if (jump) {
      jump.remove();
    }
    if (listBelow) {
      listBelow.remove();
    }
    openButton.hidden = false;
    if (jumpHadFocus) {
      openButton.focus();
    }
    openButton.addEventListener("click", function () {
      menu.showModal();
    });
    closeButton.addEventListener("click", function () {
      menu.close();
    });
    menu.addEventListener("click", function (event) {
      if (event.target === menu) {
        menu.close();
      }
    });
    menu.addEventListener("close", function () {
      openButton.focus();
    });
  }

  // Fehlerseiten (#21): „Zurück“ nur, wenn die vorige Seite eine Seite des Tools war, damit
  // der Knopf nie ins Leere oder auf eine fremde Seite führt. Fremde Seiten nennt der Browser
  // wegen der Referrer-Policy „same-origin“ meist gar nicht; eine fremde Seite kann das aber
  // für sich selbst ausdrücklich erlauben, deshalb wird hier trotzdem verglichen. Der Knopf
  // lädt die vorige Seite neu, wie es die Seite „Formular abgelaufen“ verlangt.
  var back = document.querySelector("a[data-zurueck]");
  var previous = null;
  try {
    previous = document.referrer ? new URL(document.referrer) : null;
  } catch (error) {
    previous = null;
  }
  if (back && previous && previous.origin === window.location.origin) {
    back.href = previous.href;
    back.hidden = false;
  }

  // Zahl der Zeichen (#215) unter Feldern mit fachlicher Grenze („data-hoechstens“): beim Tippen
  // „12/30“, zu lang rot mit der Meldung „zu lang“ darunter. Nichts wird abgeschnitten, Speichern
  // bleibt möglich; der Server prüft wie bisher. Gezählt wird wie dort (`trimmed()` und `len()` in
  // Python): ohne Leerzeichen am Rand, auch unsichtbare, und je Unicode-Zeichen, sodass ein Emoji
  // eins zählt und ein zerlegter Umlaut zwei. Python kennt \x1c-\x1f und \x85 als Leerraum,
  // JavaScripts \s nicht; deshalb stehen sie hier eigens. Die Zahl ist mit der Eingabe verknüpft,
  // wird aber nicht bei jedem Tastendruck angesagt; die Meldung nur, wenn sie erscheint.
  // Programmgesteuerte Änderungen (Verwerfen, ×) lösen deshalb selbst ein „input“ aus.
  var EDGE_SPACES = /^[\s\x1c-\x1f\x85­᠎​-‍⁠﻿]+|[\s\x1c-\x1f\x85­᠎​-‍⁠﻿]+$/g;

  function describedBy(input, id, linked) {
    var ids = (input.getAttribute("aria-describedby") || "").split(" ").filter(function (each) {
      return each && each !== id;
    });
    if (linked) {
      ids.unshift(id);
    }
    if (ids.length) {
      input.setAttribute("aria-describedby", ids.join(" "));
    } else {
      input.removeAttribute("aria-describedby");
    }
  }

  document.querySelectorAll("input[data-hoechstens]").forEach(function (input) {
    var counter = document.getElementById(input.id + "-zahl");
    if (!counter) {
      return;
    }
    var limit = parseInt(input.getAttribute("data-hoechstens"), 10);
    var tooLong = input.getAttribute("data-zu-lang");
    var errorId = input.id + "-fehler";
    var shown = counter.querySelector("[aria-hidden]");
    var spoken = counter.querySelector(".sr-nur");

    function update() {
      var count = Array.from(input.value.replace(EDGE_SPACES, "")).length;
      var over = count > limit;
      shown.textContent = count + "/" + limit;
      spoken.textContent = counter.getAttribute("data-vorlesen").replace("{anzahl}", count);
      counter.classList.toggle("ist-zu-lang", over);
      // Die Meldung „zu lang“ ist dieselbe wie vom Server; andere Fehler am Feld bleiben stehen.
      var error = document.getElementById(errorId);
      if (over && !error) {
        error = document.createElement("div");
        error.className = "invalid-feedback";
        error.id = errorId;
        error.setAttribute("role", "alert");
        error.textContent = tooLong;
        counter.after(error);
      } else if (!over && error && error.textContent.trim() === tooLong) {
        error.remove();
        error = null;
      }
      input.classList.toggle("is-invalid", !!error);
      if (error) {
        input.setAttribute("aria-invalid", "true");
      } else {
        input.removeAttribute("aria-invalid");
      }
      describedBy(input, errorId, !!error);
    }

    input.addEventListener("input", update);
    update();
    counter.hidden = false;
  });

  // Feld zum Antippen (#180, Zielbild „Mein Profil“): In Ruhe zeigt es den gespeicherten Wert
  // wie eine Angabe; Antippen öffnet die Eingabe mit „Verwerfen“ und „Speichern“. Gespeichert
  // wird wie ohne Skript mit dem Formular, also nur mit „Speichern“ oder Enter. Verwerfen geht
  // mit dem Knopf, mit Escape oder mit Tippen außerhalb. Ohne Skript bleiben Eingabe und
  // „Speichern“ einfach stehen (core/templates/core/_antippfeld.html).
  document.querySelectorAll("[data-antippfeld]").forEach(function (box) {
    var rest = box.querySelector("[data-oeffnen]");
    var clear = box.querySelector("[data-leeren]");
    var discard = box.querySelector("[data-verwerfen]");
    var editor = box.querySelector(".a-antippfeld-eingabe");
    var input = editor.querySelector("input");
    var buttons = box.querySelector(".a-antippfeld-knoepfe");
    var label = box.querySelector("label");
    var announcer = box.querySelector("[data-ansage]");
    var counter = box.querySelector(".a-zeichenzahl");
    var saved = box.getAttribute("data-gespeichert") || "";
    var isOpen = false;

    // Erst leeren, dann kurz danach setzen: So sagen Vorleseprogramme auch denselben Satz zweimal an.
    function say(text) {
      announcer.textContent = "";
      window.setTimeout(function () {
        announcer.textContent = text;
      }, 50);
    }

    function show(open) {
      isOpen = open;
      rest.hidden = open;
      editor.hidden = !open;
      buttons.hidden = !open;
      box.classList.toggle("ist-offen", open);
      // Die Zahl der Zeichen (#215) steht nur bei offener Eingabe.
      if (counter) {
        counter.hidden = !open;
      }
      clear.disabled = open ? input.value === "" : saved === "";
    }

    // Der Fehler gehört zur verworfenen Eingabe und verschwindet mit ihr.
    function forgetError() {
      var error = box.querySelector(".invalid-feedback");
      if (error) {
        describedBy(input, error.id, false);
        error.remove();
      }
      input.classList.remove("is-invalid");
      input.removeAttribute("aria-invalid");
      // Eine Fehlermeldung nach gescheitertem Speichern bleibt stehen (#186) und mit der Eingabe verknüpft,
      // ebenso die Zahl der Zeichen.
      var failure = box.querySelector(".a-meldung.ist-fehler");
      if (failure) {
        describedBy(input, failure.id, true);
      }
    }

    // Wie Tippen: Die Zahl der Zeichen und der Knopf × passen sich an.
    function setValue(value) {
      input.value = value;
      input.dispatchEvent(new Event("input"));
    }

    function open() {
      show(true);
      input.focus();
      input.select();
    }

    // Der Fokus geht zurück aufs Feld, außer jemand hat außerhalb etwas anderes angetippt,
    // das den Fokus selbst nimmt, etwa einen Link.
    function close(keepFocusElsewhere) {
      setValue(saved);
      forgetError();
      show(false);
      if (!keepFocusElsewhere) {
        rest.focus();
      }
      say(box.getAttribute("data-ansage-verworfen"));
    }

    rest.hidden = false;
    clear.hidden = false;
    discard.hidden = false;
    box.classList.add("ist-bereit");

    rest.addEventListener("click", open);
    label.addEventListener("click", function (event) {
      if (!isOpen) {
        event.preventDefault();
        open();
      }
    });
    // Leeren löscht nichts selbst: Es öffnet das Feld leer, gelöscht wird erst mit „Speichern“.
    clear.addEventListener("click", function () {
      show(true);
      setValue("");
      input.focus();
      say(box.getAttribute("data-ansage-geleert"));
    });
    input.addEventListener("input", function () {
      clear.disabled = input.value === "";
    });
    discard.addEventListener("click", function () {
      close(false);
    });
    // Escape wirkt auch, wenn der Fokus mit Tab schon aus dem offenen Feld hinaus ist.
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && isOpen) {
        event.preventDefault();
        close(false);
      }
    });
    // „pointerdown“ statt „click“: Safari am iPhone meldet ein Antippen von Flächen ohne eigene
    // Funktion (Überschrift, leerer Rand) nicht als Klick. Ob das Angetippte den Fokus selbst
    // nimmt, steht am Ziel fest; Safari gibt angeklickten Knöpfen und Links keinen Fokus.
    // Den Fokus erst danach zurückgeben: Das Antippen selbst nimmt ihn sonst gleich wieder weg.
    document.addEventListener("pointerdown", function (event) {
      if (isOpen && !box.contains(event.target)) {
        close(true);
        if (!event.target.closest("a, button, input, select, textarea, label, [tabindex]")) {
          window.setTimeout(function () {
            rest.focus();
          }, 0);
        }
      }
    });

    // Nach einem Fehler kommt das Feld offen vom Server, nach dem Speichern mit dem Fokus darauf.
    // Scheiterte das Speichern, zeigt der Bildschirm das Feld mit der Fehlermeldung darunter (#186).
    if (box.hasAttribute("data-offen")) {
      show(true);
      if (box.querySelector(".a-meldung.ist-fehler")) {
        input.focus({ preventScroll: true });
        box.scrollIntoView({ block: "center" });
      } else {
        input.focus();
      }
    } else {
      show(false);
      if (box.hasAttribute("data-fokus")) {
        rest.focus();
      }
    }
  });

  // Kurze Meldungen (#186, docs/gestaltung.md): Eine Meldung mit „data-kurz“ (Erfolg oder Information
  // nach einer eigenen Handlung) wandert in den Bereich unten. Dort sagen Vorleseprogramme sie an, ohne
  // dass der Cursor sich bewegt, und nach rund 6 Sekunden verschwindet sie. Solange die Maus über einer
  // Meldung oder der Fokus darin ist, bleiben alle stehen und zählen danach neu. Höchstens drei, die
  // neueste unten. Ohne Skript oder ohne Bereich (Login-Seite) bleibt sie fest, wo sie steht.
  var shortArea = document.getElementById("kurzmeldungen");
  var SHORT_TIME = 6000;
  var SHORT_MOST = 3;
  // Erst kurz nach dem Laden einblenden: Vorleseprogramme sagen nur an, was nach dem Bereich selbst
  // dazukommt.
  var SHORT_DELAY = 100;
  var FADE_TIME = 200;
  // Stehen die Meldungen gerade still (Maus oder Fokus darauf)? Nur dann zählen sie danach neu.
  var shortPaused = false;

  function shortOpen() {
    return Array.prototype.slice.call(shortArea.querySelectorAll(".a-kurz:not(.ist-weg)"));
  }

  function shortHeld() {
    return shortArea.matches(":hover") || shortArea.contains(document.activeElement);
  }

  function shortCount(notice) {
    window.clearTimeout(notice.kurzUhr);
    notice.kurzUhr = window.setTimeout(function () {
      shortFade(notice);
    }, SHORT_TIME);
  }

  // Lag der Fokus in der Meldung, geht er dorthin zurück, wo er war, als sie erschien.
  function shortRemove(notice) {
    var hadFocus = notice.contains(document.activeElement);
    window.clearTimeout(notice.kurzUhr);
    notice.remove();
    if (hadFocus && notice.kurzHer && notice.kurzHer.isConnected) {
      notice.kurzHer.focus();
    }
    // Mit der Meldung verschwinden oft Maus oder Fokus aus dem Bereich, ohne dass der Browser es meldet.
    shortGoOn();
  }

  function shortFade(notice) {
    notice.classList.add("ist-weg");
    window.setTimeout(function () {
      shortRemove(notice);
    }, FADE_TIME);
  }

  function shortShow(notice) {
    notice.removeAttribute("role");
    notice.classList.add("a-kurz");
    notice.kurzHer = document.activeElement === document.body ? null : document.activeElement;
    var close = notice.querySelector(".a-kurz-zu");
    close.hidden = false;
    close.addEventListener("click", function () {
      shortRemove(notice);
    });
    shortArea.appendChild(notice);
    var open = shortOpen();
    if (open.length > SHORT_MOST) {
      shortRemove(open[0]);
    }
    if (shortHeld()) {
      shortPaused = true;
    } else {
      shortCount(notice);
    }
  }

  function shortHold() {
    shortPaused = true;
    shortOpen().forEach(function (notice) {
      window.clearTimeout(notice.kurzUhr);
    });
  }

  function shortGoOn() {
    window.setTimeout(function () {
      if (shortPaused && !shortHeld()) {
        shortPaused = false;
        shortOpen().forEach(shortCount);
      }
    }, 0);
  }

  if (shortArea) {
    document.querySelectorAll("[data-kurz]").forEach(function (notice) {
      notice.remove();
      window.setTimeout(function () {
        shortShow(notice);
      }, SHORT_DELAY);
    });
    shortArea.addEventListener("mouseover", shortHold);
    shortArea.addEventListener("mouseout", shortGoOn);
    shortArea.addEventListener("focusin", shortHold);
    shortArea.addEventListener("focusout", shortGoOn);

    // Bausteinkatalog: Knöpfe blenden Beispiele aus Vorlagen ein, mehrere kurz nacheinander.
    document.querySelectorAll("[data-kurz-zeigen]").forEach(function (button) {
      button.addEventListener("click", function () {
        button.getAttribute("data-kurz-zeigen").split(" ").forEach(function (name, index) {
          window.setTimeout(function () {
            var example = document.getElementById(name).content.querySelector("[data-kurz]");
            shortShow(example.cloneNode(true));
          }, index * 700);
        });
      });
    });
  }

  // Gliederung (#189): Ist sie kürzer als der Baum und rollt innen, steht die geöffnete
  // Organisation beim Laden im sichtbaren Teil. Nur die Gliederung rollt, nie die Seite selbst.
  var outline = document.querySelector(".a-gliederung-rolle");
  var current = outline && outline.querySelector("[aria-current]");
  if (current && outline.scrollHeight > outline.clientHeight) {
    var offset = current.getBoundingClientRect().top - outline.getBoundingClientRect().top;
    outline.scrollTop += offset - outline.clientHeight / 3;
  }

  // Stelle merken (#220): Jeder Dialog hat eine eigene Adresse (#190); Öffnen, Schließen und Speichern laden
  // die Seite neu, und sie stünde danach oben. Deshalb merkt sich die Seite bei jedem Link und Formular, wie
  // weit sie gerollt war, und die nächste Seite stellt das wieder her, aber nur, wenn sie von genau dieser
  // Seite kommt (`document.referrer`) und es um einen Dialog geht: Die neue Seite zeigt einen Dialog (Öffnen,
  // „Suchen“, Ablehnung im Dialog), oder die vorige zeigte einen und die neue ist die Seite darunter
  // (Schließen, Speichern). Eine andere Seite, etwa die neue Veranstaltung, beginnt oben; ebenso, wer eine
  // Seite später über einen Link, die Navigation oder die Adresse öffnet. Gemerkt wird je Tab und nur für
  // den nächsten Seitenwechsel. Ist die Seite kürzer geworden, begrenzt der Browser die Stelle aufs Ende.
  // Ohne Skript springen die Seiten stattdessen zum Abschnitt mit dem Knopf („#abschnitt-…“, core/sections.py);
  // mit Skript fällt diese Sprungmarke weg, bevor die Seite wechselt, damit sie nicht dorthin springt.
  var SPOT_KEY = "dialog-stelle";
  var openDialog = document.querySelector("dialog[data-dialog]");

  function withoutJump(address) {
    var at = address.indexOf("#abschnitt-");
    return at < 0 ? address : address.slice(0, at);
  }

  function pathOf(address) {
    return new URL(address, window.location.href).pathname;
  }

  function rememberSpot() {
    try {
      window.sessionStorage.setItem(SPOT_KEY, JSON.stringify({
        y: window.scrollY,
        title: document.title,
        from: window.location.href.split("#")[0],
        below: openDialog ? pathOf(openDialog.getAttribute("data-schliessen")) : null,
      }));
    } catch (error) {
      // Ist der Speicher im Browser gesperrt, beginnt die Seite oben wie früher.
    }
  }

  function recallSpot() {
    var spot = null;
    try {
      spot = JSON.parse(window.sessionStorage.getItem(SPOT_KEY));
      window.sessionStorage.removeItem(SPOT_KEY);
    } catch (error) {
      return null;
    }
    if (!spot || typeof spot.y !== "number" || document.referrer.split("#")[0] !== spot.from) {
      return null;
    }
    // Gleicher Pfad heißt nicht gleiche Seite: Wer seine Verbandsleitung abgibt, sieht unter „/organisation/“
    // danach die Seite seines Stamms. Der Titel unterscheidet sie; ein Dialog trägt den Titel der Seite darunter.
    if (openDialog || (spot.below === window.location.pathname && spot.title === document.title)) {
      return spot.y;
    }
    return null;
  }

  var spot = recallSpot();

  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("a[href]") : null;
    // Mit Strg, Cmd oder Umschalt öffnet der Link einen neuen Tab oder ein neues Fenster; die Seite hier bleibt.
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    link.setAttribute("href", withoutJump(link.getAttribute("href")));
    rememberSpot();
  });
  document.addEventListener("submit", function (event) {
    var form = event.target;
    var action = form.getAttribute("action");
    if (action) {
      form.setAttribute("action", withoutJump(action));
    }
    rememberSpot();
  });

  // Dialog (#190): Er kommt offen vom Server und hat eine eigene Adresse. Mit Skript wird er modal: Der
  // Browser hält den Fokus darin, und Escape oder Tippen daneben führen wie × und „Abbrechen“ zurück zur
  // Seite darunter. Ohne Skript liegt er einfach über der Seite.
  document.querySelectorAll("dialog[data-dialog]").forEach(function (dialog) {
    var back = withoutJump(dialog.getAttribute("data-schliessen"));
    if (typeof dialog.showModal !== "function") {
      return;
    }
    dialog.close();
    dialog.showModal();
    var first = dialog.querySelector("[autofocus]");
    if (first) {
      first.focus({ preventScroll: spot !== null });
    }
    function leave() {
      rememberSpot();
      window.location.href = back;
    }
    dialog.addEventListener("cancel", function (event) {
      event.preventDefault();
      leave();
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        leave();
      }
    });
  });

  // Zurück aus einem Dialog (#117): Führt der Dialog zur Seite mit der Kennung eines Knopfs in der Adresse
  // („#…“), etwa „Bearbeiten“ bei einer verwalteten Person, bekommt dieser Knopf wieder den Fokus. Ohne
  // Skript beginnt die Tastatur dort, weil der Browser zu ihm springt. Mit gemerkter Stelle (#220) springt
  // die Seite dabei nicht zum Knopf.
  if (window.location.hash.length > 1 && !openDialog) {
    var returnTo = document.getElementById(window.location.hash.slice(1));
    if (returnTo && returnTo.matches("a[href], button")) {
      returnTo.focus({ preventScroll: spot !== null });
    }
    // Safari rollt nach dem Laden noch selbst weich zur Kennung in der Adresse, auch nach dem Zurückrollen.
    // Mit gemerkter Stelle fällt die Kennung deshalb aus der Adresse; der Fokus liegt schon auf dem Knopf.
    if (spot !== null) {
      window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
    }
  }

  // „instant“: Bootstrap lässt die Seite sonst weich rollen, und man sähe sie von oben zur Stelle fahren.
  if (spot !== null) {
    window.scrollTo({ top: spot, behavior: "instant" });
  }

  // Adressfeld am Handy (#400): Dort klebt die Kopfleiste oben. Nach „Adresse suchen“ rollte der Browser zum Fokus
  // auf Treffern oder Meldung (`autofocus`), und wo „Straße und Hausnummer“ dann stand, war Zufall, manchmal halb
  // unter der Leiste. Deshalb setzt das Skript den Fokus selbst, ohne zu rollen, und stellt die Seite so, dass die
  // Straße direkt unter der Leiste beginnt; passt so der Anfang der Treffer oder der Meldung nicht ins Bild, rollt es
  // nur so weit, dass er unten im Bild steht, denn der Fokus liegt nie außerhalb (WCAG 2.4.11). Am Ende der Seite hält
  // der Browser früher an; die Straße steht dann tiefer, aber ganz im Bild. Am PC (dort klebt keine Leiste) und im
  // Dialog bleibt es beim Browser, ebenso ohne Skript. Nach „Übernehmen“ gilt der nächste Abschnitt (#410).
  var topbar = document.querySelector(".a-topbar");
  var GAP = 8;
  var stickyTopbar = topbar && window.getComputedStyle(topbar).position === "sticky";
  var addressFocus = document.querySelector(".a-adressfeld [autofocus]");
  var streetInput = addressFocus && addressFocus.closest(".a-adressfeld").querySelector("[name='street']");
  var street = streetInput && streetInput.closest(".a-textfeld");
  if (stickyTopbar && street && addressFocus.matches(".a-adresse-ergebnis") && !addressFocus.closest("dialog")) {
    addressFocus.focus({ preventScroll: true });
    var below = topbar.getBoundingClientRect().bottom + GAP;
    var target = window.scrollY + street.getBoundingClientRect().top - below;
    var resultStart = addressFocus.querySelector(".a-treffer") || addressFocus.firstElementChild || addressFocus;
    target = Math.max(target, window.scrollY + resultStart.getBoundingClientRect().bottom + GAP - window.innerHeight);
    window.scrollTo({ top: target, behavior: "instant" });
  }

  // Ein Feld des Adressfelds mit seiner Beschriftung (der ganze Baustein „Textfeld“) ganz ins Bild holen und nur so weit
  // rollen wie nötig (#410; Befund M1 der unabhängigen Prüfung: nur das Feld ließ am Handy die Beschriftung unter der
  // Kopfleiste): auf der Seite unter der Kopfleiste, wenn sie oben klebt, im Dialog in dessen Fläche. `wanted` ist, wo
  // es oben stehen soll.
  function placeField(field, wanted) {
    var dialog = field.closest("dialog");
    var box = field.getBoundingClientRect();
    var top = dialog ? dialog.getBoundingClientRect().top + GAP : (stickyTopbar ? topbar.getBoundingClientRect().bottom : 0) + GAP;
    var bottom = dialog ? dialog.getBoundingClientRect().bottom - GAP : window.innerHeight - GAP;
    var at = Math.min(Math.max(typeof wanted === "number" ? wanted : box.top, top), bottom - box.height);
    var by = box.top - at;
    if (Math.abs(by) < 1) {
      return;
    }
    if (dialog) {
      dialog.scrollTop += by;
    } else {
      window.scrollTo({ top: window.scrollY + by, behavior: "instant" });
    }
  }

  // Adressfeld: Seite bleibt stehen (#410, BA4). Nach „Übernehmen“ kommt die Seite neu vom Server, mit dem Fokus auf
  // der Straße. Stand die Straße dabei schon im Bild, rollte der Browser nicht zu ihr, und die Seite stand wieder oben.
  // Deshalb merkt sich die Seite beim Klick, wo die Straße im Bild stand, und die neue Seite stellt sie genau dorthin,
  // in der Seite oder im Dialog, aber nur, wenn sie von genau dieser Seite kommt. Stand sie außerhalb des Bilds oder
  // am Handy unter der Kopfleiste, rollt sie nur so weit, dass sie ganz zu sehen ist. Ohne Skript führt „#adressfeld“
  // in der Adresse zum Adressfeld; mit Skript fällt diese Stelle weg, damit der Fokus auf der Straße liegen kann.
  var STREET_KEY = "adresse-stelle";
  document.querySelectorAll(".a-adressfeld button[formaction*='#adressfeld']").forEach(function (button) {
    button.setAttribute("formaction", button.getAttribute("formaction").split("#")[0]);
  });
  document.addEventListener("submit", function (event) {
    var button = event.submitter;
    var box = button && button.closest ? button.closest(".a-adressfeld") : null;
    var field = box && box.querySelector("[name='street']");
    if (!field || (button.name !== "treffer" && button.name !== "leeren")) {
      return;
    }
    try {
      window.sessionStorage.setItem(STREET_KEY, JSON.stringify({
        top: field.closest(".a-textfeld").getBoundingClientRect().top,
        from: window.location.href.split("#")[0],
      }));
    } catch (error) {
      // Ist der Speicher gesperrt, steht die Straße nur sicher im Bild.
    }
  });
  if (streetInput && addressFocus === streetInput) {
    var streetSpot = null;
    try {
      streetSpot = JSON.parse(window.sessionStorage.getItem(STREET_KEY));
      window.sessionStorage.removeItem(STREET_KEY);
    } catch (error) {
      streetSpot = null;
    }
    var cameFrom = streetSpot && document.referrer.split("#")[0] === streetSpot.from;
    streetInput.focus({ preventScroll: true });
    placeField(street, cameFrom && typeof streetSpot.top === "number" ? streetSpot.top : null);
  }

  // Adressfeld: Enter sucht (#410, BA1 bis BA3, BA9). Enter in Bezeichnung, Straße, PLZ oder Ort (die Felder aus
  // „data-enter-sucht“) wirkt wie „Adresse suchen“, am Handy ebenso die Eingabetaste der Bildschirmtastatur. In den
  // übrigen Feldern bleibt Enter, was der Browser tut: der erste Knopf des Formulars, also „Weiter“ oder „Speichern“.
  // Während eine Eingabe noch zusammengesetzt wird (Wortvorschläge, Akzente), schließt Enter nur sie ab. Ohne Skript
  // bleibt Enter überall „Weiter“ bzw. „Speichern“, gesucht wird über den Knopf.
  document.querySelectorAll(".a-adressfeld[data-enter-sucht]").forEach(function (box) {
    var search = box.querySelector(".a-adresse-suchen");
    var names = box.getAttribute("data-enter-sucht").split(" ");
    if (!search || !search.form) {
      return;
    }
    document.addEventListener("keydown", function (event) {
      var input = event.target;
      if (event.key !== "Enter" || event.isComposing || event.keyCode === 229 || event.shiftKey || event.ctrlKey ||
          event.metaKey || event.altKey || !(input instanceof HTMLInputElement) || input.form !== search.form ||
          names.indexOf(input.name) < 0) {
        return;
      }
      event.preventDefault();
      search.click();
    });
  });

  // Adressfeld: „Adresse leeren“ (#410, BA5 bis BA7, BG3 bis BG5). Den Knopf gibt es, sobald in Straße, PLZ, Ort oder
  // Bundesland etwas steht oder ein anderes Land als Deutschland gewählt ist. Mit Skript leert er die Adresse im
  // Browser, ohne die Seite neu zu laden und ohne Rückfrage: Straße, PLZ, Ort und Bundesland leer, das Land
  // Deutschland, die Koordinaten eines übernommenen Treffers, Treffer und Meldung der Suche und die Fehler an der
  // Adresse weg; die Bezeichnung bleibt. Der Fokus liegt danach auf der Straße. Gespeichert wird erst mit „Weiter“
  // bzw. „Speichern“; an OpenStreetMap geht nichts. Ohne Skript schickt der Knopf das Formular (core/views.py).
  var GERMANY = "DE";
  document.querySelectorAll(".a-adressfeld").forEach(function (box) {
    var clear = box.querySelector(".a-adresse-leeren");
    if (!clear) {
      return;
    }
    function field(name) {
      return box.querySelector("[name='" + name + "']");
    }
    var texts = ["street", "postal_code", "city"].map(field);
    var state = field("state");
    var country = field("country");
    var coordinates = field("coordinates");

    function update() {
      clear.hidden = !(texts.some(function (input) { return input.value.trim(); }) || state.value ||
        (country.value && country.value !== GERMANY));
    }

    clear.addEventListener("click", function (event) {
      event.preventDefault();
      texts.forEach(function (input) {
        input.value = "";
        // Wie Tippen: Die Zahl der Zeichen passt sich an.
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      state.value = "";
      country.value = GERMANY;
      country.dispatchEvent(new Event("change", { bubbles: true }));
      if (coordinates) {
        coordinates.value = "";
      }
      var result = box.querySelector(".a-adresse-ergebnis");
      if (result) {
        result.remove();
      }
      box.querySelectorAll(".is-invalid").forEach(function (input) {
        input.classList.remove("is-invalid");
        input.removeAttribute("aria-invalid");
        describedBy(input, input.id + "-fehler", false);
      });
      box.querySelectorAll(".invalid-feedback").forEach(function (error) {
        error.remove();
      });
      update();
      texts[0].focus({ preventScroll: true });
      placeField(texts[0].closest(".a-textfeld"), null);
    });
    box.addEventListener("input", update);
    box.addEventListener("change", update);
    update();
  });

  // Vorschläge beim Tippen (#190, PK-09): Ab drei Zeichen fragt das Skript die Personen aus dem eigenen
  // Bereich ab und zeigt sie in der Trefferliste; darunter wird nicht gesucht und nichts gezählt. Eine
  // ältere Antwort, die erst nach einer neueren ankommt, wird verworfen. „Suchen“ und Enter schicken
  // weiter das Formular ab. Ohne Skript gibt es keine Vorschläge, nur „Suchen“.
  document.querySelectorAll("form[data-vorschlaege]").forEach(function (form) {
    var input = form.querySelector("input[name='suche']");
    var list = form.parentElement.querySelector("[data-treffer]");
    var address = form.getAttribute("data-vorschlaege");
    var asked = 0;
    var timer = null;
    if (!input || !list) {
      return;
    }
    list.setAttribute("aria-live", "polite");
    input.addEventListener("input", function () {
      window.clearTimeout(timer);
      var text = input.value.trim();
      var number = ++asked;
      if (text.length < 3) {
        list.innerHTML = "";
        return;
      }
      timer = window.setTimeout(function () {
        // Als Formular mit Formularschutz, damit der Name nicht in der Adresse und in keinem Protokoll steht.
        fetch(address, { method: "POST", body: new FormData(form), credentials: "same-origin" })
          .then(function (response) {
            // Abgelaufene Anmeldung oder abgelaufener Support-Zugang (#92): Statt der Seite in der Liste geht es
            // dorthin, wohin das Tool weiterleitet, etwa zum Login oder zur Seite mit der Meldung nach Ablauf.
            if (response.redirected) {
              window.location.assign(response.url);
              return "";
            }
            return response.ok ? response.text() : "";
          })
          .then(function (html) {
            if (number === asked) {
              list.innerHTML = html;
            }
          })
          .catch(function () {
            // Ohne Verbindung bleibt die Liste, wie sie ist; „Suchen“ geht weiter.
          });
      }, 200);
    });
  });

  // Formulare im Bausteinkatalog (#176) zeigen nur das Aussehen und schicken nichts ab.
  document.querySelectorAll("form[data-nur-ansicht]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
    });
  });
})();
