---
name: phase-steuern
description: Eine Phase als Steuerungssession führen, vom Phasenstart über Aufträge und die Pflege des Phasen-Issues bis zur Übergabe an die nächste Steuerungssession und zum Abschluss. Verwenden, wenn eine Phase beginnt, wenn eine Steuerungssession startet oder übernimmt, und wenn Sebastian „Phase steuern“, „Phase starten“ oder „Phase abschließen“ sagt.
---

# Phase steuern

Hier stehen die Regeln und Handgriffe, die nur die Steuerungssession betreffen. Was für jede Session gilt, steht in `CLAUDE.md` und wird hier nicht wiederholt.

In der Cloud-Umgebung von Claude Code ist die GitHub-Suche (`search/issues`) gesperrt; dort nur Adressen unter `repos/...` verwenden, wie in den Befehlen dieses Skills.

Das Phasen-Issue folgt der Vorlage `.github/ISSUE_TEMPLATE/phase.yml`. Für P2 ist es #106. Nach der Vorlage angelegte Phasen-Issues findet dieser Befehl; `<phase>` ist das Label der Phase, etwa `P3`:

```bash
gh api --paginate "repos/sebivtt/dpv-participant-management/issues?state=open&labels=<phase>&per_page=100" \
  --jq '.[] | select(.pull_request == null) | select(.body // "" | contains("### Stand für die nächste Steuerungssession")) | "#\(.number) \(.title)"'
```

## 0. Einstieg einer neuen Steuerungssession

**Was die Steuerungssession darf:** lesen, Aufträge verteilen und das Phasen-Issue pflegen, dazu, was ihr dieser Skill beim Start und bei neuen Issues zuweist (Issues mit `issue-anlegen` anlegen, Labels und Abhängigkeiten eintragen). Sie entscheidet nichts Fachliches. <!-- R09 -->

Gibt es schon ein Phasen-Issue, zuerst nur dieses lesen, besonders den Abschnitt „Stand für die nächste Steuerungssession“. Daraus ergibt sich, was gerade läuft und was als Nächstes kommt. Nicht nachfragen, was im alten Gespräch war; fehlt etwas Wichtiges im Stand, Sebastian fragen und die Antwort ins Phasen-Issue schreiben. Dazu den Lauf auf `main` abfragen (Befehl in Abschnitt 2).

```bash
gh api repos/sebivtt/dpv-participant-management/issues/<phasen-issue> --jq '.title, .body'
```

## 1. Phasenstart

Beim Start legt die Steuerungssession das Phasen-Issue nach Vorlage an und macht die Bestandsaufnahme: alle offenen Issues der Phase, dazu alle mit `vorgemerkt` oder ohne Phasen-Label (Issues ohne Phasen-Label sind bewusst offen, nicht vergessen); die Phasen-Labels werden dabei bei Bedarf korrigiert. <!-- R03 -->

1. **Phasen-Issue anlegen** nach der Vorlage, mit den Labels `enhancement` und dem der Phase. Alle Überschriften der Vorlage als `### <Feldname>` in derselben Reihenfolge übernehmen (wie im Skill `issue-anlegen`, Abschnitt 2). Die Abschlusskriterien bekommen je ein Häkchen mit kurzem Stichwort und Verweis auf `docs/fahrplan.md`, nicht den Wortlaut.
2. **Bestandsaufnahme:** alle offenen Issues lesen (Text, nicht nur Titel) und die eingetragenen Abhängigkeiten.
   ```bash
   gh api --paginate "repos/sebivtt/dpv-participant-management/issues?state=open&per_page=100" \
     --jq '.[] | select(.pull_request == null) | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"'
   gh api repos/sebivtt/dpv-participant-management/issues/<nummer>/dependencies/blocked_by --jq '.[] | "#\(.number) \(.state)"'
   ```
   Abgleichen mit den Anforderungen und Abschlusskriterien der Phase in `docs/fahrplan.md`. Phasen-Labels bei Bedarf korrigieren. Widersprüche (zwischen Issues, Labels, Abhängigkeiten oder Doku) Sebastian einzeln mit Vorschlag vorlegen. Fehlende Issues mit dem Skill `issue-anlegen` anlegen. Ab P3 legt sie dabei ein Issue „Aufräumen“ an; es benennt die Zusammenführungen und Bereinigungen dieser Phase, die das Verhalten nicht ändern, und läuft wie jedes andere Issue. <!-- R07 --> Vorschläge dafür kommen aus dem letzten Rückblick und den offenen Befunden.
3. **Grundlagen zuerst:** Issues, von denen andere abhängen, kommen in der Reihenfolge nach vorn und werden zuerst mit `grill-me` geklärt.
4. **Reihenfolge eintragen:** ins Phasen-Issue nur als nummerierte Liste von Issue-Nummern. Was technisch zuerst da sein muss, zusätzlich auf GitHub als „blockiert durch“ (Befehl im Skill `issue-anlegen`, Abschnitt 4).
5. **Planung prüfen lassen:** Eine zweite KI-Instanz ohne Kenntnis des Gesprächs prüft lesend das Phasen-Issue, die Abhängigkeiten auf GitHub und `docs/fahrplan.md`. Auftrag: fehlende Issues, fehlende oder überflüssige Abhängigkeiten, Abschlusskriterien ohne passendes Issue, Widersprüche. Befunde selbst nachprüfen und Sebastian vorlegen. Erst danach startet die erste Umsetzung.

## 2. Aufträge

- **Vor dem Auftrag** prüfen, ob das Issue das Label `geklärt` trägt, keine offenen blockierenden Issues hat, alles, was die Umsetzung wissen muss, in seinem Text steht und der Lauf auf `main` nicht dagegen spricht (`gh run list --workflow "Prüfungen" --branch main --limit 2`; Regel in `CLAUDE.md`, „Roter Lauf auf `main` geht vor“; außer für die Behebung selbst). Geht die Abfrage nicht, das offen sagen und Sebastian fragen. Fehlt etwas, erst den Text des Issues ergänzen lassen (über `grill-me`), nicht den Auftrag.
- **Auftrag:** Ein Auftrag besteht nur aus dem Link zum Issue und dem Verweis auf `CLAUDE.md`, etwa „Setze #123 um, nach `CLAUDE.md`.“ Was sonst wichtig ist, steht vorher im Issue. <!-- R11 --> Er geht an eine neue Session.
- **Stand selbst feststellen:** Ob ein Lauf grün oder ein Pull Request übernommen ist, stellt die Steuerungssession selbst fest, nicht über Sebastians Meldung: für Läufe wie in `CLAUDE.md`, Ablauf je Aufgabe Nr. 6; für die Übernahme bei jedem Wiedereinstieg mit `gh pr view <nummer> --json state,mergedAt`, und wartet sie darauf, mit einem Hintergrundauftrag, der diese Abfrage wiederholt und sie bei der Übernahme weckt.
- **Nachträge** zu einem geklärten Issue nach `CLAUDE.md` („Neuer Inhalt zu einem geklärten Issue“) an eine Klärung mit `grill-me` geben (Kurzform möglich).
- **In der Claude-Code-Desktop-App:** Wird der Zug der Steuerungssession durch die Meldung einer anderen Session ausgelöst, kann sie selbst keine neue Session starten. Sie legt sie stattdessen als Vorschlag an (eine Karte in der App), den Sebastian mit einem Klick startet; der Inhalt ist der Auftrag nach Punkt „Auftrag“.
- **Klären läuft voraus:** Richtwert sind die nächsten drei Issues der Reihe, geklärt in Gruppen, die fachlich zusammenhängen (also auch zwei, vier oder eines). Die nächste Gruppe ist spätestens in Klärung, wenn die Umsetzung der laufenden beginnt. Issues, die ein Zielbild brauchen (`CLAUDE.md`, „Zielbild vor Gestaltung“), kommen früher in Klärung, etwa zwei Gruppen vorher, weil das Warten auf das Zielbild dauert. <!-- R04 --> Dafür beim Start einer Umsetzung die nächste Gruppe zum Klären an Sebastian geben.

## 3. Phasen-Issue pflegen

Text des Phasen-Issues holen, ändern, zurückschreiben:

```bash
gh api repos/sebivtt/dpv-participant-management/issues/<phasen-issue> --jq '.body' > phase.md
# phase.md bearbeiten
gh api -X PATCH repos/sebivtt/dpv-participant-management/issues/<phasen-issue> -F body=@phase.md
```

- **Nach jeder übernommenen Umsetzung:** Häkchen beim Abschlusskriterium, das sie belegt, mit Beleg (Pull Request, Commit, Test oder Datei). Das Issue selbst ist erledigt, wenn es geschlossen ist; dafür kein eigener Vermerk. Dazu den Lauf auf `main` abfragen (`gh run list --branch main --limit 1`); auf sein Ende muss sie vor dem nächsten Auftrag nicht warten.
- **Roter Lauf auf `main`** (Regel in `CLAUDE.md`, „Roter Lauf auf `main` geht vor“): Die Steuerungssession stellt die Ursache fest. Erfüllt der Lauf die Bedingungen für den Neustart aus `CLAUDE.md`, Ablauf je Aufgabe Nr. 6, startet sie ihn neu; sieht es sonst nur nach einer Störung oder einem wackelnden Test aus, entscheidet Sebastian, ob sie neu startet. Sonst legt sie ein Fehler-Issue an; es läuft wie jedes Issue, auch vor einem offenen Pull Request.
- **Neues Issue in der Phase:** Nummer an ihren Platz in der Reihenfolge, Abhängigkeiten auf GitHub (Skill `issue-anlegen`, Abschnitt „Laufende Phase“).
- **Was nicht ins Phasen-Issue gehört,** ergibt sich aus `CLAUDE.md`, „Ein Ort je Angabe“: Es steht an seinem eigenen Ort und wird hier höchstens verlinkt.
- **Protokolle** (Bestandsaufnahme, Prüfung der Planung) kommen als Kommentar ins Phasen-Issue; der Text des Issues verlinkt sie.

## 4. Übergabe an die nächste Steuerungssession

Die Steuerungssession wechselt nach jedem Issue, dessen Pull Request übernommen und im Phasen-Issue eingetragen ist, also zwischen zwei Umsetzungen, nie mitten in einer Umsetzung; Issues ohne Pull Request (Klärungen, Sammel-Issues) lösen keinen Wechsel aus. Vorher schreibt sie den Stand ins Phasen-Issue, mit allem, was noch läuft (Klärungen, wartende Pull Requests, Hintergrundaufträge); die nächste macht allein damit weiter. Fasst Claude Code das Gespräch vorher automatisch zusammen, beginnt sie nichts Neues mehr, schreibt sofort den Stand ins Phasen-Issue und endet; ein Hook erinnert sie daran. <!-- R12 --> Beim Wechsel den Abschnitt „Stand für die nächste Steuerungssession“ im Phasen-Issue neu schreiben.

Der Stand hat höchstens 15 Zeilen, keine Zeile länger als ein Satz, und nur diese fünf Angaben:

- Datum und Uhrzeit der Übergabe,
- welches Issue zuletzt umgesetzt und eingetragen wurde,
- was gerade läuft (Klärung, offene Frage an Sebastian, wartender Pull Request, Lauf auf `main`, Hintergrundauftrag), mit Link,
- welches Issue als Nächstes beauftragt wird,
- Besonderheiten, die nirgends sonst stehen; gehören sie in ein Issue, dort eintragen und hier nur verlinken.

Nichts Abgeschlossenes als „Davor: …“; der Verlauf steht in der Bearbeitungshistorie des Issues.

Dann Sebastian sagen, dass die Session endet, mit genau diesem Startsatz für die nächste und sonst nichts: „Steuere Phase <Pn> weiter, Phasen-Issue #<nr>, nach `CLAUDE.md` und Skill `phase-steuern`.“

## 5. Abschluss

Abgeschlossen ist eine Phase, wenn alle Häkchen im Phasen-Issue einen Beleg haben, das externe Review nach `docs/review-leitfaden.md` gelaufen ist (ab P1) und danach der Rückblick. Wer das Review zusammenführt, arbeitet nur lesend, schreibt nur ins Review-Issue und legt Befund-Issues erst nach Sebastians Entscheidung an. Ist das Review-Issue eingeordnet und sind alle blockierenden Befunde behoben, prüft der Rückblick zuerst, welche Regeln sich streichen, zusammenfassen oder durch eine Prüfschranke ersetzen lassen, und wertet die Befunde der unabhängigen Prüfung nach Fehlerarten aus; erst dann kommt Neues dazu, und vor jeder neuen Regel die Frage, ob eine Prüfschranke genügt. <!-- R06 --> Neue Erfahrungen kommen in `CLAUDE.md`, „Erfahrungen“; erst dann wechselt der „Stand“ im `README.md`.

1. Alle Abschlusskriterien im Phasen-Issue abgehakt, jedes mit Beleg; Sebastian die Liste zeigen.
2. Externes Review nach `docs/review-leitfaden.md` anstoßen (Vorlage `externes-review.yml`); das Review-Issue verlinkt das Phasen-Issue.
3. Sind alle blockierenden Befunde behoben, Rückblick mit Sebastian: was lief gut, was nicht. Dazu aus den Zeilen „Unabhängige Prüfung“ der Pull Requests der Phase bis zu drei häufige Fehlerarten mit je einer Folgerung, mit der Zahl der ausgewerteten Pull Requests und fehlenden Angaben; die gestrichenen oder zusammengefassten Regeln oder der Grund, warum es keine gibt (Regel oben). Neustarts mit dem Issue „Wackelnde Prüfungen“ abgleichen (`gh run list --workflow "Prüfungen" --created ">=<Phasenstart>" --limit 1000 --json attempt,headSha,url`, Versuch über 1; kommen genau 1000 zurück, das offen sagen). Streichungen und neue Erfahrungen kommen als Issue (Skill `issue-anlegen`) und von dort per Auftrag an eine Umsetzungs-Session in `CLAUDE.md`, „Erfahrungen“.
4. Erst danach geht der „Stand“ im `README.md` ebenso per Issue und Auftrag an eine Umsetzungs-Session. Ist er in `main`, das Phasen-Issue schließen.
