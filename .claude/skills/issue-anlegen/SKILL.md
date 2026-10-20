---
name: issue-anlegen
description: Neuen Fehler oder neue Anforderung als GitHub-Issue anlegen, nach Vorlage und mit Prüfung auf Abhängigkeiten zu offenen Issues. Verwenden, sobald Sebastian einen Fehler meldet oder etwas Neues wünscht, oder die KI selbst einen Fehler findet.
---

# Issue anlegen

Neue Fehler und Anforderungen stehen nur als Issue auf GitHub (aus dem Vorgänger-Repo übernommen, siehe `docs/entscheidungen.md`). Dieser Ablauf sorgt dafür, dass jedes Issue gleich aufgebaut ist und seine Abhängigkeiten von Anfang an sichtbar sind.

Gesprochen wird mit Sebastian deutsch, in Alltagssprache, ohne Fachjargon. Er ist kein Programmierer.

## 1. Einordnen

- **Fehler** (Label `bug`): Das Tool tut etwas Falsches oder Unerwartetes. Vorlage `.github/ISSUE_TEMPLATE/fehler.yml`.
- **Anforderung** (Label `enhancement`): Das Tool soll etwas können, was bisher nicht vorgesehen ist. Vorlage `.github/ISSUE_TEMPLATE/anforderung.yml`.
- Ein Thema pro Issue. Stecken mehrere Themen in einer Meldung, mehrere Issues vorschlagen.
- Dazu das Label der Phase (`P1` bis `P10`), in die das Issue laut `docs/fahrplan.md` voraussichtlich gehört; ist sie unklar, keins. Ist es erst später dran, zusätzlich `vorgemerkt` (`CLAUDE.md`, „Für Phasen und Vorgemerktes gilt“).

## 2. Inhalt aufbauen

- Alle Überschriften der Vorlage als `### <Feldname>` in derselben Reihenfolge übernehmen, auch die der Auswahlfelder. Freiwillige Felder ohne Inhalt mit `_No response_` füllen, so wie GitHub es selbst tut.
- Auswahlfelder (Rolle, Auswirkung, Priorität) nicht raten, sondern Sebastian fragen.
- Begriffe nach dem Glossar am Ende von `docs/anforderungen.md` (z. B. „Ansprechperson“, „Teilnahmekreis“, „verwaltete Person“). Steht die Anforderung schon dort, ihre ID eintragen.
- Akzeptanzkriterien so formulieren, dass man sie durch Ausprobieren prüfen kann.
- Hier noch nicht ausfragen. Das gründliche Klären übernimmt später der Skill `grill-me`. Ein neues Issue darf offene Fragen enthalten.

## 3. Abhängigkeiten prüfen

Alle offenen Issues lesen, nicht nur die Titel:

```bash
gh api --paginate "repos/sebivtt/dpv-participant-management/issues?state=open&per_page=100" \
  --jq '.[] | select(.pull_request == null) | "#\(.number) \(.title)"'
gh api repos/sebivtt/dpv-participant-management/issues/<nummer> --jq '.body'
```

Eine Abhängigkeit liegt vor, wenn eines dieser Dinge zutrifft:
- Das neue Issue lässt sich erst sinnvoll umsetzen, wenn ein anderes erledigt ist (**blockiert durch**).
- Ein anderes Issue wartet auf das neue (**blockiert**).
- Beide ändern dieselbe Seite, denselben Dialog, denselben Schritt im Anmeldeablauf oder dieselbe Regel, sodass sie sich widersprechen oder gegenseitig überschreiben können. Dann im Text unter „Nicht Teil dieser Anforderung“ bzw. „Bildschirmfotos und Hinweise“ darauf verweisen und Sebastian fragen, ob eine Reihenfolge nötig ist.
- Es ist dasselbe Thema wie ein offenes Issue (Dublette). Dann kein neues Issue, sondern Sebastian vorschlagen, das bestehende zu ergänzen. Trägt es schon das Label `geklärt`, wird es dabei entfernt (siehe Skill `grill-me`, Abschnitt „Danach“).

Gefundene Abhängigkeiten Sebastian in einem Satz je Abhängigkeit nennen, mit Begründung, und erst nach seinem Okay eintragen.

## 4. Anlegen

Erst den fertigen Text Sebastian zeigen und sein Okay abwarten. Dann:

```bash
gh api repos/sebivtt/dpv-participant-management/issues \
  -f title='…' -F body=@<datei.md> -f 'labels[]=bug' -f 'labels[]=P2'   # bzw. enhancement, Phase und ggf. vorgemerkt
```

Abhängigkeiten über die eingebaute Funktion von GitHub eintragen. Sie braucht die interne `id` des anderen Issues, nicht seine Nummer:

```bash
# interne id eines Issues
gh api repos/sebivtt/dpv-participant-management/issues/<nummer> --jq '.id'
# <neu> wird blockiert durch <andere>
gh api repos/sebivtt/dpv-participant-management/issues/<neu>/dependencies/blocked_by \
  -F issue_id=<id der anderen>
```

## 5. Abschluss

Sebastian den Link zum Issue nennen und in einem Satz, welche Abhängigkeiten eingetragen sind. Umgesetzt wird das Issue erst, nachdem es mit `grill-me` geklärt ist und das Label `geklärt` trägt.
