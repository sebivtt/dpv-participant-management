<!-- In Alltagssprache schreiben. Sebastian liest den Code nicht; diese Beschreibung ist seine Prüfgrundlage (CONTRIBUTING.md, Abschnitt 8).
Für Sebastian: Ist „PR-Angaben“ rot oder läuft noch, nicht übernehmen. Unter „Details“ steht, was fehlt; das an die KI geben und den neuen grünen Lauf abwarten. -->

## Was sich für Nutzende ändert

Für Nutzende des Tools nichts. Für dich ändert sich: An jedem Pull Request steht jetzt eine zweite Prüfung **„PR-Angaben“**. Sie wird in Sekunden rot, wenn eine Pflichtangabe fehlt oder nicht passt:

- kein oder mehr als ein „Closes #…“, oder das Issue trägt nicht `geklärt`;
- kein Link auf einen Kommentar „Szenarien (…)“ in genau diesem Issue, und auch kein Verzicht, den das Issue mit der Zeile „Szenarien: keine.“ festhält;
- bei einer Änderung am Code keine Zeile „Test-Commit“, oder der genannte Commit enthält nicht nur Tests, oder schon vor ihm ändert ein Commit Code (außer einem genannten leeren Gerüst).

Sie läuft bei jeder Bearbeitung der Beschreibung neu, ohne dass der lange Prüflauf (rund 30 Minuten) noch einmal startet. Unter „Details“ steht in Alltagssprache, was fehlt.

- **Wichtigste Grenze:** Die Prüfung zeigt, dass die Angaben da sind und die Commits die Reihenfolge Test → Code sichtbar zeigen. Sie zeigt nicht, dass du die Szenarien wirklich bestätigt hast (KI und du schreiben unter demselben Konto), und nicht, dass ein Test aus dem richtigen Grund rot war. Eine rote Prüfung sperrt das Übernehmen weiterhin nicht (#16).

## Zielbild

Nicht nötig: keine Seite und kein Baustein (Prüfung auf GitHub und Arbeitsregeln).

## Anforderungen und Entscheidungen

Closes #237

- Neuer Eintrag in `docs/entscheidungen.md` (03.11.2026, #237): Pflichtangaben im Pull Request werden geprüft, Test-Commit vor dem Code, Label `geklärt`, Begriff *Code*, Grenzen.
- Geänderte Regeln: `CLAUDE.md` (zwei Punkte unter „Für die Umsetzung gilt außerdem“), `CONTRIBUTING.md` Abschnitt 3 (Test-Commit, Begriff *Code*), Vorlage für Pull Requests (Zeile „Test-Commit“, Hinweis für dich), `grill-me` (Verzicht als Zeile „Szenarien: keine.“). Herkunft: Projektprüfung, Paket P-02; Regel-Review durch Codex vorab (7 Einwände, alle eingearbeitet).
- **Abweichung vom Paket:** In `CLAUDE.md` steht der Satz zu „Szenarien: keine.“ als eigener Satz am Ende des Punkts „Direkt vor dem Start …“, nicht mitten im ersten Satz. Mitten im Satz hätte der Punkt in „keine.“ den Satz für den bestehenden Test `test_ohne_szenarien_haelt_die_ki_an_auch_wenn_der_auftrag_den_schritt_nicht_nennt` zerteilt; der Test bleibt unverändert, der Inhalt ist gleich.

## Wie geprüft wurde

- Szenarien: keine, weil das Issue kein fachliches Verhalten des Tools hat (Zeile „Szenarien: keine.“ im Issue-Text, `CLAUDE.md` Schritt 3). Ersatz: 64 Fälle in `tests/test_pr_angaben.py` (neu, ohne Netz, mit erfundenen Pull Requests) und 7 neue Regeltests in `tests/test_arbeitsregeln.py` (nur hinzugefügt).
- Gerüst-Commit: `16e0397`
- Test-Commit: `ec80e4f`, `aa8fb5a`
- Test für den erlaubten Fall: grün bleiben u. a. vollständiger PR nach neuer Vorlage; Szenarien in zwei Links einer Zeile (wie #213) und Nachtrag in eigener Zeile mit zweitem Test-Commit (wie #223); Gerüst → Test → Code; Test → Code → Test → Code (Nachbesserung); Doku-PR mit Verzicht und „entfällt“; PR nur mit Tests; CI-PR ohne Szenarien mit Test-Commit; Zeiten in verschiedenen Zeitzonen.
- Test für den verbotenen Fall: rot u. a. ohne/zwei „Closes“, „Fixes“ statt „Closes“, Issue ohne `geklärt`, kein Szenarien-Link, Link in ein anderes Issue, Kommentar ohne „Szenarien (“, Verzicht ohne Vermerk oder mit leerem Grund, Szenarien nach dem Test-Commit bearbeitet, Test-Commit nicht im PR, Test-Commit mit Code, **Code → Test → kleine Codekorrektur**, Test-Commit löscht nur, kein Code nach dem Test, „entfällt“ trotz Code, GitHub antwortet mit Fehler → „nicht prüfbar“. Dazu: der Ablauf hat nur Leserechte, setzt keinen fremden Text in Befehle ein, nutzt kein `pull_request_target`; fremder Text in Meldungen wird bereinigt.
- Rot vor Grün: Tests zuerst (Commit `ec80e4f`, Korrektur nur an den neuen Tests `2a260d7`), am Gerüst `16e0397` 53 rot, 60 grün, aus den erwarteten Gründen (Prüfregel fehlt, Ablaufdatei fehlt, Regeltext fehlt); von der Hauptsession in einer eigenen Arbeitskopie wiederholt. Am neuen Stand alle grün.
- Lokal ausgeführte Prüfungen nach `CLAUDE.md`, Ablauf je Aufgabe Nr. 4 (welcher Lauf, welche Tests mit Begründung, wie viele übersprungen): schneller Lauf `./pruefen.sh schnell tests/test_pr_angaben.py tests/test_arbeitsregeln.py tests/test_issue_vorlagen.py tests/test_pruefung_auf_github.py tests/test_texte.py` (die neuen Tests, die Tests, die Regeltexte und Vorlagen lesen, und die Tests zum Prüfablauf) an `accd741`: grün, 205 Tests, 0 übersprungen, zweimal hintereinander. Einmal voller Lauf `./pruefen.sh` an `04e04fc` (Ausnahme in Nr. 4, weil ein Prüfablauf auf GitHub dazukommt): alle acht Prüfungen grün, 1.585 Tests, 252 Rauchtests, 125 übersprungen (Firefox auf dem Mac), Container 9, 38 min 47 s (Rechner stark ausgelastet; der erste Versuch war rot, nur weil Docker nicht lief). Nach den Korrekturen aus der unabhängigen Prüfung nur der schnelle Lauf; der volle Lauf kommt auf GitHub.
- Prüfungen auf GitHub für den letzten Stand (alle grün?): ja, für `accd741`. „Prüfungen“ grün ([Lauf 41650684481](https://github.com/sebivtt/dpv-participant-management/actions/runs/41650684481), 33:57, Schlusszeile „Alle Prüfungen grün.“; Tests 10:28, Rauchtests 18:44). „PR-Angaben“: erst rot, wie für die Probe gewollt ([Lauf 41650684659](https://github.com/sebivtt/dpv-participant-management/actions/runs/41650684659): Zeile „Test-Commit“ fehlte, und meine eigene Beschreibung nannte als Beispiel zwei weitere Issues so, dass GitHub #13 mitgeschlossen hätte); nach dem Bearbeiten der Beschreibung ohne neuen Commit grün, und der lange Lauf startete dabei nicht neu. Kein Neustart.
- Rauchtest des Hauptablaufs: nicht betroffen (keine Seite geändert); läuft im vollen Lauf mit.
- Unabhängige Prüfung: Befunde und was daraus wurde: einmal, 0 hoch, 2 mittel, 4 gering, alle selbst nachgeprüft und behoben, je mit Test zuerst (`aa8fb5a`, rot) und dann Code (`accd741`): B1 (mittel) Beschreibung oder Issue mit Zeilenenden aus dem Browser (`\r\n`) wurde fälschlich rot → Zeilenenden vereinheitlicht. B2 (mittel) „Fixes“ oder „Closes“ mit Doppelpunkt vor der Nummer, mit der Adresse eines Issues oder mit `inhaber/repo` davor schließen auf GitHub ein zweites Issue und blieben unbemerkt → jede Form außer genau einem „Closes #N“ ist rot. B3 (gering) Vorlage erklärt jetzt die Form „- Szenarien: keine, weil …“; Links mit Großbuchstaben zählen. B4 (gering) ein Merge-Commit („Update branch“) zählt nicht als eigener Code; bei der Erwartung eines neuen Tests lag ich zuerst falsch und habe sie in eigenem Commit `cabf03b` korrigiert. B5 (gering) der Zugangsschlüssel geht bei einer Weiterleitung nicht mit; Kommentar oder Issue aus einem anderen Repo zählen nicht. B6 (gering) Tests für Abruf, `main()`, 300 Dateien und Umbenennung ergänzt. Hinweis der Prüfung: `2a260d7` passt zwei der neuen Regeltests an den gewählten Wortlaut in `CLAUDE.md` an (siehe Abweichung oben).

## Datenmodell oder Rechte

Nicht betroffen.

- Neue Daten? Keine. Rechtematrix: keine Zeile.

## Neue Pakete

Keine (nur Python-Standardbibliothek).

## Aus dem alten Repo übernommen

Nichts.

## Nicht geprüft und offen

- Ändert sich nach der letzten Prüfung nur etwas am Issue (Label, Text, Szenarien), läuft „PR-Angaben“ nicht von selbst neu; die Regel verlangt dann vor dem Link einen neuen Lauf.
- Ein Pull Request, der das Prüfskript oder den Prüfablauf selbst ändert, prüft sich mit der geänderten Fassung (so auch dieser). Das ist in der Liste der Dateien sichtbar und Sache der unabhängigen Prüfung.
- Pull Requests mit Merge-Commits (etwa nach Abgleich mit `main`) sind nicht eigens getestet; ein Merge-Commit zählt mit seinen Dateien gegenüber dem ersten Vorgänger.
- Bei der Umsetzung hat die KI zweimal versucht, `.env` in eine Hilfskopie zu kopieren; die Sperre hat beide Male gegriffen und wurde nicht umgangen. Anlass war mein Auftrag (Rot-Grün in einer Hilfskopie), der nicht sagte, wie das ohne `.env` geht.
- Ob die KI-Sitzungen die Regel künftig einhalten, zeigt sich erst an den nächsten Pull Requests (Beobachtung der Projektprüfung).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

