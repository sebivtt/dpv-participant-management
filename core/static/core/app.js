// Kleine Helfer der Grundgestaltung (#7). Ohne Skript bleibt am PC alles bedienbar; am Handy
// öffnet das Skript das Menü.
(function () {
  "use strict";

  // Handy-Menü: Der Browser hält den Fokus im geöffneten Dialog und schließt ihn mit Escape.
  // Dazu kommen: Schließen-Knopf, Antippen daneben und Rückkehr des Fokus auf „Menü“.
  var menu = document.getElementById("menue");
  var openButton = document.getElementById("menue-auf");
  var closeButton = document.getElementById("menue-zu");
  if (menu && openButton && closeButton && typeof menu.showModal === "function") {
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
      clear.disabled = open ? input.value === "" : saved === "";
    }

    // Der Fehler gehört zur verworfenen Eingabe und verschwindet mit ihr.
    function forgetError() {
      var error = box.querySelector(".invalid-feedback");
      if (error) {
        error.remove();
      }
      input.classList.remove("is-invalid");
      input.removeAttribute("aria-invalid");
      // Eine Fehlermeldung nach gescheitertem Speichern bleibt stehen (#186) und mit der Eingabe verknüpft.
      var failure = box.querySelector(".a-meldung.ist-fehler");
      if (failure) {
        input.setAttribute("aria-describedby", failure.id);
      } else {
        input.removeAttribute("aria-describedby");
      }
    }

    function open() {
      show(true);
      input.focus();
      input.select();
    }

    // Der Fokus geht zurück aufs Feld, außer jemand hat außerhalb etwas anderes angetippt,
    // das den Fokus selbst nimmt, etwa einen Link.
    function close(keepFocusElsewhere) {
      input.value = saved;
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
      input.value = "";
      clear.disabled = true;
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

  // Formulare im Bausteinkatalog (#176) zeigen nur das Aussehen und schicken nichts ab.
  document.querySelectorAll("form[data-nur-ansicht]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
    });
  });
})();
