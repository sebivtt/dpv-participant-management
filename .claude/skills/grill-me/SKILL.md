---
name: grill-me
description: Ein GitHub-Issue vor der Umsetzung vollständig klären, indem Sebastian Frage für Frage ausgefragt wird, dann das Issue überarbeiten, bei Bedarf in Unter-Issues aufteilen und mit dem Label „geklärt“ freigeben. Verwenden, bevor ein Issue ohne Label „geklärt“ umgesetzt wird, und wenn Sebastian „grill me“, „frag mich aus“ oder „Issue klären“ sagt.
---

# Grill-Me: ein Issue vor der Umsetzung klären

Umgesetzt wird nur, was vollständig geklärt ist (aus dem Vorgänger-Repo übernommen, siehe `docs/entscheidungen.md`). Dieser Ablauf fragt Sebastian so lange aus, bis zu einem Issue keine Fragen mehr offen sind, und hält alle Antworten im Issue fest.

Sebastian ist kein Programmierer. Gesprochen wird deutsch, in Alltagssprache. Fachbegriffe beim ersten Auftreten erklären.

**Wer entscheidet was:** nach `CLAUDE.md`, „Zusammenarbeit mit Sebastian“. Fachlich ist hier alles, was regelt, wer was darf, wie etwas aussieht und was im Grenzfall passiert.

**Kurzform oder volle Klärung:** Passt die Kurzform (Abschnitt „Kurzform“ unten), schlägt die KI sie in der Übersicht (Abschnitt 2) vor. Ohne Sebastians Bestätigung gilt die volle Klärung.

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
- **Fachliches Verhalten:** Ändert sich am Tool etwas für Nutzende? Wenn nicht (z. B. reine Doku, CI oder Arbeitsregeln), wird das festgehalten. Was daraus für die Szenarien folgt, regelt `CLAUDE.md`, „Ablauf je Aufgabe“, Schritt 3; Sebastian kann trotzdem Szenarien wollen, etwa für Abläufe bei reinen Arbeitsregeln.
- **Rollen und Rechte:** Wer darf es sehen, wer ändern, und wer ausdrücklich nicht? Rollen nach ROL-01, dazu Veranstaltungsleitung und Ansprechperson. Welche Zeile der Rechtematrix (`docs/rechtematrix.md`) ändert sich? Bringt das Issue neue Daten, werden beim Klären ihre Zeilen festgelegt: wer sie sehen, anlegen, bearbeiten und löschen bzw. verwalten darf, erlaubt und verboten (`CONTRIBUTING.md`, Abschnitt 4).
- **Ablauf:** Wo im Tool, in welchem Schritt, was passiert vorher und danach?
- **Grenzfälle:** leere Eingaben, null, sehr große Werte, Fristen abgelaufen, nachträgliche Änderungen, Personen entfernt, mehrere Bearbeitende gleichzeitig, bestehende Veranstaltungen und Anmeldungen.
- **Meldungen:** Was sieht man bei Fehlern oder im Erfolgsfall, mit welchem Wortlaut?
- **Aussehen und Bedienung,** wenn die Oberfläche betroffen ist, auch auf dem Handy.
- **Zielbild:** Braucht das Issue eines? Wann es nötig ist, regelt `CLAUDE.md`, „Zielbild vor Gestaltung“; bei einem neuen Abschnitt einer bestehenden Seite entscheidet Sebastian. Die Antwort kommt ins Protokoll und in den Text des Issues, auch wenn keins nötig ist.
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

## 5. Szenarien

Aus den Szenarien entstehen später die Tests; wann sie nötig sind und wann nicht, regelt `CLAUDE.md`, „Ablauf je Aufgabe“, Schritt 3. Sie werden hier gesammelt, solange Sebastian im Thema ist.

- Die KI schlägt Szenarien vor, in der Form wie in #89: Wer tut was, was passiert, mit der Kennung der Matrixzeile, gruppiert nach erlaubt, verboten und Grenzfällen. Erfundene Personen und Einheiten wie in den Szenarien zu #90.
- Sebastian entscheidet je Szenario (`CLAUDE.md`, „Ablauf je Aufgabe“, Schritt 3).
- Danach kommen sie als Kommentar „Szenarien (Datum)“ ins Issue, mit seinen Entscheidungen. Wird das Issue aufgeteilt, kommen sie beim Aufteilen (Abschnitt 8) in das Unter-Issue, zu dem sie gehören.

## 6. Grober Entwurf und Zielbild

Nur wenn das Issue ein Zielbild braucht (Abschnitt 2). Regel und Reihenfolge: `CLAUDE.md`, „Zielbild vor Gestaltung“. Vorbild ist der Ablauf bei #165.

- **Grober Entwurf:** eine einzelne HTML-Datei, die sich mit Doppelklick im Browser öffnet. Grundlage sind die Szenarien, die Musterseite (`core/templates/core/muster.html`), die anderen Seiten und `docs/gestaltung.md`. Er zeigt nur, was geklärt ist, mit erfundenen Personen wie in den Szenarien, und lädt nichts von fremden Servern (Gestaltung und Symbole stehen in der Datei, Schrift ist die Systemschrift). Als Kommentar „Grober Entwurf (Datum)“ ins Issue, die Datei in einem aufklappbaren Codeblock; Sebastian bekommt sie zusätzlich als Datei zum Öffnen.
- **Warten:** Sebastian baut daraus, etwa mit ChatGPT, das Zielbild. So lange ruht die Klärung; der Stand kommt als Kommentar ins Issue wie bei einer Pause (Abschnitt 3).
- **Zielbild eintragen:** Die Datei von Sebastian unverändert als Kommentar „Zielbild (Datum)“ ins Issue, in einem aufklappbaren Codeblock, mit Herkunft (Dateiname, Datum), Größe und Prüfsumme (`shasum -a 256 <datei>`). Vorher prüfen, dass sie nur erfundene Daten enthält und nichts von fremden Servern lädt; sonst Sebastian fragen.
- **Zu groß für einen Kommentar** (GitHub nimmt höchstens 65 536 Zeichen, „Mein Profil“ hat mit eingebettetem Bootstrap rund 275 000): Entwurf oder Zielbild unverändert auf nummerierte Kommentare verteilen („Teil 1 von 5“ usw.), jeder Teil ein Codeblock. Der erste Teil sagt, wie die Teile ohne Zaunzeilen zusammengesetzt werden; die Prüfsumme gilt für die zusammengesetzte Datei.
- **Nachklärung:** Das Zielbild mit Issue, Szenarien, `docs/rechtematrix.md`, `docs/entscheidungen.md` und `docs/gestaltung.md` vergleichen. Jede Abweichung als eigene Frage wie in Abschnitt 3: wie im Zielbild oder wie geklärt, mit Empfehlung. Das Ergebnis kommt als Kommentar „Nachklärung nach dem Zielbild (Datum)“ ins Issue. Ändern sich Szenarien, kommt eine neue Fassung „Szenarien (Datum, Fassung nach dem Zielbild)“, die die alte ausdrücklich ersetzt. Abweichungen, die bleiben, stehen danach im Text des Issues, damit die Umsetzung sie nennen kann.
- **Beim Aufteilen** (Abschnitt 8) kommen Entwurf, Zielbild und Nachklärung in das Unter-Issue, das die Seite oder den Baustein baut.

## 7. Issue überarbeiten

- Den Text des Issues so neu schreiben, dass er ohne das Gespräch vollständig und eindeutig ist. Aufbau und Überschriften der passenden Vorlage (`.github/ISSUE_TEMPLATE/`) beibehalten, keine neuen Überschriften erfinden. Antworten landen dort, wo sie passen:
  - **Anforderung:** als Akzeptanzkriterium, als Beispiel, unter „Wer darf das nicht?“ oder unter „Nicht Teil dieser Anforderung“. Unter „Offene Fragen“ steht danach „Keine, geklärt am <Datum>“.
  - **Fehler:** unter „Erwartetes Verhalten“, bei Bedarf ergänzt unter „Schritte zum Nachstellen“. Abgrenzungen, Abhängigkeiten und der Vermerk „Geklärt am <Datum>“ kommen unter „Bildschirmfotos und Hinweise“.
- Abhängigkeiten über die eingebaute Funktion von GitHub eintragen (siehe Skill `issue-anlegen`, Abschnitt 4), zusätzlich im Text mit einem Satz Begründung.
- Was in der Klärung auf später verschoben wurde, als eigenes Issue anlegen (Skill `issue-anlegen`; Regel in `CLAUDE.md`, „Ablauf einer Phase“, Punkt „Was beim Klären auf später verschoben wird“).
- Gehört das Issue zur laufenden Phase und ist es neu, seinen Platz im Phasen-Issue eintragen (Skill `issue-anlegen`, Abschnitt „Laufende Phase“).
- Einen Kommentar mit dem Protokoll anhängen: jede Frage, die Antwort, bei Bedarf der Grund. So bleibt nachvollziehbar, warum etwas so entschieden wurde.
- Regeln, die über dieses Issue hinaus gelten (z. B. „Alle Dialoge schließen mit ESC“), zusätzlich in `docs/entscheidungen.md` eintragen. Das geschieht im Pull Request der Umsetzung.

```bash
gh api -X PATCH repos/sebivtt/dpv-participant-management/issues/<nummer> -F body=@<datei.md>
gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/comments -F body=@<protokoll.md>
```

## 8. Ein Issue oder mehrere?

Aufteilen, wenn mindestens eines zutrifft:
- Es betrifft mehrere Seiten oder Dialoge, die sich einzeln ändern und prüfen lassen.
- Es braucht erst ein Grundgerüst (z. B. ein gemeinsames Aussehen), das danach an mehreren Stellen genutzt wird.
- Ein Fehler würde einen wichtigen Ablauf treffen, vor allem die Anmeldung, und ein kleinerer Schritt senkt das Risiko.
- Der Pull Request würde so groß, dass seine Beschreibung nicht mehr auf eine Bildschirmseite passt.

Jeder Teil muss für sich umsetzbar sein, einen eigenen Test bekommen und etwas liefern, das Sebastian ausprobieren kann. Den Vorschlag (Teile, Reihenfolge, Begründung) Sebastian zeigen und sein Okay abwarten. Dann:
- jeden Teil als eigenes Issue nach Vorlage anlegen, mit den Kriterien, die zu ihm gehören,
- die Teile als Unter-Issues an das ursprüngliche Issue hängen, das damit zum Sammel-Issue wird,
- eine technisch nötige Reihenfolge als „blockiert durch“ eintragen, jede andere nur im Phasen-Issue (`CLAUDE.md`, „Ein Ort je Angabe“).

```bash
# interne id des Teils (nicht die Nummer)
gh api repos/sebivtt/dpv-participant-management/issues/<teil> --jq '.id'
# Teil an das Sammel-Issue hängen
gh api repos/sebivtt/dpv-participant-management/issues/<sammel>/sub_issues -F sub_issue_id=<id des Teils>
```

## 9. Freigeben

Nach Sebastians ausdrücklichem Okay das Label `geklärt` setzen, bei einer Aufteilung an jedes Unter-Issue (das Sammel-Issue selbst wird nicht umgesetzt). Vorher muss im Issue der Kommentar „Szenarien (Datum)“ stehen, oder das Issue hält fest, dass es keine Szenarien braucht. Braucht es ein Zielbild, müssen auch Zielbild und Nachklärung im Issue stehen (Abschnitt 6).

```bash
gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/labels -f 'labels[]=geklärt'
```

## Kurzform

Für Issues mit höchstens einem neuen Punkt oder ohne fachliches Verhalten. Die KI schlägt sie in der Übersicht vor, Sebastian bestätigt; will er die volle Klärung, gilt die volle.

- **Lesen** (Abschnitt 1) nur das Issue samt Kommentaren, seine eingetragenen Abhängigkeiten und die betroffenen Dateien, nicht alle offenen Issues und nicht die ganze Doku.
- **Themen** (Abschnitt 2) nur, soweit sie zutreffen.
- **Unverändert bleiben:** Fragen einzeln (Abschnitt 3), Zusammenfassung (Abschnitt 4), Szenarien, wenn nötig (Abschnitt 5), Entwurf und Zielbild, wenn nötig (Abschnitt 6), Protokoll (Abschnitt 7) und Sebastians Okay vor dem Label (Abschnitt 9).

## Danach

Für die Umsetzung gelten die Regeln in `CLAUDE.md`, „Ablauf je Aufgabe“ und „Ablauf einer Phase“.
