---
name: grill-me
description: Ein GitHub-Issue vor der Umsetzung vollständig klären, indem Sebastian Frage für Frage ausgefragt wird, dann das Issue überarbeiten, bei Bedarf in Unter-Issues aufteilen und mit dem Label „geklärt“ freigeben. Verwenden, bevor ein Issue ohne Label „geklärt“ umgesetzt wird, und wenn Sebastian „grill me“, „frag mich aus“ oder „Issue klären“ sagt.
---

# Grill-Me: ein Issue vor der Umsetzung klären

Umgesetzt wird nur, was vollständig geklärt ist (aus dem Vorgänger-Repo übernommen, siehe `docs/entscheidungen.md`). Dieser Ablauf fragt Sebastian so lange aus, bis zu einem Issue keine Fragen mehr offen sind, und hält alle Antworten im Issue fest.

Sebastian ist kein Programmierer. Gesprochen wird deutsch, in Alltagssprache. Fachbegriffe beim ersten Auftreten erklären.

**Wer entscheidet was:** Fachliches entscheidet Sebastian (wer darf was, wie soll es aussehen, was passiert im Grenzfall). Technisches entscheidet die KI und begründet es. Hat eine technische Wahl spürbare Folgen für Nutzende, Aufwand oder Risiko, stellt die KI die Möglichkeiten in Alltagssprache vor und lässt Sebastian wählen.

## 1. Vorbereiten, ohne zu fragen

Erst alles lesen, was die KI selbst nachsehen kann. Sebastian wird nie etwas gefragt, was im Code oder in der Doku steht.

- Das Issue samt Kommentaren. Gibt es schon ein Protokoll einer früheren, unterbrochenen Runde, dort weitermachen.
  ```bash
  gh api repos/sebivtt/dpv-participant-management/issues/<nummer> --jq '.title, .body'
  gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/comments --paginate --jq '.[].body'
  ```
- Alle offenen Issues (Text, nicht nur Titel) und die eingetragenen Abhängigkeiten:
  ```bash
  gh api --paginate "repos/sebivtt/dpv-participant-management/issues?state=open&per_page=100" \
    --jq '.[] | select(.pull_request == null) | "#\(.number) \(.title)"'
  gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/dependencies/blocked_by --jq '.[] | "#\(.number) \(.state)"'
  gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/dependencies/blocking --jq '.[] | "#\(.number) \(.state)"'
  ```
- `docs/entscheidungen.md` (widerspricht das Issue einer Entscheidung?), `docs/anforderungen.md` (betroffene Anforderungen, Glossar am Ende), `docs/fahrplan.md` (in welche Phase gehört es?).
- **Fehlendes Diagramm zum Lebenszyklus:** In `docs/anforderungen.md` steht unter „Veranstaltung planen“, „Lebenszyklus“ nur ein Platzhalter für das Diagramm „Lebenszyklus einer Veranstaltung · 8 Zustände“. Sebastian hat es lokal. Berührt das Issue den Lebenszyklus (Zustände einer Veranstaltung wie „Anmeldung offen“ oder „Geschlossen“, Wechsel zwischen ihnen, Fristen, Veröffentlichen, Löschen), Sebastian in der Übersicht (Abschnitt 2) danach fragen und es mit seiner Zustimmung an der Stelle des Platzhalters ergänzen. Ist es ergänzt, diesen Punkt hier streichen.
- Den betroffenen Code: welche Seiten, Schritte im Anmeldeablauf, Dialoge, Schnittstellen und Rechte berührt sind, wie oft etwas vorkommt (z. B. wie viele Dialoge es gibt), was bestehende Daten betrifft. Die Erfahrungen in `CLAUDE.md` beachten (Adressen mit mehreren Aufrufern, Rechte).

## 2. Übersicht zeigen

Sebastian zuerst eine kurze Übersicht geben, bevor die erste Frage kommt:
- in zwei, drei Sätzen, was die KI aus Issue und Code verstanden hat,
- welche Themen geklärt werden müssen und wie viele Fragen es ungefähr sind,
- gefundene Widersprüche oder Unklarheiten im Issue selbst.

Diese Themen immer durchgehen und nur auslassen, was offensichtlich nicht zutrifft:
- **Ziel:** Welches Problem löst es, für wen? Woran merkt man, dass es erfüllt ist?
- **Rollen und Rechte:** Wer darf es sehen, wer ändern, und wer ausdrücklich nicht? Rollen nach ROL-01, dazu Veranstaltungsleitung und Ansprechperson. Welche Zeile der Rechtematrix ändert sich?
- **Ablauf:** Wo im Tool, in welchem Schritt, was passiert vorher und danach?
- **Grenzfälle:** leere Eingaben, null, sehr große Werte, Fristen abgelaufen, nachträgliche Änderungen, Personen entfernt, mehrere Bearbeitende gleichzeitig, bestehende Veranstaltungen und Anmeldungen.
- **Meldungen:** Was sieht man bei Fehlern oder im Erfolgsfall, mit welchem Wortlaut?
- **Aussehen und Bedienung,** wenn die Oberfläche betroffen ist, auch auf dem Handy.
- **Abhängigkeiten:** zu offenen Issues (blockiert durch, blockiert, berührt dieselbe Stelle, Dublette).
- **Umsetzungsmöglichkeiten** mit spürbaren Folgen, jeweils mit Empfehlung.
- **Risiken:** Was könnte dabei kaputtgehen? Vor allem der Anmeldeablauf.
- **Abgrenzung:** Was gehört ausdrücklich nicht dazu?
- **Prüfbarkeit:** Ist jedes Akzeptanzkriterium durch Ausprobieren prüfbar?

## 3. Einzeln fragen

- **Genau eine Frage pro Nachricht.** Steht ein Auswahl-Werkzeug zur Verfügung (z. B. `AskUserQuestion`), damit fragen, aber auch dort nur eine Frage je Aufruf.
- Jede Frage hat: ein, zwei Sätze Hintergrund, die Frage selbst, die Möglichkeiten mit ihren Folgen und eine **Empfehlung** mit Begründung. Dann reicht oft ein „ja, so“.
- Den Stand mitzählen: „Frage 4 von etwa 9“. Werfen Antworten neue Fragen auf, die Zahl anpassen und das kurz sagen.
- Ist eine Antwort unklar oder widerspricht einer früheren, nachfragen statt deuten.
- Sagt Sebastian „Pause“ oder „stop“, sofort anhalten. Den bisherigen Stand als Kommentar ins Issue schreiben (beantwortete Fragen mit Antwort, offene Fragen), damit eine spätere Sitzung dort weitermacht. Den Text des Issues selbst nicht ändern.
- Weiter, bis keine Frage aus der Übersicht und keine neu entstandene mehr offen ist.

## 4. Zusammenfassen und bestätigen lassen

Alle Entscheidungen kurz als Liste zeigen und fragen, ob das so stimmt. Erst nach Sebastians Bestätigung weiter.

## 5. Issue überarbeiten

- Den Text des Issues so neu schreiben, dass er ohne das Gespräch vollständig und eindeutig ist. Aufbau und Überschriften der passenden Vorlage (`.github/ISSUE_TEMPLATE/`) beibehalten, keine neuen Überschriften erfinden. Antworten landen dort, wo sie passen:
  - **Anforderung:** als Akzeptanzkriterium, als Beispiel, unter „Wer darf das nicht?“ oder unter „Nicht Teil dieser Anforderung“. Unter „Offene Fragen“ steht danach „Keine, geklärt am <Datum>“.
  - **Fehler:** unter „Erwartetes Verhalten“, bei Bedarf ergänzt unter „Schritte zum Nachstellen“. Abgrenzungen, Abhängigkeiten und der Vermerk „Geklärt am <Datum>“ kommen unter „Bildschirmfotos und Hinweise“.
- Abhängigkeiten über die eingebaute Funktion von GitHub eintragen (siehe Skill `issue-anlegen`, Abschnitt 4), zusätzlich im Text mit einem Satz Begründung.
- Was in der Klärung auf später verschoben wurde, als eigenes Issue mit `vorgemerkt` anlegen (Skill `issue-anlegen`), mit Verweis auf das Protokoll. Nur unter „Nicht Teil dieser Anforderung“ ginge es verloren, sobald das Issue geschlossen ist.
- Einen Kommentar mit dem Protokoll anhängen: jede Frage, die Antwort, bei Bedarf der Grund. So bleibt nachvollziehbar, warum etwas so entschieden wurde.
- Regeln, die über dieses Issue hinaus gelten (z. B. „Alle Dialoge schließen mit ESC“), zusätzlich in `docs/entscheidungen.md` eintragen. Das geschieht im Pull Request der Umsetzung.

```bash
gh api -X PATCH repos/sebivtt/dpv-participant-management/issues/<nummer> -F body=@<datei.md>
gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/comments -F body=@<protokoll.md>
```

## 6. Ein Issue oder mehrere?

Aufteilen, wenn mindestens eines zutrifft:
- Es betrifft mehrere Seiten oder Dialoge, die sich einzeln ändern und prüfen lassen.
- Es braucht erst ein Grundgerüst (z. B. ein gemeinsames Aussehen), das danach an mehreren Stellen genutzt wird.
- Ein Fehler würde einen wichtigen Ablauf treffen, vor allem die Anmeldung, und ein kleinerer Schritt senkt das Risiko.
- Der Pull Request würde so groß, dass seine Beschreibung nicht mehr auf eine Bildschirmseite passt.

Jeder Teil muss für sich umsetzbar sein, einen eigenen Test bekommen und etwas liefern, das Sebastian ausprobieren kann. Den Vorschlag (Teile, Reihenfolge, Begründung) Sebastian zeigen und sein Okay abwarten. Dann:
- jeden Teil als eigenes Issue nach Vorlage anlegen, mit den Kriterien, die zu ihm gehören,
- die Teile als Unter-Issues an das ursprüngliche Issue hängen, das damit zum Sammel-Issue wird,
- die Reihenfolge als „blockiert durch“ eintragen.

```bash
# interne id des Teils (nicht die Nummer)
gh api repos/sebivtt/dpv-participant-management/issues/<teil> --jq '.id'
# Teil an das Sammel-Issue hängen
gh api repos/sebivtt/dpv-participant-management/issues/<sammel>/sub_issues -F sub_issue_id=<id des Teils>
```

## 7. Freigeben

Nach Sebastians ausdrücklichem Okay das Label `geklärt` setzen, bei einer Aufteilung an jedes Unter-Issue (das Sammel-Issue selbst wird nicht umgesetzt):

```bash
gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/labels -f 'labels[]=geklärt'
```

## Danach: Umsetzung

Diese Regeln stehen auch in `CLAUDE.md`:
- Umgesetzt wird nur ein Issue mit dem Label `geklärt`, und erst, wenn es laut `docs/fahrplan.md` dran ist. Das Label heißt nur „fertig geklärt“, nicht „jetzt dran“.
- Direkt vor dem Start die Abhängigkeiten erneut prüfen. Ist ein blockierendes Issue noch offen, nicht anfangen, sondern Sebastian fragen.
- Ein Issue = ein Pull Request mit eigenem Test. Die Beschreibung des Pull Requests nennt „Closes #<nummer>“, dann schließt GitHub das Issue bei der Übernahme.
- Der Reihe nach: Der nächste Pull Request beginnt erst, wenn der vorige in `main` ist. Ein Issue ist dran, wenn seine Anforderungen zur laufenden Phase in `docs/fahrplan.md` gehören. Fehler, die einen wichtigen Ablauf blockieren, gehen vor. Im Zweifel fragt die KI Sebastian.
- Ein Sammel-Issue wird geschlossen, wenn sein letztes Unter-Issue erledigt ist.
- Kommt zu einem geklärten Issue neuer Inhalt dazu (neue Anforderung, ergänzte Dublette, neue fachliche Frage), das Label `geklärt` entfernen und `grill-me` nur für den neuen Teil durchlaufen.
- Taucht während der Umsetzung eine fachliche Frage auf, die das Issue nicht beantwortet, anhalten und Sebastian fragen, die Antwort ins Issue übernehmen. Nicht still selbst entscheiden.
