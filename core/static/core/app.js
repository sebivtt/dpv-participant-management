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
      input.removeAttribute("aria-describedby");
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
    if (box.hasAttribute("data-offen")) {
      show(true);
      input.focus();
    } else {
      show(false);
      if (box.hasAttribute("data-fokus")) {
        rest.focus();
      }
    }
  });

  // Formulare im Bausteinkatalog (#176) zeigen nur das Aussehen und schicken nichts ab.
  document.querySelectorAll("form[data-nur-ansicht]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
    });
  });
})();
