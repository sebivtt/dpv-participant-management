---
name: issue-anlegen
description: Neuen Fehler oder neue Anforderung als GitHub-Issue anlegen, nach Vorlage und mit Prüfung auf Abhängigkeiten zu offenen Issues. Verwenden, sobald Sebastian einen Fehler meldet oder etwas Neues wünscht, oder die KI selbst einen Fehler findet.
---

# Issue anlegen

Neue Fehler und Anforderungen stehen nur als Issue auf GitHub (aus dem Vorgänger-Repo übernommen, siehe `docs/entscheidungen.md`). Dieser Ablauf sorgt dafür, dass jedes Issue gleich aufgebaut ist und seine Abhängigkeiten von Anfang an sichtbar sind.

Gesprochen wird mit Sebastian nach `CLAUDE.md`, „Zusammenarbeit mit Sebastian“.

## 1. Einordnen

- **Fehler** (Label `bug`): Das Tool tut etwas Falsches oder Unerwartetes. Vorlage `.github/ISSUE_TEMPLATE/fehler.yml`.
- **Anforderung** (Label `enhancement`): Das Tool soll etwas können, was bisher nicht vorgesehen ist. Vorlage `.github/ISSUE_TEMPLATE/anforderung.yml`.
- **Befund aus einem externen Review** (Label `review-befund`): nur nach `docs/review-leitfaden.md`, Abschnitt 7, und erst nach Sebastians Einordnung. Vorlage `.github/ISSUE_TEMPLATE/review-befund.yml`; das Review-Issue einer Phase hat die Vorlage `externes-review.yml`.
- Ein Thema pro Issue. Stecken mehrere Themen in einer Meldung, mehrere Issues vorschlagen.
- Dazu das Label der Phase und bei Bedarf `vorgemerkt`, nach `CLAUDE.md`, „Ablauf einer Phase“, Punkt „Labels“.

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
- Es ist dasselbe Thema wie ein offenes Issue (Dublette). Dann kein neues Issue, sondern Sebastian vorschlagen, das bestehende zu ergänzen. Für ein bestehendes Issue mit dem Label `geklärt` gilt dabei `CLAUDE.md`, „Ablauf einer Phase“, Punkt „Neuer Inhalt zu einem geklärten Issue“.

Gefundene Abhängigkeiten Sebastian in einem Satz je Abhängigkeit nennen, mit Begründung, und erst nach seinem Okay eintragen. Was davon auf GitHub kommt und was nur ins Phasen-Issue, regelt `CLAUDE.md`, „Ein Ort je Angabe“.

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

## 5. Laufende Phase

Gehört das neue Issue zur laufenden Phase (Phase im `README.md` unter „Stand“), trägt es die KI im selben Schritt ins Phasen-Issue ein (Regel in `CLAUDE.md`, „Ablauf einer Phase“, Punkt „Neues während der Phase“):

- **Platz:** seine Nummer an der passenden Stelle der Reihenfolge; die Stelle mit dem Issue in Abschnitt 4 Sebastian zeigen.
- **Abhängigkeiten:** die aus Abschnitt 3, auf GitHub eingetragen.
- **Stunden:** Schätzung aus dem Puffer, Sebastian vorgelegt. Steht seine Zustimmung in seinen eigenen Worten im Issue oder Pull Request, kommt der Verweis darauf ins Phasen-Issue; die Zahlen selbst stehen in `docs/fahrplan.md` und ändern sich nur mit seiner Zustimmung.

Wie das Phasen-Issue bearbeitet wird, steht im Skill `phase-steuern`, Abschnitt „Phasen-Issue pflegen“.

## 6. Abschluss

Sebastian den Link zum Issue nennen und in einem Satz, welche Abhängigkeiten eingetragen sind und welchen Platz es im Phasen-Issue hat. Umgesetzt wird es erst, wenn es geklärt ist (Skill `grill-me`).
