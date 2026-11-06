---
name: vorschau
description: Eine sichtbare Änderung vor dem Pull Request als HTML-Datei aus den echten Vorlagen zeigen. Verwenden, sobald bei einem Issue mit sichtbarer Änderung die Seite steht und die Tests vorher rot waren.
---

# Vorschau: das Ergebnis zeigen, bevor der Pull Request entsteht

Wann sie nötig ist: `CLAUDE.md`, Punkt „Vorschau“. Hier steht nur der Handgriff.

## 1. Fälle wählen

Aus den Szenarien die Fälle, in denen die Seite anders aussieht: je Rolle oder Zustand einer, dazu PC und Handy (Breite 390). Ändert das Issue einen Baustein, den auch andere Seiten nutzen, gehört eine dieser Seiten dazu.

## 2. Datei erzeugen

Einen vorübergehenden Test `tests/test_zz_vorschau_<nummer>.py` schreiben; git ignoriert ihn. Er nutzt die Fixtures der bestehenden Tests, holt jede Seite mit dem Test-Client und gibt die Fälle an `schreibe_vorschau` aus `tests/vorschau.py`. Ausgabe nach `lokal/vorschau-<nummer>.html`; auch das ignoriert git, und der Helfer legt den Ordner bei Bedarf an. Gleich danach den vorübergehenden Test löschen, sonst liefe er im vollen Prüflauf mit; für eine weitere Runde neu anlegen. <!-- R38 --> So enthält die Datei nur erfundene Daten und braucht keinen laufenden Server.

Nicht gleichzeitig mit einem anderen Prüflauf derselben Arbeitskopie laufen lassen. Eine Seite, die erst nach einem Klick oder Speichern entsteht, wird über den Zustand in den Fixtures erzeugt, ein Dialog als eigener Fall.

## 3. Zeigen

Den Stand committen; die Tests liegen schon als eigener Commit davor. Dann den Kommentar „Vorschau (Datum)“ ins Issue: gezeigte Fälle, Kennung des Commits, Arbeitskopie und Dateipfad, was die Datei nicht zeigt, „wartet auf Sebastian“. So kann eine neue Sitzung weitermachen.

Sebastian die Datei schicken, mit der Liste der Fälle und dem, was sie nicht zeigt: Links und Speichern sind gesperrt, Neuladen und Springen der Seite sind nicht zu sehen. Dann auf seine Antwort warten.

Will er lokal ausprobieren, ihm die Kennung für den Abschnitt „Pull Request lokal ausprobieren“ im `README.md` nennen, dazu die Rollen und Einheiten, die er braucht. Vorher mit `git -C ~/Entwicklung/dpv-participant-management cat-file -e <kennung>` prüfen, ob sein Ordner den Stand kennt; sonst den Zweig hochladen, ohne Pull Request.

## 4. Antwort festhalten

In denselben Kommentar: Sebastians Anmerkungen wörtlich, was daraus wurde, die neue Kennung, sein Okay wörtlich. Eine weitere Runde kommt ebenfalls dorthin.

Weicht das Ergebnis im Wortlaut von einem Szenario ab, nennt der Text des Issues das mit der Kennung des Szenarios. Den Kommentar „Szenarien (Datum)“ nicht bearbeiten, sonst wird die Prüfung „PR-Angaben“ rot. Ändert eine Anmerkung einen Test, gilt `CONTRIBUTING.md`, Abschnitt 3: erst der Test, dann der Code.

Trifft eine Anmerkung einen gemeinsamen Baustein, nennt die neue Fassung die anderen Seiten, die sich mitändern.

Was eine Anmerkung auslöst, regeln `CLAUDE.md`, „Vorschau“ und „Neuer Inhalt zu einem geklärten Issue“. Handgriff: umsetzen, die neue Fassung zeigen, die Änderung im Text des Issues festhalten. Auch dabei gelten „Bausteine einbinden“ und „Zielbild vor Gestaltung“. Der Pull Request verlinkt den Kommentar „Vorschau (Datum)“.
