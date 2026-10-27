---
name: phase-steuern
description: Eine Phase als Steuerungssession führen, vom Phasenstart über Aufträge und die Pflege des Phasen-Issues bis zur Übergabe an die nächste Steuerungssession und zum Abschluss. Verwenden, wenn eine Phase beginnt, wenn eine Steuerungssession startet oder übernimmt, und wenn Sebastian „Phase steuern“, „Phase starten“ oder „Phase abschließen“ sagt.
---

# Phase steuern

Die Regeln dazu stehen in `CLAUDE.md`, Abschnitte „Ein Ort je Angabe“, „Ablauf einer Phase“ und „Steuerungssession und Umsetzungs-Sessions“. Dieser Skill enthält nur die Handgriffe. Was die Steuerungssession darf und wann sie wechselt, steht dort und wird hier nicht wiederholt.

Das Phasen-Issue folgt der Vorlage `.github/ISSUE_TEMPLATE/phase.yml`. Für P2 ist es #106 (bis zum Umbau nach der Vorlage in #170 noch ohne den Abschnitt „Stand für die nächste Steuerungssession“). Nach der Vorlage angelegte Phasen-Issues findet dieser Befehl; `<phase>` ist das Label der Phase, etwa `P3`:

```bash
gh api --paginate "repos/sebivtt/dpv-participant-management/issues?state=open&labels=<phase>&per_page=100" \
  --jq '.[] | select(.pull_request == null) | select(.body // "" | contains("### Stand für die nächste Steuerungssession")) | "#\(.number) \(.title)"'
```

## 0. Einstieg einer neuen Steuerungssession

Gibt es schon ein Phasen-Issue, zuerst nur dieses lesen, besonders den Abschnitt „Stand für die nächste Steuerungssession“. Daraus ergibt sich, was gerade läuft und was als Nächstes kommt. Nicht nachfragen, was im alten Gespräch war; fehlt etwas Wichtiges im Stand, Sebastian fragen und die Antwort ins Phasen-Issue schreiben.

```bash
gh api repos/sebivtt/dpv-participant-management/issues/<phasen-issue> --jq '.title, .body'
```

## 1. Phasenstart

1. **Phasen-Issue anlegen** nach der Vorlage, mit den Labels `enhancement` und dem der Phase. Alle Überschriften der Vorlage als `### <Feldname>` in derselben Reihenfolge übernehmen (wie im Skill `issue-anlegen`, Abschnitt 2). Die Abschlusskriterien bekommen je ein Häkchen mit kurzem Stichwort und Verweis auf `docs/fahrplan.md`, nicht den Wortlaut.
2. **Bestandsaufnahme:** alle offenen Issues lesen (Text, nicht nur Titel) und die eingetragenen Abhängigkeiten.
   ```bash
   gh api --paginate "repos/sebivtt/dpv-participant-management/issues?state=open&per_page=100" \
     --jq '.[] | select(.pull_request == null) | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"'
   gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/dependencies/blocked_by --jq '.[] | "#\(.number) \(.state)"'
   ```
   Abgleichen mit den Anforderungen und Abschlusskriterien der Phase in `docs/fahrplan.md`. Phasen-Labels bei Bedarf korrigieren. Widersprüche (zwischen Issues, Labels, Abhängigkeiten oder Doku) Sebastian einzeln mit Vorschlag vorlegen. Fehlende Issues mit dem Skill `issue-anlegen` anlegen.
3. **Grundlagen zuerst:** Issues, von denen andere abhängen, kommen in der Reihenfolge nach vorn und werden zuerst mit `grill-me` geklärt.
4. **Reihenfolge eintragen:** ins Phasen-Issue nur als nummerierte Liste von Issue-Nummern. Was technisch zuerst da sein muss, zusätzlich auf GitHub als „blockiert durch“ (Befehl im Skill `issue-anlegen`, Abschnitt 4).
5. **Planung prüfen lassen:** Eine zweite KI-Instanz ohne Kenntnis des Gesprächs prüft lesend das Phasen-Issue, die Abhängigkeiten auf GitHub und `docs/fahrplan.md`. Auftrag: fehlende Issues, fehlende oder überflüssige Abhängigkeiten, Abschlusskriterien ohne passendes Issue, Widersprüche. Befunde selbst nachprüfen und Sebastian vorlegen. Erst danach startet die erste Umsetzung.

## 2. Aufträge

- **Vor dem Auftrag** prüfen, ob das Issue das Label `geklärt` trägt, keine offenen blockierenden Issues hat und alles, was die Umsetzung wissen muss, in seinem Text steht. Fehlt etwas, erst den Text des Issues ergänzen lassen (über `grill-me`), nicht den Auftrag.
- **Den Auftrag** nach `CLAUDE.md`, „Steuerungssession und Umsetzungs-Sessions“, Punkt „Auftrag“, in einer neuen Session erteilen.
- **Vorlauf beim Klären** im Blick behalten (`CLAUDE.md`, „Ablauf einer Phase“): Beim Start einer Umsetzung die nächste Gruppe zum Klären an Sebastian geben und Issues, die ein Zielbild brauchen, rechtzeitig zum Klären geben.

## 3. Phasen-Issue pflegen

Text des Phasen-Issues holen, ändern, zurückschreiben:

```bash
gh api repos/sebivtt/dpv-participant-management/issues/<phasen-issue> --jq '.body' > phase.md
# phase.md bearbeiten
gh api -X PATCH repos/sebivtt/dpv-participant-management/issues/<phasen-issue> -F body=@phase.md
```

- **Nach jeder übernommenen Umsetzung:** Häkchen beim Abschlusskriterium, das sie belegt, mit Beleg (Pull Request, Commit, Test oder Datei). Das Issue selbst ist erledigt, wenn es geschlossen ist; dafür kein eigener Vermerk.
- **Neues Issue in der Phase:** Nummer an ihren Platz in der Reihenfolge, Abhängigkeiten auf GitHub, Stunden mit Verweis auf Sebastians Zustimmung (Skill `issue-anlegen`, Abschnitt „Laufende Phase“).
- **Was nicht ins Phasen-Issue gehört,** ergibt sich aus `CLAUDE.md`, „Ein Ort je Angabe“: Es steht an seinem eigenen Ort und wird hier höchstens verlinkt.
- **Protokolle** (Bestandsaufnahme, Prüfung der Planung) kommen als Kommentar ins Phasen-Issue; der Text des Issues verlinkt sie.

## 4. Übergabe an die nächste Steuerungssession

Wann gewechselt wird, steht in `CLAUDE.md`, „Steuerungssession und Umsetzungs-Sessions“. Beim Wechsel den Abschnitt „Stand für die nächste Steuerungssession“ im Phasen-Issue neu schreiben, kurz und ohne Wiederholung dessen, was schon anderswo steht:

- Datum und Uhrzeit der Übergabe,
- welches Issue zuletzt umgesetzt und eingetragen wurde,
- was gerade läuft (Klärung, offene Frage an Sebastian, wartender Pull Request), mit Link,
- welches Issue als Nächstes beauftragt wird,
- Besonderheiten, die nirgends sonst stehen; gehören sie in ein Issue, dort eintragen und hier nur verlinken.

Dann Sebastian sagen, dass die Session endet und eine neue mit diesem Skill weitermacht.

## 5. Abschluss

1. Alle Abschlusskriterien im Phasen-Issue abgehakt, jedes mit Beleg; Sebastian die Liste zeigen.
2. Externes Review nach `docs/review-leitfaden.md` anstoßen (Vorlage `externes-review.yml`); das Review-Issue verlinkt das Phasen-Issue.
3. Sind alle blockierenden Befunde behoben, Rückblick mit Sebastian: was lief gut, was nicht. Die neuen Erfahrungen kommen als Issue (Skill `issue-anlegen`) und von dort per Auftrag an eine Umsetzungs-Session in `CLAUDE.md`, „Erfahrungen aus dem Vorgänger-Repo“.
4. Erst danach geht der „Stand“ im `README.md` ebenso per Issue und Auftrag an eine Umsetzungs-Session. Ist er in `main`, das Phasen-Issue schließen.
