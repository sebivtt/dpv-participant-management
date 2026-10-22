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

  // Formulare der Musterseite zeigen nur das Aussehen und schicken nichts ab.
  document.querySelectorAll("form[data-nur-ansicht]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
    });
  });
})();
