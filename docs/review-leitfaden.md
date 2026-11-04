# Leitfaden: externes Review am Phasenende

Am Ende jeder Phase P1 bis P10 prüfen zwei externe KI-Modelle unabhängig voneinander den ganzen Stand des Repos. Ihre Befunde werden nachgeprüft, eingeordnet und erst nach einer Klärung mit `grill-me` umgesetzt. Entschieden am 21.10.2026 (#26, Protokoll dort; `docs/entscheidungen.md`).

Das Review sucht, was im Alltag durchrutscht: Lücken bei Rechten, Datenschutz und Sicherheit, Abschlusskriterien, die nur scheinbar erfüllt sind, widersprüchliche Anforderungen und fehlende Tests. Ein Modellurteil gilt nie von selbst als wahr. Maßgeblich sind der nachgeprüfte Beleg, Sebastians Entscheidung und die Prüfung nach der Behebung.

## 1. Abgrenzung

| Prüfung | Wann | Was | Wer |
| --- | --- | --- | --- |
| Unabhängige Prüfung (`CLAUDE.md`) | vor jedem Pull Request | der Diff, dazu Issue, nötige Aufrufer und Nachbarstellen | zweite Claude-Instanz |
| Prüfung vom 20.10.2026 (`docs/pruefung-2026-10-20.md`) | einmalig | Fahrplan und Anforderungen | ChatGPT und Gemini, ausgewertet von Claude |
| **Externes Review** (dieser Leitfaden) | am Ende jeder Phase P1 bis P10 | der ganze Stand zum geprüften Commit | zwei externe Modelle, zusammengeführt von Claude |
| Prüfer (`docs/fahrplan.md`, E1, E3, E6) | an drei Prüfpunkten | ob die Basis trägt | ein Mensch |

Das Review ersetzt keine der anderen Prüfungen. Übernommen aus der Prüfung vom 20.10.2026: die Bewertung **Beleg** (mit Fundstelle nachgeprüft) gegenüber **Annahme** (nicht im Projekt belegt), die Einordnung je Befund mit Begründung und die Gegenüberstellung, wo die Modelle übereinstimmen und wo sie sich widersprechen.

## 2. Wann und mit welcher Folge

- Das Review beginnt, sobald alle Abschlusskriterien der Phase (`docs/fahrplan.md`, Abschnitt 3) erfüllt scheinen. P0 bekommt keins, weil sie keinen Code hat.
- Die Phase gilt erst als abgeschlossen, wenn das Review-Issue eingeordnet ist und alle blockierenden Befunde behoben sind. Erst dann wechselt der „Stand“ im `README.md` zur nächsten Phase.
- Aufwand für Sebastian: rund 2,5 Stunden je Review (Annahme). Nach dem Review zu P2 wird das Verfahren ausgewertet (#35).

## 3. Was geprüft wird

- **Umfang:** der ganze Stand zum geprüften Commit: Code, Tests und Doku. Schwerpunkt ist, was in der Phase neu kam.
- **Abschlusskriterien:** Jedes Abschlusskriterium der Phase wird bewertet: erfüllt, nicht erfüllt oder nicht prüfbar, jeweils mit Fundstelle. „Nicht prüfbar“ ist erlaubt, z. B. für alles, was nur im Browser oder auf dem Testserver sichtbar ist.
- **Widersprüche** zwischen Anforderungen, Fahrplan, Entscheidungen und Code werden gemeldet, nie von einem Modell aufgelöst. Aufgelöst werden sie fachlich von Sebastian.
- **Zwei Schwerpunkte:**
  - **A, breiter Blick:** Anforderungen und Abschlusskriterien, fehlende oder schwache Tests, Verständlichkeit, Widersprüche in der Doku, Regeln aus `CONTRIBUTING.md`.
  - **B, Sicherheit, Rechte und Datenschutz:** Zugriff ohne Recht, auch über direkte Adressen, Kennungen, htmx-Anfragen und manipulierte Formulare; Personen- und Gesundheitsdaten in Logs, Mails oder Adressen; Zugangsdaten; Datenintegrität und gleichzeitige Anfragen.

## 4. Wer prüft

- **Zwei Modelle,** jedes mit einem Schwerpunkt aus Abschnitt 3. Für den Pilot nach P1: A = ChatGPT, B = Gemini, jeweils das stärkste Modell in Sebastians Abo. Der Leitfaden schreibt keinen Anbieter vor; das Review-Issue nennt Modell und Fassung, soweit bekannt.
- **Unabhängig:** B bekommt den Bericht von A erst, nachdem B seinen eigenen Bericht abgegeben hat.
- **Claude prüft nicht als A oder B,** weil Claude den Code schreibt. Claude führt in einer eigenen Sitzung zusammen (Abschnitt 7).
- **Ein drittes Modell** prüft nur in zwei Fällen:
  1. Bei einem möglicherweise blockierenden Befund widersprechen sich A und B, und die Nachprüfung klärt es nicht. Das dritte Modell bekommt dann nur diesen Befund mit beiden Begründungen.
  2. Immer beim Review nach P6, weil danach echte Daten kommen (Tor E3). Es bekommt Prüfauftrag B.

## 5. Datenschutz und Grenzen

- **DSG-08:** Externe Modelle bekommen nur den Inhalt des Repos als ZIP-Datei. Nie echte Personen- oder Gesundheitsdaten, nie Auszüge aus Server-Logs, nie Bildschirmfotos aus dem Betrieb, nie Zugangsdaten. Die Datei `.env` ist nicht im Repo und deshalb nie in der ZIP-Datei. Die Konten in `dev/keycloak/dpv-realm.json` sind erkennbar erfunden.
- **Kein dauerhafter Zugriff:** keine GitHub-Verbindung der Modelle zum Repo. Die ZIP-Datei enthält genau den geprüften Commit.
- **Lesend:** Die Modelle ändern nichts, sie schreiben nur ihren Bericht. Die Claude-Sitzung, die zusammenführt, schreibt nur ins Review-Issue; Befund-Issues legt sie erst nach Sebastians Entscheidung an. Code, Doku und andere Issues ändert dabei niemand. Änderungen entstehen erst im üblichen Ablauf je Issue (`CLAUDE.md`, „Ablauf je Aufgabe“).
- **Kein Modell entscheidet:** Keine Vermutung gilt als bestätigter Fehler, kein fachlicher Widerspruch wird von einem Modell aufgelöst, kein Befund wird ohne Klärung umgesetzt.

## 6. Ablauf für Sebastian

Je Schritt genau ein Befehl im Programm „Terminal“, dazu, was danach zu sehen sein sollte.

1. In den Ordner des Projekts wechseln.
   ```bash
   cd ~/Entwicklung/dpv-participant-management
   ```
   Danach: keine Ausgabe.
2. Zum Stand von `main` wechseln.
   ```bash
   git switch main
   ```
   Danach: `Switched to branch 'main'` oder `Already on 'main'`. Steht dort `error: Your local changes … would be overwritten`, gibt es auf dem Mac ungesicherte Änderungen: Sie zuerst mit der KI sichern oder verwerfen, dann diesen Schritt wiederholen.
3. Den neuesten Stand von GitHub holen.
   ```bash
   git pull
   ```
   Danach: `Already up to date.` oder eine Liste geänderter Dateien.
4. Die Kennung des geprüften Commits anzeigen.
   ```bash
   git rev-parse HEAD
   ```
   Danach: eine Zeile aus 40 Zeichen, z. B. `7d5f673d097ad2bdacec3366abd4d887bde780ff`. Diese Kennung kommt ins Review-Issue und in die Prüfaufträge.
5. Die ZIP-Datei genau dieses Stands erzeugen. Statt `7d5f673` die Kennung aus Schritt 4 eintragen.
   ```bash
   git archive --format=zip --output ~/Downloads/externes-review.zip 7d5f673
   ```
   Danach: keine Ausgabe; im Ordner „Downloads“ liegt `externes-review.zip`. Sie enthält alle Dateien des Repos außer den fremden Bibliotheken Bootstrap und axe-core (`.gitattributes`).
6. Auf GitHub ein Issue nach der Vorlage **Externes Review einer Phase** anlegen. Phase, Commit aus Schritt 4, Datum und geprüfte Bereiche eintragen; im Titel die Phase anpassen.
7. **ChatGPT:** einen neuen Chat öffnen, die ZIP-Datei hochladen und Prüfauftrag A (Abschnitt 9) hineinkopieren; vorher `[PHASE]` durch die Phase (z. B. P1) und `[KENNUNG]` durch die Kennung aus Schritt 4 ersetzen. Den fertigen Bericht kopieren.
8. **Gemini:** einen neuen Chat öffnen, die ZIP-Datei hochladen und Prüfauftrag B hineinkopieren, mit Phase und Kennung wie in Schritt 7. Erst wenn der Bericht fertig ist, den Nachtrag zu Prüfauftrag B mit dem Bericht von ChatGPT schicken.
9. Jeden Bericht unverändert als eigenen Kommentar ins Review-Issue stellen, eingeklappt mit diesem Rahmen; in die leere Zeile den Bericht einfügen:
   ```text
   <details><summary>Bericht A: ChatGPT, Modell laut Chat</summary>

   </details>
   ```
   Bei Gemini „Bericht B“, beim Nachtrag „Nachtrag B“.
10. **Nur nach P6:** einem dritten Modell in einem neuen Chat die ZIP-Datei und Prüfauftrag B geben und den Bericht als „Bericht C“ wie in Schritt 9 ins Review-Issue stellen.
11. Eine neue Claude-Sitzung starten und den Auftrag zur Zusammenführung (Abschnitt 9) mit der Nummer des Review-Issues hineinkopieren.
12. **Nur wenn die Zusammenführung ein drittes Modell vorschlägt** (Abschnitt 4, Fall 1): einem dritten Modell in einem neuen Chat die ZIP-Datei und den Auftrag „Strittiger Befund“ (Abschnitt 9) geben; die Zusammenführung füllt ihn vorher mit dem Befund und beiden Begründungen aus. Die Antwort als „Bericht C“ wie in Schritt 9 ins Review-Issue stellen und der Claude-Sitzung Bescheid geben.
13. Die vorgeschlagene Einordnung durchgehen und je Befund entscheiden. Danach legt die Claude-Sitzung die Befund-Issues an.
14. Jedes Befund-Issue vor der Umsetzung mit `grill-me` klären, wie jedes andere Issue. Blockierende zuerst. Nach jeder Behebung wird geprüft wie in `CLAUDE.md`, Ablauf je Aufgabe Nr. 4 (mit `./pruefen.sh`); im Befund-Issue steht, womit geprüft wurde.
15. Sind alle Befunde eingeordnet und alle blockierenden behoben: die Abschlussentscheidung ins Review-Issue schreiben und es schließen. Erst dann wechselt der „Stand“ im `README.md`.

## 7. Zusammenführung

Eine eigene Claude-Sitzung, ohne Kenntnis der Sitzungen, die den Code der Phase geschrieben haben:

- prüft jeden Befund am geprüften Commit nach: mit Fundstelle bestätigt heißt **Beleg**, sonst **Annahme**. Wo ein Befund Verhalten betrifft, führt sie die Tests in einer eigenen Arbeitskopie dieses Commits aus;
- bündelt Doppelte und hält fest, wo A und B übereinstimmen und wo sie sich widersprechen; schlägt bei einem strittigen, möglicherweise blockierenden Befund das dritte Modell vor und füllt dafür den Auftrag „Strittiger Befund“ aus (Abschnitt 4); Sebastian gibt ihn weiter, weil die Sitzung selbst keine anderen Modelle erreicht;
- schlägt je Befund eine Stufe vor (Abschnitt 8), mit Begründung;
- schreibt das Ergebnis in den Text des Review-Issues (Felder „Modelle und Fassungen“, „Ergebnisse“ und später „Verlinkte Befunde“) und ändert sonst nichts; die Abschlussentscheidung schreibt Sebastian;
- legt nach Sebastians Entscheidung je eigenständig bearbeitbarem Befund ein Issue nach der Vorlage **Befund aus einem externen Review** an und verlinkt es im Review-Issue. Labels: `review-befund`, das Phasen-Label der Phase, in der er erledigt wird, bei „später“ zusätzlich `vorgemerkt`.

Ein Befund-Issue nur, wenn sich der Befund eigenständig bearbeiten lässt. Duplikate werden zusammengeführt. Fehlalarme, Duplikate und akzeptierte Risiken stehen nur im Review-Issue, mit Begründung.

## 8. Stufen

| Stufe | Bedeutung | Folge |
| --- | --- | --- |
| blockierend | Lücke bei Rechten, Datenschutz oder Sicherheit; möglicher Datenverlust; eine falsche Kernregel; ein Abschlusskriterium der Phase ist in Wahrheit nicht erfüllt | vor Abschluss der Phase behoben, nicht nur entschieden |
| zeitnah | echter Fehler ohne diese Folgen | in der nächsten Phase erledigt |
| später | Verbesserung | eigenes Issue mit `vorgemerkt` und Phasen-Label |
| Fehlalarm oder Duplikat | nicht nachweisbar, falsch oder schon erfasst | nur im Review-Issue, mit Begründung |
| akzeptiertes Risiko | bewusst nicht behoben | nur durch Sebastian, mit Begründung in `docs/entscheidungen.md` |

Bei Sicherheit und Datenschutz gibt es kein akzeptiertes Risiko (`docs/fahrplan.md`, Risiken: „bei Sicherheit und Datenschutz wird nie gekürzt“). Ein Härtungshinweis dort ohne konkrete Lücke darf mit Begründung auf „später“, ist aber vor E3 erledigt.

Befund-Issues gibt es nur für die ersten drei Stufen. Zeigt sich beim Klären mit `grill-me`, dass ein Befund ein Fehlalarm ist, wird sein Issue mit Begründung geschlossen und die Einordnung im Review-Issue nachgetragen.

## 9. Prüfaufträge zum Hineinkopieren

In jedem Auftrag `[PHASE]` durch die Phase (z. B. P1) und `[KENNUNG]` durch die Kennung aus Schritt 4 ersetzen.

### Prüfauftrag A: breiter Blick

```text
Phase: [PHASE]
Commit: [KENNUNG]

Du prüfst als unabhängiges Review den Stand eines Software-Projekts am Ende dieser Phase.
Die ZIP-Datei enthält genau diesen Commit des Repos „DPV Anmeldetool“,
eines Anmeldetools für Pfadfinderveranstaltungen (Django, PostgreSQL, Login über Keycloak).

Lies zuerst CLAUDE.md, CONTRIBUTING.md und alle Dateien in docs/. Maßgeblich sind
docs/anforderungen.md (Anforderungen mit IDs) und docs/fahrplan.md (Phasen und
Abschlusskriterien, Abschnitt 3). Was in docs/entscheidungen.md steht, ist entschieden.

Grenzen:
- Du arbeitest nur lesend und schlägst Korrekturen höchstens vor. Du entscheidest keine
  fachlichen Widersprüche; du meldest sie.
- Das Repo enthält nur erfundene Testdaten. Siehst du etwas, das wie echte Personendaten
  aussieht, melde nur die Fundstelle und wiederhole den Inhalt nicht.
- Trenne strikt: „belegt“ heißt, du nennst Datei und Zeile, an der man es nachprüfen kann.
  Alles andere ist „vermutet“. Keine Vermutung als Tatsache.

Schwerpunkt: der breite Blick. Anforderungen und Abschlusskriterien, fehlende oder
schwache Tests, Verständlichkeit, Widersprüche zwischen Anforderungen, Fahrplan,
Entscheidungen und Code, Verstöße gegen die Regeln in CONTRIBUTING.md.
Geprüft wird der ganze Stand, mit Schwerpunkt auf dem, was in dieser Phase neu kam.

Liefere:
1. Eine Tabelle mit jedem Abschlusskriterium dieser Phase aus docs/fahrplan.md:
   erfüllt / nicht erfüllt / nicht prüfbar, mit Fundstelle und einem Satz Begründung.
2. Deine Befunde, nummeriert A1, A2, …, nach Schwere sortiert. Je Befund:
   - Kategorie (Rechte, Datenschutz, Sicherheit, Datenintegrität, Abschlusskriterium
     nicht erfüllt, Widerspruch in Anforderungen oder Doku, fehlender Test,
     Verständlichkeit, Sonstiges)
   - Fundstelle (Datei und Zeile oder Abschnitt)
   - Beobachtung: was genau falsch ist oder fehlt, als konkreter Fall
   - Beleg oder Weg zum Nachstellen
   - mögliche Auswirkung
   - Sicherheit: belegt oder vermutet
   - vorgeschlagene Stufe: blockierend, zeitnah, später oder akzeptiertes Risiko
     (Bedeutung in docs/review-leitfaden.md, Abschnitt 8)
3. Was du nicht prüfen konntest und warum.
Antworte auf Deutsch.
```

### Prüfauftrag B: Sicherheit, Rechte und Datenschutz

```text
Phase: [PHASE]
Commit: [KENNUNG]

Du prüfst als unabhängiges Review den Stand eines Software-Projekts am Ende dieser Phase.
Die ZIP-Datei enthält genau diesen Commit des Repos „DPV Anmeldetool“,
eines Anmeldetools für Pfadfinderveranstaltungen (Django, PostgreSQL, Login über Keycloak).
Später verarbeitet es Daten von Kindern und Gesundheitsdaten.

Lies zuerst CLAUDE.md, CONTRIBUTING.md (vor allem Abschnitt 4) und alle Dateien in docs/.
Maßgeblich sind docs/anforderungen.md (Anforderungen mit IDs) und docs/fahrplan.md
(Phasen und Abschlusskriterien, Abschnitt 3). Was in docs/entscheidungen.md steht,
ist entschieden.

Grenzen:
- Du arbeitest nur lesend und schlägst Korrekturen höchstens vor. Du entscheidest keine
  fachlichen Widersprüche; du meldest sie.
- Das Repo enthält nur erfundene Testdaten. Siehst du etwas, das wie echte Personendaten
  aussieht, melde nur die Fundstelle und wiederhole den Inhalt nicht.
- Trenne strikt: „belegt“ heißt, du nennst Datei und Zeile, an der man es nachprüfen kann.
  Alles andere ist „vermutet“. Keine Vermutung als Tatsache.

Schwerpunkt: Sicherheit, Rechte und Datenschutz. Zugriff ohne Recht, auch über direkte
Adressen, Kennungen, htmx-Anfragen und manipulierte Formulare; Adressen ohne Login;
Personen- oder Gesundheitsdaten in Logs, Mails, Fehlerseiten oder Adressen; Zugangsdaten
im Code; Sitzung und Abmelden; Datenintegrität und gleichzeitige Anfragen; Pakete mit
bekannten Lücken. Geprüft wird der ganze Stand, mit Schwerpunkt auf dem, was in dieser
Phase neu kam.

Liefere:
1. Eine Tabelle mit jedem Abschlusskriterium dieser Phase aus docs/fahrplan.md, das
   Sicherheit, Rechte oder Datenschutz berührt: erfüllt / nicht erfüllt / nicht prüfbar,
   mit Fundstelle und einem Satz Begründung.
2. Deine Befunde, nummeriert B1, B2, …, nach Schwere sortiert. Je Befund:
   - Kategorie (Rechte, Datenschutz, Sicherheit, Datenintegrität, Abschlusskriterium
     nicht erfüllt, Widerspruch in Anforderungen oder Doku, fehlender Test,
     Verständlichkeit, Sonstiges)
   - Fundstelle (Datei und Zeile oder Abschnitt)
   - Beobachtung: was genau falsch ist oder fehlt, als konkreter Fall
   - Beleg oder Weg zum Nachstellen
   - mögliche Auswirkung
   - Sicherheit: belegt oder vermutet
   - vorgeschlagene Stufe: blockierend, zeitnah, später oder akzeptiertes Risiko
     (Bedeutung in docs/review-leitfaden.md, Abschnitt 8)
3. Was du nicht prüfen konntest und warum.
Antworte auf Deutsch.
```

### Nachtrag zu Prüfauftrag B

Erst schicken, wenn der Bericht B fertig ist; darunter den Bericht A einfügen.

```text
Hier ist der Bericht eines anderen, unabhängigen Reviews desselben Commits. Ändere deine
eigenen Befunde nicht. Nenne nur:
1. bei welchen Befunden du zustimmst (Nummern),
2. wo du widersprichst, mit Fundstelle und Begründung,
3. was du nach dem Lesen zusätzlich siehst, nummeriert B-N1, B-N2, … im selben Format
   wie deine Befunde.
```

### Auftrag zur Zusammenführung (Claude)

```text
Führe das externe Review nach docs/review-leitfaden.md zusammen, Abschnitt 7.
Review-Issue: Nummer hier eintragen. Die Berichte stehen dort als Kommentare.
Arbeite nur lesend: keine Änderung an Code, Doku oder anderen Issues, kein Commit,
kein Pull Request. Schreib nur in den Text des Review-Issues (Felder „Modelle und
Fassungen“, „Ergebnisse“ und „Verlinkte Befunde“).
Leg Befund-Issues erst an, nachdem ich die Einordnung entschieden habe.
```

### Strittiger Befund (drittes Modell)

Die Zusammenführung füllt die eckigen Klammern aus; Sebastian gibt den Text mit der ZIP-Datei weiter.

```text
Phase: [PHASE]
Commit: [KENNUNG]

Die ZIP-Datei enthält genau diesen Commit des Repos „DPV Anmeldetool“. Zwei unabhängige
Reviews sind sich bei einem Befund uneinig. Prüf nur diesen Befund, nur lesend.

Befund: [BEFUND MIT FUNDSTELLE]
Begründung Review A: [BEGRÜNDUNG A]
Begründung Review B: [BEGRÜNDUNG B]

Antworte: Besteht das Problem? Belegt (mit Datei und Zeile) oder vermutet? Welche Stufe
schlägst du vor: blockierend, zeitnah oder später (Bedeutung in docs/review-leitfaden.md,
Abschnitt 8)? Das Repo enthält nur erfundene Testdaten. Antworte auf Deutsch.
```
