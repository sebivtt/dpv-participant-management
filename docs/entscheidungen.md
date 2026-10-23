# Entscheidungen

Fachliche und technische Entscheidungen mit Begründung. Neue Einträge oben. Wer eine Regel ändern will, ergänzt einen neuen Eintrag, statt einen alten zu überschreiben.

Format: Datum · Entscheidung · Begründung · Umsetzung

---

## 2026-10-23 · Protokoll der Rollenänderungen (#91): nur schreiben in P2 (W4), Namen zum Zeitpunkt, Sperre in der Datenbank

**Entscheidung** (Sebastian; Bestandsaufnahme P2 vom 22.10.2026, [W4 in #106](https://github.com/sebivtt/dpv-participant-management/issues/106#issuecomment-6342842432); Klärung von #91 am 22.10.2026; Nachklärung P2 vom 22.10.2026 in #106, Frage 2; [Fragen bei der Umsetzung](https://github.com/sebivtt/dpv-participant-management/issues/91#issuecomment-6360190203) am 23.10.2026):

1. **W4, Einsicht in Protokolle (ROL-03 gegen ADM-03):** In P2 werden das Protokoll der Rollenänderungen (#91) und das Protokoll der Admin-Zugriffe (#92) nur geschrieben und getestet, auch dass sich Einträge nicht ändern oder löschen lassen. Die Einsicht für Admins und Verbandsleitung kommt mit ADM-03 in P8; bis dahin gilt die Ausnahme in ROL-03 noch nicht.
2. **Was ins Protokoll kommt:** jedes tatsächliche Vergeben und Entfernen einer Rolle aus ROL-01, auch der Mitgliedschaft (aufnehmen, beenden, wechseln, automatisch beim Einsetzen als Leitung) und der Admin-Befehle auf dem Server. Ein Wechsel ergibt „entfernt“ und „vergeben“ mit derselben Uhrzeit. Abgelehnte Versuche und Speichern ohne Änderung schreiben nichts. Es gibt kein Feld für einen Grund oder freien Text, weil darin Gesundheitsangaben landen könnten.
3. **Urheber:** Der Eintrag nennt nur die Person, die geändert hat, nicht die Rolle, in der sie gehandelt hat; bei mehreren passenden Rollen wäre unklar, welche gemeint ist. Bei Befehlen auf dem Server steht „Befehl auf dem Server“.
4. **Namen zum Zeitpunkt der Änderung:** Der Eintrag hält die Namen von Person, Urheber und Organisation fest, wie sie damals hießen; eine spätere Umbenennung ändert ihn nicht. Ein Eintrag hindert nie daran, später ein Konto zu löschen. Was dann mit den Einträgen geschieht und wie lange sie bleiben, klärt #66 (DSG-09, OP-2); in P2 wird nichts gelöscht.
5. **Testdaten-Befehl:** Lokal und in der Testumgebung darf der Befehl aus #103 die Datenbank vollständig leeren, auch das Protokoll. Die Sperre im Tool bleibt.
6. **Rechtematrix:** Die Zeilen für das Protokoll kommen mit #87, weil es die Matrix bei #91 noch nicht gab (Hinweis in #87).

**Technische Wahl** (KI):

- **Eine Tabelle `roles.RoleChange`** in der App der Rollen. Kennungen von Urheber, Person und Einheit stehen als Zahlen darin, nicht als Verweise; sonst ließe sich ein Konto, das je eine Rolle hatte, nie löschen, oder die Datenbank müsste den Eintrag beim Löschen ändern.
- **Wer ändert, ist Pflicht:** Speichern und Löschen einer Rolle verlangen die Angabe `by` (Konto oder `SERVER_COMMAND`); ohne sie lehnt das Tool ab. So kann keine spätere Seite (#65, #93, #94, #92, #103) den Urheber still vergessen. Die bestehenden Tests in `tests/test_rollen.py` und `tests/test_rollen_befehle.py` geben deshalb an, wer ändert; ihre Regeln blieben gleich.
- **Beides oder nichts:** Rolle und Eintrag werden in derselben Datenbank-Transaktion geschrieben. Die Uhrzeit ist der Beginn der äußersten laufenden Transaktion, deshalb tragen zusammengehörige Einträge genau dieselbe. Öffnet eine spätere Seite oder ein Befehl vorher selbst eine Transaktion, ist es deren Beginn; das Tool tut das in P2 nicht. Die Reihenfolge der Einträge gibt ihre laufende Nummer an, nicht die Uhrzeit: Bei gleichzeitigen Änderungen kann eine früher begonnene Transaktion später schreiben.
- **Sperre doppelt:** Im Programm lehnt das Tool Ändern und Löschen eines Eintrags ab. Zusätzlich lehnt eine Regel in der Datenbank (Trigger) jedes `UPDATE` und `DELETE` auf der Tabelle ab, auch Sammeländerungen am Programm vorbei. Offen bleibt nur das vollständige Leeren (`TRUNCATE`), das der Testdaten-Befehl (#103) und der Testlauf brauchen; im Tool gibt es dafür keinen Weg. Wer direkt in der Datenbank auf dem Server arbeitet, kann den Trigger entfernen; das gehört ins Betriebshandbuch (P6).
- **Grenze:** Sammeländerungen an den Rollen selbst (`update()`, `bulk_create()`, `QuerySet.delete()`) umgehen wie schon die Regeln aus #89 auch das Protokoll. Das Tool nutzt sie für Rollen nicht.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Protokoll der Rollenänderungen `role_change` (`RoleChange`), Urheber `actor`, vergeben `granted`, entfernt `removed`, Befehl auf dem Server `SERVER_COMMAND`.

**Umsetzung:** `roles/models.py` (`RoleChange`, Einträge beim Speichern und Löschen), `roles/expressions.py`, `roles/migrations/0002_role_change.py` (Tabelle und Trigger), `roles/texts.py`, `roles/management/commands/admin.py`, `README.md` (Abschnitt „Admins ernennen und entfernen“), Tests in `tests/test_rollen_protokoll.py`; Anpassungen in `tests/test_rollen.py` und `tests/test_rollen_befehle.py`.

## 2026-10-23 · Rollen: Mitgliedschaft und Leitungspfad, Rolle Admin, ROL-01 ergänzt

**Entscheidung** (Sebastian; Klärung von #89 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/89#issuecomment-6343606180); Nachklärung P2 vom 22.10.2026 in #106, Fragen 4 und 9; Fragen bei der Umsetzung am 23.10.2026 in #89):

1. **Mitgliedschaft und Leitung sind getrennt.** Eine Person mit Account ist Mitglied in höchstens einer Einheit (Gruppe, Stamm, Ring oder Bund), nie im Verband. Leitungsrollen hat sie nur auf ihrem Pfad: im eigenen Stamm (auch in anderen Gruppen dort) und in den Einheiten darüber; ist sie direkt Mitglied eines Rings oder Bundes, auch in allen Einheiten darunter. Sonst lehnt das Tool ab und nennt den Grund.
2. **Automatische Mitgliedschaft:** Wer ohne Mitgliedschaft als Leitung einer Gruppe, eines Stammes, eines Rings oder eines Bundes eingesetzt wird, wird Mitglied der geleiteten Einheit und bleibt es, wenn die Leitung endet. Verbandsleitung und DPV-Veranstaltungsteam brauchen keine Mitgliedschaft und legen keine an.
3. **Wechsel und Ende der Mitgliedschaft** gehen nur, wenn danach alle Leitungsrollen in Einheiten noch auf dem Pfad liegen; ohne Mitgliedschaft heißt das: keine Leitungsrollen in Einheiten. Sonst nennt das Tool die Rollen, die zuerst entfernt werden müssen. Leitungsrollen werden nie automatisch entfernt. Am 23.10.2026 hat Sebastian erwogen, beim Austreten die Leitungsrollen mit enden zu lassen, und ist nach dem Hinweis auf #65 und den Wortlaut von ROL-01 bei der geklärten Regel geblieben (F1 in #89).
4. **Admin** gibt keine Rechte einer Leitung; Personendaten sieht ein Admin nur über den Support-Weg mit Protokoll (#92). Admin wird man bis ADM-01 (P6) nur per Befehl auf dem Server, über den Benutzernamen eines Kontos, das sich schon einmal angemeldet hat; ein zweiter Befehl entfernt das Recht, auch beim letzten Admin. Rechte entstehen nur aus Rollen, nie aus Keycloak und nie daraus, wer etwas angelegt hat.
5. **ROL-01 ergänzt** (#109) um den Satzteil ab „Eine Person mit Account ist Mitglied in höchstens einer Einheit …“ bis „Ohne Leitungsrolle kann sie selbst aus ihrer Einheit austreten.“, im Wortlaut der Nachklärung vom 22.10.2026, dem Sebastian zugestimmt hat.

**Technische Wahl** (KI):

- **Eine Tabelle für alle Rollen** (`roles.Role`: Person, Rolle, Einheit), auch für die Mitgliedschaft. So setzt die Datenbank „höchstens eine Mitgliedschaft“, „dieselbe Rolle je Einheit nur einmal“, „Admin ohne Einheit, alle anderen mit“ selbst durch, und das Protokoll (#91) beobachtet nur eine Stelle. Welche Rolle zu welcher Ebene passt und der Pfad stehen in der Regelprüfung beim Speichern und Löschen.
- **Admin nicht als Djangos „Superuser“:** Der hätte automatisch alle Rechte; ein Admin bekommt dadurch keine.
- **Gleichzeitige Änderungen:** Jede Änderung an den Rollen einer Person sperrt deren Konto kurz; so sehen die Regeln immer den aktuellen Stand, etwa wenn ein Wechsel und eine neue Leitung zugleich kommen.
- **Nur die Einheit einer Mitgliedschaft lässt sich ändern** (Wechsel). Jede andere Rolle wird entfernt und neu gegeben, damit jede Änderung als solche im Protokoll steht (#91).
- **Löschschutz:** Eine Einheit, an der eine Rolle hängt, und ein Konto mit Rollen lassen sich in der Datenbank nicht löschen.
- **Meldungen** nennen Namen in Anführungszeichen ohne Artikel („keine Leitung in „Zugvögel““), weil sich Namen nicht automatisch beugen lassen; Gruppen mit ihrem Stamm in Klammern. Meldungen, die die Einheit der Person nennen (Pfad, zweite Mitgliedschaft, Rollen zuerst entfernen), tragen je einen eigenen Code (`outside_path`, `second_membership`, `remove_roles_first`), damit #65, #93 und #94 bei fremden Personen eine Fassung ohne Einheit zeigen können (BER-01).
- **Befehl:** `python manage.py admin grant|revoke BENUTZERNAME` (Anleitung im `README.md`). Wer schon Admin ist, bekommt beim Ernennen nur einen Hinweis.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Rolle `role`, Mitglied `member`, Gruppenleitung `group_lead`, Stammesleitung `troop_lead`, Ringleitung `ring_lead`, Bundesleitung `association_lead`, Verbandsleitung `federation_lead`, DPV-Veranstaltungsteam `event_team`, Admin `admin`.

**Umsetzung:** `roles/` (Datenmodell, Migration, Regeln, Meldungen, Befehl `admin`), `config/settings.py`, `.dockerignore`, `README.md` (Abschnitt „Admins ernennen und entfernen“), `docs/anforderungen.md` (ROL-01), Tests in `tests/test_rollen.py` und `tests/test_rollen_befehle.py`; `tests/test_testumgebung_aufbau.py` nennt die neue App.

## 2026-10-23 · Einheiten: kein Löschknopf (W5), Ring-Schalter, Personen auf jeder Ebene, eindeutige Namen

**Entscheidung** (Sebastian; Klärung von #88 am 22.10.2026, Nachklärung P2 vom 22.10.2026 in #106, Fragen bei der Umsetzung am 23.10.2026 in #88). Das sind Auslegungen von ORG-01 und ORG-06; der Text der Anforderungen bleibt.

1. **W5, Einheiten löschen:** In P2 gibt es in der Oberfläche keinen Löschknopf, nur Anlegen und Bearbeiten. Die Datenbank verhindert das Löschen einer Einheit, unter der noch Einheiten hängen; den Schutz für Einheiten mit Personen testen die Issues, die Personen an Einheiten hängen (#65, #97). Im Notfall löscht ein Admin eine leere Einheit per Befehl, protokolliert (#92). Löschen mit Zusammenfassung nach ORG-07 kommt später (#108).
2. **Ring-Schalter je Bund** statt Ringen fest nur im „DPBM Mosaik“: Jeder Bund hat den Schalter „hat Ringe“, Standard aus. Nur dort lassen sich Ringe anlegen, und jeder neue Stamm hängt dann in einem Ring. Einschalten geht auch, wenn der Bund schon Stämme hat; sie bleiben ohne Ring, bis sie einem zugeordnet werden (#95). Ausschalten geht nur, solange der Bund keinen Ring hat.
3. **Personen auf jeder Ebene außer dem Verband:** Personen gehören zu einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie direkt zum Verband. Das deckt „Pflegt ein Bund keine Stämme, gehören Personen direkt zum Bund“ (ORG-01) ab. Umgesetzt mit #65 und #97.
4. **Eindeutige Namen:** Kein Name ist leer, keiner ist länger als 100 Zeichen. Eindeutig sind Bünde im Verband, Ringe und Stämme zusammen im Bund (auch über verschiedene Ringe hinweg; ein Ring und ein Stamm im selben Bund heißen also nie gleich) und Gruppen im Stamm. Als gleich gilt, was sich nur in Groß- und Kleinschreibung oder Leerzeichen am Anfang oder Ende unterscheidet; Leerzeichen in der Mitte zählen („Sippe  Falken“ ist ein anderer Name als „Sippe Falken“). Stämme und Gruppen dürfen in verschiedenen Bünden bzw. Stämmen gleich heißen.
5. **Kurznamen** wie „DPV“ oder „DPBM“ kommen nicht mit #88; vorgemerkt in #124.

**Technische Wahl** (KI):

- **Eine Tabelle für alle fünf Ebenen** (`units.Unit`) mit Art, Name und der Einheit darüber, statt fünf Tabellen. Später hängen Personen, Rollen und Teilnahmekreise an Einheiten jeder Ebene; mit einer Tabelle reicht dafür ein Verweis. Nachteil: Welche Art unter welcher hängen darf, prüft das Tool beim Speichern, nicht die Datenbank. Genau ein Verband, eindeutige Namen, nicht leere Namen ohne Leerzeichen am Rand und der Löschschutz stehen zusätzlich als Regeln in der Datenbank.
- **Der Bund steht bei Ringen und Stämmen zusätzlich dabei,** damit die Datenbank selbst doppelte Stämme über Ringe hinweg verhindert, auch bei gleichzeitigen Anfragen. Damit dieser Wert nie veraltet, bleibt die Ebene einer Einheit fest, und ein Ring oder Stamm wechselt nicht den Bund. Innerhalb eines Bundes lässt sich ein Stamm weiter einem Ring zuordnen oder in einen anderen Ring verschieben (#95). Sollte ein Wechsel zwischen Bünden einmal gebraucht werden, wird er dort neu entschieden.
- **„Ring ist Pflicht“ auch beim Verschieben** (aus Frage 4 der Klärung): In einem Bund mit Ringen kommt kein Stamm neu ohne Ring an den Bund, auch nicht, indem man ihn aus seinem Ring herausnimmt. Nur Stämme von vor dem Einschalten bleiben ohne Ring.
- **Gleichzeitige Änderungen:** Beim Anlegen eines Rings oder Stammes und beim Umschalten von „hat Ringe“ sperrt das Tool den Bund kurz, sonst könnten ein neuer Ring und das Ausschalten zugleich durchgehen.
- **Befehle für Admins:** `python manage.py federation create|rename` und `python manage.py association create|rename|rings|list` (Anleitung im `README.md`). Befehlsnamen sind Code und deshalb englisch; die Meldungen sind deutsch. Umbenennen und Umschalten schreiben nur das geänderte Feld, damit zwei gleichzeitige Befehle sich nicht gegenseitig überschreiben.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Einheit `unit`, Verband `federation`, Bund `association`, Ring `ring`, Stamm `troop`, Gruppe `group`, Schalter „hat Ringe“ `has_rings`.

**Umsetzung:** `units/` (Datenmodell, Migration, Befehle, Meldungen), `config/settings.py`, `README.md` (Abschnitt „Verband und Bünde anlegen (Admins)“), Tests in `tests/test_einheiten.py`, `tests/test_einheiten_befehle.py`, `tests/test_testumgebung_aufbau.py` und `containertests/test_testumgebung_container.py`; `.dockerignore` gibt den Ordner `units/` für das Container-Abbild frei.

## 2026-10-22 · Antworten der Datenschutzperson zu OP-2

**Entscheidung** (Sebastian, 22.10.2026; #81): Die Antworten der Datenschutzperson des DPV werden so übernommen:

- **Verantwortlich** im Sinne der DSGVO ist der Betreiber, also der DPV.
- **Einwilligung:** Die Abfrage genügt, dass die angemeldeten Personen die Kriterien erfüllen bzw. die Einwilligung der Erziehungsberechtigten vorliegt (DSG-01; für die Bestätigung beim Anlegen nach DSG-02 ist das eine Auslegung der KI). Angeregt ist, zusätzlich abzufragen, dass die Personen die Teilnahmekriterien erfüllen; der Wortlaut wird beim Klären von DSG-01 festgelegt. Grundsatz: nach bestem Wissen umsetzen, handhabbar und brauchbar bleiben, Vertrauen statt übermäßiger Kontrolle. Die Idee, dass die Leitung einen Link erzeugt, über den Eltern bzw. Kinder einer Gruppenanmeldung beitreten und selbst bestätigen, kommt als Vorschlag in #44.
- **Gesundheitsangaben im eigenen Profil** (FRM-04): freiwillige Angaben sind in Ordnung, bei regelmäßiger automatischer Löschung (dass die Löschung Bedingung für die Speicherung im Profil ist, ist eine vorsichtige Auslegung der KI). In der Anmeldung speichert ein Knopf „Für künftige Anmeldungen speichern“ die Angaben im eigenen Profil, wo sie bearbeitet werden können. Die Löschfrist ist offen und wird beim Klären festgelegt.
- **Verträge zur Auftragsverarbeitung** (u. a. Microsoft Azure, Google Workspace) liegen vor; Google Workspace soll laut Datenschutzperson DSGVO-konform sein.
- **Impressum und Datenschutzerklärung:** Das Tool bekommt eigene Seiten (#12); verantwortlich ist der DPV.

**Noch offen** (nicht beantwortet oder ausdrücklich offen): ob eine Datenschutz-Folgenabschätzung nötig ist; ab welchem Alter Personen mit Account selbst einwilligen können; ob die Einwilligung nach Volljährigkeit fortgilt (DSG-02, bleibt Annahme); Verzeichnis der Verarbeitungen und Ablauf bei Datenpannen; ob das Fehlerprotokoll einen Bezug zum Konto braucht (#11, bis dahin bleibt es ohne); ob für Entwicklung und Betrieb des Tools ein eigener Vertrag mit dem DPV nötig ist (gefragt war nur nach den Verträgen mit Azure und Google). Der Vorbehalt bei FRM-04 bleibt deshalb: Die Speicherung im Profil wird in P4 zuletzt gebaut und nur mit Freigabe aus OP-2. Fristen und Folgen der OP-Tabelle bleiben unverändert.

**Neue Wünsche,** vorgemerkt ohne Phase: Fahrtkosten- und Auslagenerstattung (#82), Anbindung an Google Sheets für Kostenübersichten (#83), Kennwort für Gäste je Veranstaltung (#84).

**Begründung:** Die Antworten bestätigen die Arbeitsannahme vom 20.10.2026 zur stellvertretenden Bestätigung. Hinweise der KI: Einige Antworten lassen die Frage offen, etwa ob eine Folgenabschätzung entfällt; sie werden deshalb nicht als geklärt eingetragen, sondern bleiben unter OP-2 offen. Gesundheitsdaten von Kindern gehören zu den besonders geschützten Daten; ob dafür eine Folgenabschätzung Pflicht ist, entscheidet die Datenschutzperson, nicht die KI.

**Umsetzung:** `docs/anforderungen.md` (FRM-04, Abschnitt Datenschutz, DSG-01, DSG-02, OP-2) und `docs/fahrplan.md` (OP-Tabelle bei OP-2, Abschnitt 6 Nr. 45), mit Zustimmung von Sebastian am 22.10.2026; Kommentare in #11, #12 und #44; neue vorgemerkte Issues #82, #83 und #84.

---

## 2026-10-22 · Login auf dem Testserver wandert von P1 nach P2

**Entscheidung** (Sebastian, 22.10.2026; #71): Das Abschlusskriterium „Login nur per Keycloak … auf dem Testserver“ gehört jetzt zu P2, zusammen mit #59 (Testumgebung auf dem Server) und #63 (Login dort nachweisen). P1 verlangt nur noch den Login lokal. Die Folgen bei OP-1 (Test-Client) und OP-4 (Testserver) in der OP-Tabelle nennen P2; die Fristen der Anfragen bleiben. Die Empfehlung der KI war das Verschieben; die Alternative war, auf den Admin zu warten.

**Begründung:** Der Code von P1 ist fertig. Der Server-Teil bringt vor allem Einrichtung auf dem Server, eine Anleitung und eine Checkliste von Hand und wartet auf Auskünfte des Admins, der im Urlaub ist. So kann das externe Review zu P1 jetzt auf dem fertigen Stand laufen, und P2 beginnt danach. Das Review zu P2 prüft den Server-Teil mit. Ändert der Server doch Code, etwa für HTTPS hinter einem vorgeschalteten Programm, landet das in P2. An E3 ändert sich nichts: Dort müssen ohnehin alle Abschlusskriterien von P1 bis P6 erfüllt sein. Die Stunden der Phasen bleiben, der Aufwand des Server-Teils ist gering (Annahme). Antwortet der Admin sehr spät, zählt die Wartezeit jetzt gegen P2 und damit gegen E1; die OP-Fristen (31.01. und 28.02.2027) liegen aber vor dem Zieldatum von P2.

**Umsetzung:** `docs/fahrplan.md` (Phasen P1 und P2, OP-Tabelle, kritischer Pfad, Abschnitt 6 Nr. 44); Labels und Texte von #37, #38, #59, #63; #57.

## 2026-10-22 · Kein Stundenlog, E1 misst Termine statt Stunden

**Entscheidung** (Sebastian, 22.10.2026; #68):

1. **Kein Stundenlog.** Sebastian führt keins; er ist dem Zeitplan weit voraus. Damit entfallen das Stundenlog aus dem Eintrag „Neustart, Name, Lizenz, Umfang und Technik“ vom 20.10.2026, die getrennt notierte Lernzeit aus „Entscheidungen nach der Prüfung der Rückmeldungen“ vom 20.10.2026, „Stundenlog führen“ aus „P1 beginnt früher, Restpunkte von P0 laufen parallel“ vom 21.10.2026 und der Eintrag der Review-Zeit aus „Externes KI-Review am Ende jeder Phase“ vom 21.10.2026.
2. **E1 misst Termine statt Stunden:** weiter, wenn P2 mit höchstens 4 Wochen Verzug fertig ist; bei 4 bis 8 Wochen Liste 2 und die Zieldaten der folgenden Phasen um den Verzug neu rechnen; bei mehr Verzug mit dem DPV-Veranstaltungsteam ein späteres Vorbereitungstreffen als Generalprobe festlegen. Die übrigen Bedingungen von E1 bleiben. E2 misst schon so.
3. **Risikotabelle:** „Zu wenig Zeit“ zeigt sich daran, dass eine Phase an ihrem Zieldatum nicht fertig ist; „Schätzung zu niedrig“ daran, dass P2 mehr als 4 Wochen nach ihrem Zieldatum fertig ist.

Die Empfehlung der KI war „Termine statt Stunden“; die anderen Möglichkeiten waren eine grobe Schätzung am Prüfpunkt oder keine Prüfung des Tempos mehr.

**Begründung:** Eine Messgröße, die nicht gepflegt wird, macht die Prüfpunkte wertlos. Termine stehen ohnehin fest. P2 dauert rund 17 Wochen (28.02. bis 30.06.2027); 4 Wochen Verzug entsprechen etwa 125 %, 8 Wochen etwa 150 % der Phasendauer. Das ist etwas großzügiger als die bisherige Schwelle von 125 % der geschätzten Stunden, die bei rund 7,5 Stunden je Woche schon nach rund 2 Wochen Verzug erreicht gewesen wäre. Die Schätzungen in Stunden bleiben als Planungsgrundlage (Annahme) stehen, werden aber nicht mehr nachgemessen. Punkt 1 aus „Offene Punkte aus der Bestandsaufnahme“ vom 20.10.2026 („Die Stundenschwelle an E1 wird nicht weiter geklärt“) ist damit gegenstandslos.

**Nicht geändert:** E4 („Betriebsaufwand pro Woche gemessen“) betrifft den Betrieb ab 2028 und wird vor E4 neu angesehen.

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, Machbarkeit, Phasen, E1, Risikotabelle, Abschnitt 6 Nr. 43), `docs/review-leitfaden.md`; in #57 ist „Stundenlog läuft“ als entfallen markiert.

## 2026-10-22 · Test-Realm im Keycloak des DPV: Konten, Passwörter, Nachweis

**Entscheidung** (Sebastian, Klärung von #38 am 22.10.2026; Protokoll in #38):

1. **Selbstregistrierung aus** im Test-Realm `dpv-test`. Konten entstehen nur, wenn Sebastian oder der Admin sie anlegen.
2. **Passwörter nicht im Repo:** Die Importdatei enthält die Konten ohne Passwort. Nach dem Import setzt Sebastian jedem Konto ein eigenes, langes Passwort und bewahrt es in seinem Passwortmanager auf. Lokal bleiben die erfundenen Passwörter im Repo, weil die Keycloak-Testumgebung nur auf dem eigenen Rechner läuft.
3. **Vier erfundene Konten:** `erika.testfrau`, `max.testmann`, `ohne.name`, `ohne.nachname`, Mails auf `@example.org`. Ein Konto ohne Mail gibt es im echten Realm nicht; seine Ablehnung prüft weiter die lokale Testumgebung.
4. **Weitere Personen** (Prüfer, Planungsteam) bekommen je ein eigenes erfundenes Konto ohne echten Namen und echte Mail. Sebastian legt es an und löscht es wieder.
5. **Keine Kennzeichnung** der Login-Seite von Keycloak (Empfehlung der KI war eine Überschrift „DPV Testumgebung – nur erfundene Konten“). Der Realm bekommt keinen Anzeigenamen; Keycloak zeigt deshalb „dpv-test“.
6. **Nachweis** des Logins auf dem Server per Checkliste von Hand (#63).
7. **Abweichende Keycloak-Fassung:** Weicht die Fassung des DPV von 26.7.5 ab, werden die lokale Testumgebung und die Prüfung auf GitHub in einem eigenen Issue angeglichen.

**Technische Wahl** (KI):

- **Importdatei** `testumgebung/keycloak/dpv-test-realm.json`, angelegt über „Realm erstellen“ mit hochgeladener Datei. Kein Passwort und kein Client-Secret darin; das Secret erzeugt Keycloak beim Import. Ein Test schlägt fehl, sobald eines hineinkommt.
- **Kein Mailserver und kein „Passwort vergessen“**, damit Keycloak aus dem Test-Realm nie Mails verschickt.
- **Schutz gegen Passwortraten:** Nach 10 Fehlversuchen (oder sehr schnellen Wiederholungen) sperrt Keycloak das Konto vorübergehend, höchstens 15 Minuten, nie dauerhaft. Die Login-Seite ist offen erreichbar.
- **Name und Mail ändert nur der Admin**, nicht die Person über die Kontoverwaltung von Keycloak. Sonst könnte jemand mit einem Testkonto seine echten Angaben eintragen (DSG-08). Gleiche Begründung wie bei der Selbstregistrierung.
- **Login-Client wie lokal:** vertraulich, Login nur über die Login-Seite von Keycloak mit PKCE, kein Login mit Passwort direkt aus dem Tool, kein Service-Konto, keine Rollen. Rücksprung und Abmelden nur zur Testdomain; bis sie feststeht, steht dort `https://testdomain-eintragen.invalid`. Die Endung `.invalid` gibt es im Internet nicht.
- **HTTPS Pflicht** (`sslRequired: external`), außer bei Aufrufen vom eigenen Rechner.
- **Prüfung gegen echtes Keycloak 26.7.5:** Die Tests importieren die Datei mit dem Admin-Zugang der lokalen Keycloak-Testumgebung (erfundener Wert, auf GitHub `KEYCLOAK_DEV_ADMIN_PASSWORD`), setzen Passwörter und melden sich im Tool an. Das Tool selbst bekommt nie einen Admin-Zugang.

**Begründung:** Zu 1 bis 7: Protokoll in #38. Die Testumgebung ist offen erreichbar (Entscheidung vom 22.10.2026 zu #37); vor E3 dürfen keine echten Daten hinein, und wer das Repo sieht, soll nicht hineinkommen.

**Umsetzung:** `testumgebung/keycloak/dpv-test-realm.json`, `README.md` (Abschnitt „Test-Realm im Keycloak des DPV“), `.github/workflows/ci.yml`, Tests in `tests/test_testrealm_datei.py` und `tests/test_testrealm_echt.py`.

## 2026-10-22 · Testumgebung im Container: Schutz, Kennzeichnung, Datenbank, Mails, Aktualisieren

**Entscheidung** (Sebastian, Klärung von #37 am 22.10.2026; Protokoll in #37):

1. **Schutz:** Die Testumgebung ist offen erreichbar wie später das echte Tool, ohne Vorschaltpasswort. Suchmaschinen werden gebeten, nichts aufzunehmen. Hineinkommen kann nur, wer ein Konto im Test-Realm hat (#38). Die Empfehlung der KI war ein Vorschaltpasswort.
2. **Kennzeichnung:** Auf jeder Seite der Testumgebung steht oben ein Band mit Symbol und dem Text „Testumgebung: Hier gibt es nur erfundene Daten. Bitte gib keine echten Angaben ein.“ Es erscheint nur mit dem Schalter `TEST_ENVIRONMENT=1`, nie im späteren Betrieb.
3. **Datenbank:** Die Testumgebung bringt einen eigenen Datenbank-Container mit PostgreSQL 18 mit, ohne Zugriff auf das PostgreSQL des Servers.
4. **Mails** gehen in der Testumgebung nur als Hinweis ins Log, ohne Empfänger und Inhalt. Der Mailtest aus P5 kommt in #60.
5. **Aktualisieren:** Sebastian selbst, der Admin als Vertretung; bei Bedarf, sicher vor jedem externen Review und vor den Prüfpunkten. Nichts wird automatisch von GitHub auf den Server gespielt.
6. **Aufteilung:** #37 in #58 (Abbild und Testumgebung lokal) und #59 (auf dem Server).

**Technische Wahl** (KI):

- **gunicorn 26.2.0** (MIT, mit der EUPL-1.2 verträglich; Fassung vom 24.08.2026, gepflegt vom Projekt gunicorn.org, keine weiteren Pakete) als Webserver im Container. Djangos eigener Server ist nur für die Entwicklung gedacht. Gewählt statt uvicorn oder waitress, weil das Tool synchron arbeitet (WSGI) und gunicorn dafür der verbreitetste Weg ist. Ohne Zugriffsprotokoll: Es enthielte jede echte Adresse mit Parametern (Entscheidung zu #6); ob der Betrieb eins braucht, klärt #11.
- **Abbild:** `python:3.13-slim` mit uv 0.13.4 wie in der Prüfung auf GitHub, Pakete fest aus `uv.lock` ohne die Pakete zum Prüfen, das Tool läuft nicht als Verwalter. Die Grundabbilder sind über ihre Fassung festgelegt, nicht über eine Prüfsumme; die ließ sich aus der Arbeitsumgebung nicht nachsehen (Docker Hub gesperrt).
- **Mails über `MAILERS`:** Seit Django 6.1 ersetzt `MAILERS` die Einstellung `EMAIL_BACKEND`, die bis Django 2028 wegfällt. Der einzige Mailweg ist `core.mail.LogOnlyEmailBackend`, auch in der Entwicklung, bis P5 den Versand bringt.
- **HTTPS nur mit Schalter** (`DJANGO_BEHIND_HTTPS_PROXY=1`): Dann vertraut das Tool dem Hinweis `X-Forwarded-Proto` des Programms davor, und Sitzungs- und Formular-Cookies gehen nur über HTTPS. Ohne Schalter könnte jede Anfrage den Hinweis selbst mitschicken.
- **Keycloak aus dem Container** (`KEYCLOAK_REALM_URL_INTERN`): Auf dem eigenen Rechner erreicht das Tool im Container die Keycloak-Testumgebung unter `keycloak:8080`, der Browser unter `localhost:8081`. Keycloak nennt dem Browser deshalb immer `localhost:8081` (`--hostname`, `--hostname-backchannel-dynamic`). Auf dem Server ist beides dieselbe Adresse.
- **Prüfung im Container:** `pruefen.sh` baut und startet die Testumgebung unter eigenem Namen (`containertests/`), meldet sich wirklich an und räumt danach ab; eine eigene Testumgebung auf dem Mac bleibt unberührt.
- **Rote Prüfungen auf GitHub lesbar:** `pruefen.sh` schreibt auf GitHub je rote Prüfung einen Fehler-Hinweis und die roten Tests als Warnungen an den Prüflauf. Das volle Protokoll ist aus der Arbeitsumgebung der KI nicht lesbar (Azure-Speicher gesperrt), diese Hinweise schon.

**Begründung:** Zu 1 bis 6: Protokoll in #37. Die Testumgebung läuft so lokal genau so, wie sie später auf dem Server läuft, und lässt sich prüfen, bevor der Admin die Testdomain eingerichtet hat.

**Umsetzung:** `Dockerfile`, `.dockerignore`, `docker/start.sh`, `testumgebung/`, `config/settings.py`, `core/mail.py`, `core/testumgebung.py`, `core/templatetags/layout.py`, `core/templates/` (Band, Symbol, Musterseite), `core/static/core/app.css`, `pyproject.toml`, `uv.lock`, `pruefen.sh`, `.github/workflows/ci.yml`, `ruff.toml`, `README.md`, Tests in `tests/test_testumgebung.py`, `tests/test_testumgebung_aufbau.py` und `containertests/`.

## 2026-10-21 · Antwort des DPV-Admins: Test-Realm, Testumgebung auf dem Produktivserver, eigene Admin-Konten

**Auskünfte** des Admins des DPV vom 21.10.2026, von Sebastian weitergegeben:

- Er kann einen Keycloak-Client anlegen oder Sebastian zum Admin machen, und er kann eine Testdomain anlegen. Der Keycloak des DPV läuft in der aktuellsten Fassung.
- Ob ein Konto gelöscht oder gesperrt ist, merkt das Tool wahrscheinlich daran, dass der Login bei Keycloak scheitert. Eine Meldung dafür kennt er nicht.
- Keycloak erhebt kein Alter.
- Einen Testserver gibt es nicht mehr. Der Produktivserver läuft mit Docker Compose bei Azure und kann beliebige Container betreiben; PostgreSQL läuft dort schon.
- Mails gehen über das SMTP-Relay von Google Workspace; der Produktivserver ist dafür freigeschaltet.
- Er ist die Ansprechperson für den Betrieb (OP-4).

**Entscheidung** (Sebastian, 21.10.2026):

1. **Eigener Test-Realm:** Der Test-Client kommt in einen eigenen Realm des DPV-Keycloak mit erfundenen Konten, nicht in den Realm der Mitglieder. Ein Realm ist ein abgeschlossener Bereich in Keycloak mit eigenen Konten.
2. **Keycloak-Fassung:** Sebastian nimmt an, dass der DPV dieselbe Fassung nutzt wie die Keycloak-Testumgebung (26.7.5), weil er sie aus aktiven Repos des DPV übernommen hat (Annahme). „Die aktuellste“ kann auch neuer sein als 26.7.5. Die genaue Fassung sieht Sebastian mit seinem Admin-Konto nach; dass das Tool mit ihr läuft, zeigt der Login über den Test-Client (#38).
3. **Testumgebung auf dem Produktivserver:** Sie läuft als eigener Container auf dem Produktivserver des DPV, mit eigener Datenbank, eigenem Datenbank-Zugang, der Testdomain und nur erfundenen Daten. Gewählt gegen einen eigenen, kostenpflichtigen Server. Die Einzelheiten klärt #37.
4. **Eigene Admin-Konten für Sebastian:** Sebastian lässt sich vom Admin ein Admin-Konto für Keycloak geben, voraussichtlich auch für Azure und weitere Dienste, um Fragen selbst nachsehen zu können. Mit diesen Konten meldet er sich nie im Tool an.

**Was unverändert gilt** (`CLAUDE.md`, `docs/fahrplan.md`): Das Tool bekommt im Keycloak des DPV keine Admin-Rechte und kein Service-Konto und schreibt nicht in Keycloak; ORG-04 Variante A nur, wenn OP-1 es erlaubt. Die KI ändert nichts am Produktivserver.

**Folge daraus** (Vorschlag der KI, Sebastian stimmt mit dem Übernehmen des Pull Requests zu): Die KI bekommt keinen von Sebastians Admin-Zugängen. Einrichtung und Aktualisierung der Testumgebung auf dem Produktivserver machen Sebastian oder der Admin nach einer Anleitung, die ohne KI funktioniert (#37).

**Begründung:** Zu 1: Im Realm der Mitglieder meldeten sich echte Personen auf dem Testserver an, und ihre echten Namen und Mails kämen ins Tool; vor E3 gibt es keine echten Personendaten (DSG-08, `docs/fahrplan.md`). Zu 3: Der Server ist schon da und kostet nichts; die Testumgebung läuft dort so wie später das Tool. Die eigene Datenbank mit eigenem Zugang hält die erfundenen Testdaten von allen echten Daten auf dem Server getrennt (Empfehlung der KI). Zu 4: Sebastian kann Fragen zu Keycloak und Server selbst nachsehen, statt jedes Mal den Admin zu fragen.

**Hinweise der KI:**

- Mit den Admin-Konten sieht Sebastian echte Daten aller Mitglieder. Auszüge daraus, auch Bildschirmfotos oder Logzeilen, gehören nie in KI-Werkzeuge (DSG-08). Für die Admin-Konten empfiehlt sich eine Anmeldung mit zweitem Faktor.
- Damit vor E3 keine echten Daten in die Testumgebung kommen, gehören drei Punkte in die Klärung von #37 und #38: Im Test-Realm ist die Selbstregistrierung aus, sonst könnten sich echte Personen mit echtem Namen und echter Mail registrieren. Die Testumgebung schickt keine Mails über das echte SMTP-Relay an echte Adressen. Sie ist von den übrigen Containern getrennt: eigenes Netz, eigene Zugangsdaten, keine gemeinsamen Ablagen.
- Gesperrte oder gelöschte Konten: Wer im Tool schon angemeldet ist, bleibt es, bis 2 Stunden lang kein Klick kam oder die Person sich abmeldet (Entscheidung zu #5). Ob das reicht, klärt #8.
- Keycloak kennt kein Alter. Der Satz in `docs/anforderungen.md` (Abgrenzung), die Altersprüfung sei Aufgabe von Keycloak, stimmte damit nicht mehr. Ob und wie das Alter für die Einwilligung von Personen mit Account zählt, ist eine Rechtsfrage für OP-2.

**Noch offen:** die Fragen an die Datenschutzperson (OP-2), die Sebastian später klärt; beim Admin die Fassung von PostgreSQL, die Region bei Azure (sie gehört in die Auftragsverarbeitung, OP-2), Backups, Absenderkonto, Tageslimit des SMTP-Relays, SPF und DKIM.

**Umsetzung:** `docs/fahrplan.md` (OP-Tabelle bei OP-1, OP-2 und OP-4; Abschnitt 6, Nr. 41 und 42) und `docs/anforderungen.md` (Abgrenzung; Offene Punkte OP-1 und OP-4), Vorschläge der KI, denen Sebastian mit dem Übernehmen des Pull Requests zustimmt. Kommentare in #37, #38 und #8.

## 2026-10-21 · Externes KI-Review am Ende jeder Phase

**Entscheidung** (Sebastian, Klärung von #26 am 21.10.2026; Protokoll in #26):

1. **Einordnung:** #26 kommt aus dem Puffer von P1 und verdrängt nichts. Die Zeit für jedes Review steht im Stundenlog.
2. **Zeitpunkt:** Am Ende jeder Phase P1 bis P10, sobald die Abschlusskriterien erfüllt scheinen, prüfen zwei externe KI-Modelle den Stand; P0 bekommt kein Review. Eine Phase gilt erst als abgeschlossen, wenn das Review-Issue eingeordnet ist und alle blockierenden Befunde behoben sind. Erst dann wechselt der „Stand“ im `README.md`.
3. **Umfang:** der ganze Stand zum geprüften Commit, Code, Tests und Doku, mit Schwerpunkt auf dem Neuen der Phase. Jedes Abschlusskriterium wird als erfüllt, nicht erfüllt oder nicht prüfbar bewertet. Widersprüche melden die Modelle, sie lösen sie nie auf.
4. **Modelle:** A mit breitem Blick, B mit Schwerpunkt Sicherheit, Rechte und Datenschutz; B sieht den Bericht von A erst nach der eigenen Prüfung. Pilot nach P1: A = ChatGPT, B = Gemini. Kein Anbieter ist vorgeschrieben. Ein drittes Modell nur bei einem strittigen, möglicherweise blockierenden Befund und immer nach P6 (vor Tor E3).
5. **Zugang:** je Review eine ZIP-Datei genau des geprüften Commits, die Sebastian hochlädt. Kein dauerhafter Zugriff externer Dienste auf das Repo. Externe Modelle bekommen nur den Inhalt des Repos und erfundene Daten (DSG-08).
6. **Zusammenführung:** Eine eigene Claude-Sitzung prüft jeden Befund nach (Beleg oder Annahme), bündelt Doppelte und schlägt die Einordnung vor. Sie schreibt nur ins Review-Issue; Befund-Issues legt sie erst nach Sebastians Entscheidung an.
7. **Stufen:** blockierend, zeitnah, später, Fehlalarm oder Duplikat, akzeptiertes Risiko. Blockierende Befunde sind vor Abschluss der Phase behoben, nicht nur entschieden. Bei Sicherheit und Datenschutz gibt es kein akzeptiertes Risiko; ein Härtungshinweis ohne konkrete Lücke darf auf „später“, ist aber vor E3 erledigt.
8. **Ablage:** ein Review-Issue je Phase. Die Rohberichte stehen unverändert als eingeklappte Kommentare darin, die eingeordneten Befunde im Text. Ins Repo kommen nur Entscheidungen.
9. **Auswertung** nach dem Review zu P2, zusammen mit E1 (#35).
10. **Fahrplan:** Phasenende und Stundenrechnung angepasst (`docs/fahrplan.md`, Abschnitt 6, Nr. 40), mit Sebastians Zustimmung.

**Technische Wahl** (KI):

- **Labels statt Issue-Typ:** GitHub bietet eigene Issue-Typen nur für Organisationen an; `sebivtt` ist ein persönliches Konto, und die Schnittstelle liefert für das Repo keine Typen (geprüft am 21.10.2026). Deshalb die Labels `externes-review` (Review-Issue einer Phase) und `review-befund` (Einzelbefund) mit je einer Vorlage in `.github/ISSUE_TEMPLATE/`.
- **ZIP-Datei mit `git archive`:** Sie enthält nur Dateien aus dem Repo, nie `.env`. `.gitattributes` hält die fremden Bibliotheken Bootstrap und axe-core heraus.
- **PyYAML 6.0.3** (MIT, mit der EUPL-1.2 verträglich; Fassung vom 25.09.2025, gepflegt vom YAML-Projekt pyyaml.org), nur zum Prüfen: Der Test liest damit die Issue-Vorlagen. Eine fehlerhafte Vorlage zeigt GitHub ohne Fehlermeldung nicht an; ein eigener Leser für das YAML-Format wäre fehleranfälliger als das verbreitete, gepflegte Paket.

**Begründung:** Die Prüfung vor jedem Pull Request sieht nur den Diff, die Prüfung vom 20.10.2026 war einmalig. Fehler im Zusammenspiel, nur scheinbar erfüllte Abschlusskriterien und widersprüchliche Anforderungen fallen so leicht durch. Zwei Modelle mit verschiedenem Schwerpunkt sehen mehr als eines; die Nachprüfung verhindert, dass Vermutungen als Fehler gelten (am 20.10.2026 waren mehrere Anmerkungen falsch oder unbelegt, z. B. G4 und G7). Claude prüft nicht als A oder B, weil Claude den Code schreibt. Blockierende Befunde müssen behoben sein, weil die nächste Phase sonst auf einem fehlerhaften Stand aufbaut; bei Sicherheit und Datenschutz wird laut Fahrplan nie gekürzt.

**Umsetzung:** `docs/review-leitfaden.md`, `.github/ISSUE_TEMPLATE/externes-review.yml`, `.github/ISSUE_TEMPLATE/review-befund.yml`, `.gitattributes`, `docs/fahrplan.md` (Machbarkeit, Phasen, Abschnitt 6 Nr. 40), `CLAUDE.md`, `README.md`, `.claude/skills/issue-anlegen/SKILL.md`, `pyproject.toml`, `uv.lock`, Labels auf GitHub, Tests in `tests/test_issue_vorlagen.py`.

## 2026-10-21 · Grundgestaltung: Bootstrap, Farben, Aufbau, Sprache und Prüfung im Browser

**Entscheidung** (Sebastian, Klärung von #7 am 20.10.2026 und drei Nachklärungen am 21.10.2026; Protokolle in #7):

1. **CSS-Grundlage: Bootstrap** (5.3.8). Sebastian hat beide Varianten der Musterseite, Bootstrap und Pico.css, am Handy und am PC verglichen. Pico.css kommt nicht ins Repo.
2. **Farbpalette:** DPV-Blau `#1a4b7e` trägt die Gestaltung, dazu Weiß und kühle Grautöne. Eine Akzentfarbe, Sonnengelb `#f0ad2c`, sparsam eingesetzt (gewählt gegen Terrakotta); Sonnengelb trägt nie Text auf Weiß. Statusfarben sind gedeckt und stehen immer mit Wort und Symbol. Alle Farben stehen in `core/static/core/app.css`; vorerst nur heller Modus, dunkler vorbereitet (#15). Schrift: die Systemschrift des Geräts (gewählt gegen Nunito Sans).
3. **Aufbau:** am PC eine feste Seitenleiste links ohne Kopfzeile über dem Inhalt; am Handy eine schmale Leiste mit „Menü“, Lilie und Profilkreis, „Abmelden“ im Menü mit Symbol und Wort. Login- und Fehlerseite ohne Seitenleiste. Fußbereich als flache Zeile: Impressum und Datenschutz links, Copyright rechts.
4. **Regel für Navigationspunkte:** Die Navigation zeigt nur, was es gibt, und nur Personen, die es nutzen dürfen. Keine leeren Platzhalter und keine Seiten „im Aufbau“. Ausblenden ersetzt nie die Rechteprüfung auf dem Server.
5. **Regel für Menüs:** Menüs öffnen am PC beim Darüberfahren und zusätzlich per Klick, Antippen und Tastatur; sie schließen mit kurzer Verzögerung. Gilt für alle späteren Menüs.
6. **Regel für gendersensible Sprache** (NFA-09): neutrale Wörter („Teilnehmende“, „Leitung“, „Person“); wo es keine gibt, beide Formen ausschreiben oder umformulieren. Kein Sternchen, kein Doppelpunkt. Die Texte duzen.
7. **Unterstützte Browser:** die gängigen der letzten rund zwei Jahre: Safari auf iPhone und Mac, Chrome und Samsung Internet auf Android, Chrome, Firefox und Edge am PC. Ältere nur bei Bedarf (#17).
8. **Logo:** Die Lilie liegt im Repo mit dem Hinweis „Das Logo ist Eigentum des DPV und nicht Teil der EUPL-Lizenz.“ im `README.md` und in `core/templates/core/LOGO-HINWEIS.md`.
9. **Leitlinie:** Sebastians Gestaltungskonzept vom 21.10.2026 steht in `docs/gestaltung.md`, zusammen mit dem, was bei #7 konkret festgelegt wurde. Spätere Seiten bauen danach.

**Technische Wahl** (KI):

- **Gestaltung vom eigenen Server mit WhiteNoise 6.12** (MIT). Ohne ein solches Paket liefert Django CSS und Skripte nur bei eingeschalteter Fehleranzeige für Entwickler aus, und die ist bewusst aus (Entscheidung zu #4). WhiteNoise liest die Dateien direkt aus `core/static/` (`WHITENOISE_USE_FINDERS`), ein Einsammeln mit `collectstatic` ist bis P6 nicht nötig. Gestaltung und Skript sind ohne Login abrufbar, weil die Login-Seite sie braucht; sie enthalten keine Daten.
- **Bootstrap ohne sein Skript:** Nur die CSS-Datei, unverändert aus dem offiziellen Paket (`npm` bootstrap 5.3.8), mit Lizenz in `core/static/core/bootstrap/`. Das Handy-Menü ist ein `dialog`-Element des Browsers mit wenigen Zeilen eigenem Skript (`core/static/core/app.js`); es hält den Fokus im Menü und schließt mit Escape.
- **Symbole:** eigene, einfache Zeichnungen in `core/templates/core/_symbole.svg` (EUPL wie das Tool), kein fremdes Symbolpaket.
- **Fachbegriffe im Code** (CONTRIBUTING.md, Abschnitt 1): Veranstaltung = `event`, Teilnehmende = `participant`. Bisher nur in den Beispieldaten der Musterseite.
- **Rauchtest mit Playwright 1.64** (Apache-2.0) in Python, nur zum Prüfen. Playwright bringt greenlet (MIT und PSF-2.0), pyee (MIT) und typing-extensions (PSF-2.0) mit. Ohne `pytest-playwright`, das zwei weitere Pakete mitbrächte; die wenigen Helfer stehen in `rauchtests/conftest.py`. Der Rauchtest läuft in Chromium, Firefox und WebKit, meldet sich wirklich bei der Keycloak-Testumgebung an und braucht dafür Port 8000. Er läuft in einem eigenen pytest-Lauf in `pruefen.sh`, weil Playwright eine Ereignisschleife betreibt, neben der Django Datenbankzugriffe abbricht; nur dort ist `DJANGO_ALLOW_ASYNC_UNSAFE` gesetzt.
- **axe-core 4.14.0** (MPL-2.0, mit der EUPL verträglich) für die Prüfung auf Barrierefreiheit liegt als Datei in `tests/vendor/axe-core/`, mit Lizenz; Prüfsumme gegen die von axe-core veröffentlichte geprüft. Gewählt statt des Python-Pakets `axe-playwright-python`, für das PyPI keine Lizenz nennt. Geprüft wird nach WCAG 2.2 A und AA.
- **Firefox auf dem Mac:** Firefox von Playwright startet unter macOS 27.0.1 nicht („Could not find profile folder“, auf Sebastians Mac auch im eigenen Terminal belegt). Der Rauchtest überspringt Firefox nur genau dann, sichtbar im Ergebnis; auf GitHub läuft Firefox immer mit.
- **WebKit auf dem Mac:** Ohne die Mac-Einstellung „Tastaturnavigation“ springt WebKit wie Safari mit Tab nur zwischen Eingabefeldern; der Tastatur-Rauchtest nutzt dort Wahltaste und Tab.

**Begründung:** Zu 1 bis 9: Protokolle in #7. Zu Bootstrap: laut Sebastian „sieht wesentlich ordentlicher aus“. Zur Technik: Gestaltung ohne Build-Schritt und vom eigenen Server (Entscheidung vom 20.10.2026, CONTRIBUTING.md, Abschnitt 6); jedes Paket weniger ist ein Paket weniger zu pflegen.

**Umsetzung:** `core/templates/base.html`, `base_app.html`, `base_einfach.html`, `core/templates/core/` (Musterseite, Bausteine, Lilie, Symbole), `core/static/core/`, `core/navigation.py`, `core/templatetags/layout.py`, `core/views.py`, `config/settings.py`, `config/urls.py`, `accounts/templates/accounts/login.html`, `core/templates/500.html`, `docs/gestaltung.md`, `README.md`, `pruefen.sh`, `.github/workflows/ci.yml`, Tests in `tests/test_gestaltung.py`, `tests/test_texte.py` und `rauchtests/`.

## 2026-10-21 · Login über Keycloak: Abmelden, Sitzung, Anrede und Technik

**Entscheidung** (Sebastian, Klärung von #5 am 20.10.2026 und Nachklärung am 21.10.2026):

1. **Vollständiges Abmelden:** „Abmelden“ beendet die Sitzung im Tool und bei Keycloak. Wer danach am selben Gerät „Anmelden“ klickt, muss das Passwort eingeben. Andere Dienste am selben Keycloak sind dann ebenfalls abgemeldet (Annahme).
2. **Sitzungsdauer:** Nach 2 Stunden ohne Aktivität endet die Sitzung im Tool; jeder Klick verlängert sie. Die Dauer steht an einer Stelle (`SESSION_IDLE_MINUTES` in `config/settings.py`).
3. **Anrede:** Alle Texte des Tools duzen, wie das Anforderungsdokument.
4. **Gleiche Mail, neue Kennung:** Meldet sich jemand mit einer neuen Keycloak-Kennung (`sub`), aber derselben Mail wie ein bestehendes Konto an, legt das Tool ein neues, leeres Konto an. Zwei Konten mit derselben Mail sind damit möglich; der Umgang damit gehört zu #8.

**Technische Wahl** (KI):

- **django-allauth 65.20.1** mit der Anbindung für OpenID Connect ist der Login-Baustein. Es läuft mit Keycloak 26.7.5; das belegen Tests, die sich wirklich an der Keycloak-Testumgebung anmelden, registrieren und abmelden. Der Rückfall auf Django 5.2 mit mozilla-django-oidc (20.10.2026) ist nicht nötig.
- **Eigenes Kontenmodell:** App `accounts`, Modell `User` (Djangos Bezeichnung), im Text „Konto“. Verknüpft wird nur über die Keycloak-Kennung, die allauth als `SocialAccount.uid` speichert.
- **Login-Pflicht für jede Adresse** über Djangos `LoginRequiredMiddleware`. Öffentlich sind nur die Login-Seite, Start und Rückkehr des Logins bei Keycloak und das Abmelden; die Liste steht mit Begründung in `tests/test_rundumtest.py`. Das Abmelden ist öffentlich, damit es auch nach abgelaufener Sitzung bei Keycloak gelingt; es geht nur per Formular mit Formularschutz.
- **Keine Anmeldung mit Passwort im Tool:** Die Adressen von allauth sind nicht eingebunden, nur Start und Rückkehr des Logins; dazu `SOCIALACCOUNT_ONLY`. Konten werden nie über die Mail gefunden oder verknüpft.
- **Abmelden ohne Rückfrage bei Keycloak:** Das Tool hebt das Kennungs-Token von Keycloak in der Sitzung auf und schickt es beim Abmelden mit. Ohne das fragt Keycloak „Möchtest du dich wirklich abmelden?“.
- **Hinweis „Sitzung abgelaufen“:** Ein Cookie `dpv_war_angemeldet` mit dem Wert `1`, ohne Bezug zur Person, überdauert die Sitzung bis zu 30 Tage. Ist es da und die Sitzung weg, zeigt die Login-Seite den Hinweis und löscht das Cookie; beim Abmelden wird es ebenfalls gelöscht.
- **Keycloak-Angaben** (`KEYCLOAK_REALM_URL`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`) prüft eine Systemprüfung beim Start (`runserver`, `migrate`, `check`), nicht das Laden der Einstellungen, damit sich diese auch ohne Keycloak laden lassen.
- **Keycloak-Testumgebung:** Keycloak 26.7.5 in `dev/docker-compose.yml` mit eingebauter Entwicklungsdatenbank, Realm, Login-Client und erfundenen Konten aus `dev/keycloak/dpv-realm.json`. Die Reihe 26.7 nutzte der DPV laut altem Repo im Juli 2026. Auf GitHub startet dieselbe Umgebung in einem eigenen Schritt.

**Begründung:** Zu 1 bis 3: Protokoll der Klärung in #5. Vollständiges Abmelden wegen gemeinsam genutzter Geräte und späterer Gesundheitsdaten. Zu 4: Niemand wird ausgesperrt, und ins bestehende Konto kommt die Person trotzdem nie (Frage beim Umsetzen, Protokoll in #5). Zur Technik: Ein eigenes Kontenmodell empfiehlt Django zu Projektbeginn, weil ein späterer Wechsel aufwendig ist; mit #5 entstehen die ersten Konten. Die Login-Pflicht als Grundeinstellung schützt auch Adressen, bei denen jemand den Schutz vergisst. Die Keycloak-Testumgebung entsteht so bei jedem Start gleich, auch bei einer schon bestehenden Datenbank; das 7 KB große Einrichtungsskript des alten Repos entfällt.

**Umsetzung:** `accounts/` (Modell, Anpassungen an allauth, Seiten, Hinweise), `config/settings.py`, `config/urls.py`, `core/views.py`, `core/templates/core/start.html`, `dev/docker-compose.yml`, `dev/keycloak/dpv-realm.json`, `.env.example`, `.github/workflows/ci.yml`, `README.md`, Tests in `tests/test_login.py`, `tests/test_rundumtest.py` und `tests/test_keycloak_echt.py`.

## 2026-10-21 · Projektordner auf dem Mac außerhalb von iCloud

**Entscheidung** (Sebastian, #23): Das Projekt liegt auf dem Mac in `~/Entwicklung/dpv-participant-management`, nicht in „Dokumente“ oder „Schreibtisch“. Das README nennt diesen Ort.

**Begründung:** Am 21.10.2026 waren fünf Kopien wie `pyproject 2.toml` versehentlich in einem Commit zu #6 (vor dem Pull Request entfernt). Belegt ist: Sebastians Ordner „Dokumente“ wird mit iCloud abgeglichen. Annahme: iCloud legt solche Kopien bei Konflikten an, etwa wenn git viele Dateien auf einmal ändert, und kann auch Dateien in `.git` doppeln oder nur in der Cloud behalten. Außerhalb von iCloud entfällt die Ursache. Nichts geht verloren, weil alles auf GitHub liegt.

**Umsetzung:** `README.md` („Projekt starten (Mac)“, Schritte 2 und 3), Test in `tests/test_grundgeruest.py`. Den bestehenden Ordner verschiebt Sebastian selbst (Anleitung im Pull Request). Zusätzlich sperrt auf Sebastians Mac `.git/info/exclude` Dateien nach dem Muster „Name Leerzeichen Zahl“ für git; das gilt nur dort und steht nicht im Repo.

## 2026-10-21 · Fehlerprotokoll ohne Personendaten

**Entscheidung** (Sebastian, Klärung von #6 am 20.10.2026 und Nachklärung am 21.10.2026):

1. **Fehlernummer:** Bei einem unerwarteten Fehler zeigt die Fehlerseite einen kurzen Hinweis in der Du-Form und eine zufällige Fehlernummer (z. B. `7F3K-92QA`). Dieselbe Nummer steht im Log. Wer einen Fehler meldet, nennt die Nummer.
2. **Kein Bezug zum Konto im Log,** auch keine interne Kontonummer. Ob das Log doch einen braucht, klärt Sebastian mit der Datenschutzperson (OP-2, vorgemerkt in #11).
3. **Muster statt echter Adresse:** Im Log steht das Muster der Adresse (z. B. `/anmeldungen/<int:pk>/`), nie die echte Adresse mit Nummern und nie angehängte Parameter. Passt eine Adresse zu keinem Muster, steht dort „unbekannte Adresse“.
4. **Kein Meldungstext im Log:** Von einem Fehler kommen nur seine Art (z. B. `ValueError`) und die Stellen im Code ins Log, nie sein Meldungstext. Das gilt für alle Log-Einträge, auch aus fremden Paketen.
5. **„Nicht gefunden“, „kein Zugriff“ und „ungültige Anfrage“** stehen als kurze Zeile im Log: Zeitpunkt, Art und Muster der Adresse, ohne Fehlernummer, ohne Bezug zum Konto und ohne frei gewählten Text aus der Anfrage. Djangos eigene Zeilen dazu sind abgeschaltet.
6. **Keine Fehlerberichte per Mail.** Djangos eingebaute Funktion dafür ist abgeschaltet.

**Begründung:** DSG-08: Echte Personendaten gelangen nie in KI-Werkzeuge, auch nicht zur Fehlersuche; Logs werden dafür leicht kopiert, sind schlechter geschützt als die Datenbank und werden länger aufbewahrt. Auch eine Kontonummer ist ein Personendatum. Schon eine Adresse wie `/konto/17/` kann sie enthalten, und Meldungstexte enthalten oft genau die eingegebenen Daten (z. B. „Mail … existiert schon“). Die Fehlernummer genügt für den häufigsten Fall, dass sich jemand meldet. Folge: Ein Fehler ist ohne Meldungstext schwerer zu finden; er wird lokal mit erfundenen Daten nachgestellt. Viele „kein Zugriff“ können ab P2 zeigen, dass jemand fremde Daten sucht, deshalb bleiben diese Zeilen. „Ungültige Anfrage“ (Nachtrag vom 21.10.2026 nach der unabhängigen Prüfung) zeigt z. B. einen falsch eingestellten Servernamen, bei dem das Tool jede Anfrage ablehnt. Der Fahrplan nennt Fehlerberichte per Mail mit Anfragedaten als Fehler des alten Tools (Abschnitt 6, Nr. 8).

**Umsetzung:** `core/errors.py`, `config/settings.py` (`LOGGING`, `ADMINS`, `MIDDLEWARE`), `config/urls.py`, `core/templates/500.html`, Tests in `tests/test_fehlerprotokoll.py`. Nicht Teil: freundliche Seiten für „nicht gefunden“ und „kein Zugriff“ (#21), Aufbewahrung der Logs und Zugriffsprotokoll des Webservers im Betrieb (#11).

## 2026-10-21 · Grundgerüst: nur grüne Pull Requests, Werkzeuge und Fassungen

**Entscheidung:**

1. **Nur grüne Pull Requests** (Sebastian, Klärung von #4 am 20.10.2026): Die KI schickt den Link zu einem Pull Request erst, wenn alle Prüfungen auf GitHub für den letzten Stand grün sind, und nennt das Ergebnis in der Beschreibung. Sebastian übernimmt keinen Pull Request mit roter Prüfung. Die Regel ersetzt die Sperre durch GitHub, bis das Repo veröffentlicht ist (#16).
2. **Werkzeuge und Fassungen** (KI, technisch):
   - `uv` verwaltet Python und Pakete. Kurze Paketliste in `pyproject.toml`, feste Fassungen in `uv.lock`.
   - Python genau 3.13, festgelegt in `.python-version` und `pyproject.toml`. Django 6.1 wie entschieden am 20.10.2026.
   - PostgreSQL 18, lokal in Docker (`dev/docker-compose.yml`) und in der Prüfung auf GitHub. Die Tests laufen nur gegen PostgreSQL, nie gegen eine Ersatzdatenbank.
   - Alle Prüfungen stehen in `pruefen.sh`. GitHub ruft dasselbe Skript auf; lokal und auf GitHub wird gleich geprüft.
   - Zugangsdaten kommen aus Umgebungsvariablen; lokal aus `.env`, die `uv run --env-file .env` einliest. Fehlt eine Pflichtangabe, startet das Tool nicht. Die Fehleranzeige für Entwickler ist nur an, wenn sie ausdrücklich eingeschaltet ist.
   - Fremde Bausteine im Prüfablauf auf GitHub sind auf einen festen Commit festgelegt.

**Begründung:** Zu 1: GitHub sperrt das Übernehmen roter Pull Requests bei privaten Repos ohne GitHub Pro nicht (Protokoll zu #4). Zu 2: `uv` installiert auch die passende Python-Fassung und macht die Startprobe einfacher (Protokoll zu #4). Die feste Python-Fassung ist nötig: Auf Sebastians Mac lagen am 21.10.2026 drei Python-Fassungen, und `uv` griff ohne Festlegung zu 3.11 und wich still auf Django 5.2 aus (Befund der KI). 3.13 statt 3.14, weil 3.13 länger erprobt ist und Django 6.1 beide unterstützt; die Fassung auf dem DPV-Server ist noch offen (OP-4). PostgreSQL 18 ist die neueste Hauptfassung; PostgreSQL pflegt jede Hauptfassung fünf Jahre, bei Erscheinen 2025 also bis 2030 (aus dem Wissen der KI, nicht eigens nachgesehen); die Fassung auf dem Server ist ebenfalls offen (OP-4). Ein gemeinsames Prüfskript verhindert, dass lokal etwas anderes geprüft wird als auf GitHub. Feste Commits verhindern, dass eine Änderung an einem fremden Baustein unbemerkt in die Prüfung gelangt. `uv run --env-file` liest die Umgebungsdatei ohne zusätzliches Paket.

**Umsetzung:** `CLAUDE.md` (Ablauf je Aufgabe, Schritte 4 und 6; Erfahrung „Erst alles hochladen“), `CONTRIBUTING.md` (Abschnitte 6 und 8), `.github/pull_request_template.md`, `README.md` („Projekt starten“), Pull Request zu #4.

## 2026-10-21 · P1 beginnt früher, Restpunkte von P0 laufen parallel

**Entscheidung** (Sebastian): Phase P1 „Gerüst“ beginnt am 21.10.2026 statt wie bisher vorgesehen am 30.11.2026. Die Restpunkte von P0 erledigt Sebastian parallel: Anfragen zu OP-1, OP-2 und OP-4 verschicken (bis 15.11.2026), altes Repo archivieren, Stundenlog führen; dazu, mit gleicher Frist wie E0, Liste 1 dem DPV mitteilen (OP-6, bis 29.11.2026). Prüfpunkt E0 bleibt am 29.11.2026; die Zieldaten im Fahrplan bleiben unverändert.

**Abweichung vom Fahrplan:** Das Ziel von P0 lautet „Rahmen steht, bevor Code entsteht“, und E0 sagt für den Fall ohne Antwort des DPV „P1 beginnt trotzdem“; beides setzt voraus, dass P1 erst nach E0 beginnt. Jetzt entsteht Code schon vor E0. Der Fahrplan bleibt unverändert, für den Beginn von P1 gilt dieser Eintrag.

**Begründung:** Die P1-Issues #4 bis #7 sind geklärt und haben keine offenen Fragen. Die beiden Klärungen für P1 werden erst gegen Ende der Phase gebraucht und haben laut OP-Tabelle Übergangslösungen: der Test-Client (OP-1, bis 31.01.2027; sonst ein eigenes Keycloak der Testumgebung) und der Testserver (OP-4, bis 28.02.2027; sonst ein eigener Testserver). OP-2 blockiert erst den Gesundheitsblock in P2 (spätestens 31.05.2027; sonst rückt er an den Anfang von P4) und Tor E3; die Zwischenschritte (Ansprechperson bis 31.12.2026, Entwurf bis 31.01.2027) laufen bei Sebastian neben P1. Ein früherer Beginn verschiebt keinen Termin nach hinten, sondern schafft Reserve (Einschätzung der KI). Die Restpunkte von P0 sind Sebastians eigene Aufgaben und keine Programmierarbeit; der Grundsatz „zwei Phasen parallel geht für eine Person nicht“ (`docs/fahrplan.md`, Kritischer Pfad) betrifft das Bauen und bleibt deshalb unberührt (Einschätzung der KI). Hinweis der KI: Die Stundenrechnung des Fahrplans zählt ab dem 26.10.2026; Stunden ab dem 21.10.2026 kommen trotzdem ins Stundenlog.

**Umsetzung:** `README.md` („Stand“). Vor dem Beginn hat die KI nach `CLAUDE.md` alle offenen Issues mit `vorgemerkt` oder ohne Phasen-Label durchgesehen (#8 bis #17); keines gehört nach P1, kein Label war zu korrigieren.

## 2026-10-20 · Auskünfte zum Keycloak des DPV, Phasen-Labels und vorgemerkte Issues

**Entscheidung** (Sebastian):

1. **Keycloak des DPV** (Auskunft von Sebastian): Die Selbstregistrierung ist erlaubt. Benutzername und Mail sind bei jedem Konto vorhanden, sind die festen Werte und ändern sich nicht; Vor- und Nachname können fehlen oder sich ändern. Unverändert gilt laut Fahrplan (P1): Das Tool verknüpft Konten über die feste Kennung (`sub`).
2. **Phasen-Labels:** Issues tragen das Label der Phase (`P0` bis `P10`), in die sie voraussichtlich gehören; ist sie unklar, keins. Das Label ist nur Orientierung, nie ein Filter.
3. **Vorgemerktes:** Was beim Klären auf später verschoben oder noch ungeklärt für eine spätere Phase angelegt wird, bekommt ein eigenes Issue mit dem Label `vorgemerkt`. Vor Beginn jeder Phase werden alle offenen vorgemerkten Issues und alle ohne Phasen-Label durchgesehen, nicht nur die der Phase.

**Begründung:** Zu 1: Die Auskünfte betreffen OP-1 schon jetzt, nicht erst mit dem Pull Request zu #5. Zu 2 und 3: Verschobene Punkte standen nur unter „Nicht Teil dieser Anforderung“ und wären mit dem Schließen des Issues aus dem Blick geraten (Hinweis der KI). Phasen-Labels geben die Übersicht; weil sich eine Zuordnung als falsch erweisen kann, sieht jede Phase alle vorgemerkten Issues und alle ohne Phasen-Label durch, und ein Fehler fällt spätestens beim nächsten Phasenbeginn auf.

**Umsetzung:** `CLAUDE.md` („Für Phasen und Vorgemerktes gilt“), `.claude/skills/issue-anlegen/SKILL.md` und `.claude/skills/grill-me/SKILL.md`, Labels `vorgemerkt` und `P0` bis `P10` auf GitHub, Issues #8 bis #17. Dazu Vorschläge der KI, denen Sebastian mit dem Übernehmen des Pull Requests zustimmt: OP-1 in `docs/fahrplan.md` (OP-Tabelle, Abschnitt 6 Nr. 39) und in `docs/anforderungen.md` (Offene Punkte) um die Auskunft aus Punkt 1 ergänzt.

## 2026-10-20 · Offene Punkte aus der Bestandsaufnahme

**Entscheidung** (Sebastian):

1. Die Stundenschwelle an E1 wird nicht weiter geklärt. Der Plan rechnet mit rund 7,5 Stunden je Woche, E1 verlangt 8, die Risikotabelle warnt unter 30 Stunden im Monat. Der Unterschied bleibt so stehen. Das Stundenkontingent soll das Projekt nicht weiter belasten. Der Fahrplan bleibt dafür unverändert.
2. Die Go/No-Go-Kriterien und die Betriebsspur aus dem Doc „Fahrplan Neubau“ kommen nicht ins Repo. Sie werden nicht mehr betrachtet.
3. Die fehlenden Diagramme hat Sebastian lokal. Das Diagramm zum Lebenszyklus einer Veranstaltung ergänzt er, wenn ein Issue den Lebenszyklus berührt. Damit das nicht vergessen wird, fragt `grill-me` dann danach.
4. Das Repo bleibt privat, bis das Tool in einen echten Test geht. Dann veröffentlicht Sebastian es. Dafür ändert sich keine Datei.

**Begründung:** Zu 2: Der Weg des Neubaus ist geklärt. Die Prüffragen von E1 stehen im Fahrplan selbst, den Betrieb regeln P6 und das Betriebshandbuch (Einschätzung der KI). Zu 4: Die EUPL wirkt erst, wenn das Repo veröffentlicht oder weitergegeben wird (Hinweis der KI).

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, P2, E1, Abschnitt 6 Nr. 35 bis 38), `.claude/skills/grill-me/SKILL.md` (Abschnitt 1). Dazu Vorschläge der KI, denen Sebastian mit dem Übernehmen des Pull Requests zustimmt: `docs/anforderungen.md`, OP-6 und Risikotabelle bei ROL-04 auf den Stand der Entscheidung vom 20.10.2026 gebracht (Protokoll in P2, Benachrichtigung in P8); Abschnitt 6 Nr. 7 und Nr. 26 im Fahrplan mit je einem erklärenden Hinweis.

## 2026-10-20 · Code aus dem alten Repo darf übernommen werden

**Entscheidung** (Sebastian): Code und Codeschnipsel aus dem alten Repo dürfen übernommen werden, wenn es dafür logische und sinnvolle Anwendungsfälle gibt. Sebastian hat dafür die Erlaubnis; sie wurde mündlich erteilt. Ersetzt im Eintrag „Neustart, Name, Lizenz, Umfang und Technik“ den Satz „Kein Programmcode wird übernommen“; auf dem alten Code wird weiterhin nicht weitergebaut.

**Begründung:** Der Fahrplan nannte die ungeklärte Lizenz als Hürde für jede Codeübernahme (Abschnitt 1, Punkt 5); die Erlaubnis räumt sie aus. Der Neustart bleibt, weil er vor allem am Datenmodell hängt (Punkte 1 bis 4) und laut Abschnitt 2 kein Baustein ohne Umbau passt. Sinnvoll sind deshalb vor allem kleine, in sich geschlossene Teile, etwa die KJP-Generatoren für LIS-03 (Einschätzung der KI).

**Umsetzung:** `CONTRIBUTING.md` (Abschnitt 10), `CLAUDE.md`, `README.md`, `.github/pull_request_template.md`, `docs/fahrplan.md` (Abschnitt 1, „Was ausdrücklich nicht gemacht wird“).

## 2026-10-20 · Klärungen zu OP-1 und OP-4, Arbeitsannahme zu OP-2, Gesundheitsdaten im Anforderungsdokument

**Entscheidung** (Sebastian):

- OP-1: Struktur, Rollen und Kreise verwaltet das Tool selbst (ORG-06). Der Keycloak-Login dient nur dazu, Personen zu verifizieren; mehr aus Keycloak kann später nachgeholt werden. Ein Lesekonto gibt es nicht. Personen mit Account dürfen selbst einwilligen (ab welchem Alter, prüft OP-2). Test-Client und Meldung gelöschter oder gesperrter Konten klärt Sebastian.
- OP-2 (Arbeitsannahme, keine Freigabe): Sebastian schätzt ein, dass die stellvertretende Bestätigung durch die anmeldende Leitung reicht (DSG-01), die Einwilligung nach Volljährigkeit fortgilt (DSG-02) und die Folgenabschätzung die Speicherung im eigenen Profil (FRM-04) mit abdecken soll. Bestätigen oder verwerfen muss das die Datenschutzperson des DPV, vor dem Gesundheitsblock und vor E3. Die übrigen OP-2-Schritte folgen wie im Fahrplan.
- OP-4: Ansprechperson für den Betrieb und Testserver klärt Sebastian. Mails gehen über das Google Workspace des DPV, wenn die Anbindung technisch möglich ist.
- Anforderungsdokument: Die drei Sätze zu Gesundheitsdaten (Einleitung und Verarbeitungen im Abschnitt Datenschutz, Risikotabelle) sind an FRM-04 angepasst (Vorschläge der KI, von Sebastian angenommen). Die Folgeänderungen aus der OP-1- und OP-4-Entscheidung bei ORG-05, ORG-06, OP-1, OP-4 und in der Risikotabelle sind Vorschläge der KI; Sebastian stimmt ihnen mit dem Übernehmen des Pull Requests zu.

**Begründung:** Die Abhängigkeit vom Verbands-Keycloak bleibt so klein wie möglich (ORG-03). Das Google Workspace nutzt der DPV bereits. Hinweise der KI: Ohne Lesekonto findet das Tool nur Personen, die sich schon einmal angemeldet haben. Ein Konto in Google Workspace darf laut Google 2.000 Mails pro Tag senden; bei Überschreitung ist der Versand bis zu 24 Stunden gesperrt, deshalb verteilt der Postausgang den Versand. Ob Jugendliche mit Account selbst einwilligen können, hängt am Alter und wird unter OP-2 mitgeprüft. Google Workspace als Mail-Dienstleister gehört in die Auftragsverarbeitung und das Verzeichnis der Verarbeitungen (OP-2).

**Umsetzung:** `docs/anforderungen.md` (Datenschutz, Risiken; Folgeänderungen bei ORG-05, ORG-06, OP-1 und OP-4), `docs/fahrplan.md` (Abschnitt 1, Planungsgrundlagen, Liste 2, P0, P5, kritischer Pfad, OP-Tabelle, E3, Risiken).

## 2026-10-20 · Kein Hitobito, eigenes Tool

**Entscheidung** (Sebastian): Statt Hitobito einzusetzen, wird das eigene Tool gebaut.

**Begründung:** Sebastian hat sich Hitobito angesehen. Es ist nicht so ansprechend und bedienungsfreundlich, wie er es sich wünscht. Das Anforderungsdokument verlangt ein Tool, das „freundlich in der Bedienung“ ist (Ausgangslage und Motivation). Hinweis der KI: Die Prüffrage von E0 im Fahrplan (deckt Hitobito Gesundheitsdaten pro Anmeldung, Teilnahmekreise und Keycloak-Login ohne eigene Programmierung ab?) ist damit nicht beantwortet. Entschieden hat die Bedienbarkeit.

**Umsetzung:** Dieser Eintrag ist das Ergebnis, das P0 verlangt („Hitobito geprüft und Ergebnis notiert“).

## 2026-10-20 · Entscheidungen nach der Prüfung der Rückmeldungen

**Entscheidung** (Sebastian, jeweils auf Empfehlung der KI):

1. Anforderungen und Fahrplan liegen maßgeblich im Repo (`docs/anforderungen.md`, `docs/fahrplan.md`). Änderungen laufen über Pull Requests. Die Docs in Claude bleiben als Stand vom 20.10.2026.
2. FRM-04: Die freiwillige Speicherung eigener Gesundheitsangaben im Profil bleibt, unter Vorbehalt. Sie wird in P4 als letzter Teil gebaut und entfällt, wenn die Datenschutz-Folgenabschätzung (OP-2) abrät oder bis dahin nicht fertig ist.
3. ROL-04: Das Protokoll der Rollenänderungen kommt in P2. Die Benachrichtigung Entfernter bleibt in P8.
4. Kontrolle: Sebastian prüft über die Rechtematrix in Klartext (ab P2) und eine Startprobe ohne KI an E1, E3 und E6: das Projekt allein nach dem README starten und die Tests laufen lassen. Code lesen lernt er aus eigenem Interesse nach und nach dazu, außerhalb der 8 Stunden pro Woche; die Lernzeit steht getrennt im Stundenlog (Ergänzung der KI).

**Begründung (Zusammenfassung der KI):**

1. Am 20.10.2026 konnte die Arbeitssitzung die beiden Docs zweimal nicht lesen; erst ein Export half. Die KI arbeitet im Repo, also gehören die maßgeblichen Texte dorthin.
2. Das Anforderungsdokument widerspricht sich: FRM-03, FRM-04 und BER-01 erlauben die Speicherung im eigenen Profil, die Datenschutz-Einleitung und die Risikotabelle sagen „nur pro Anmeldung“. Die Einzelregeln sind genauer; die Folgenabschätzung entscheidet, ob es dabei bleibt.
3. Das Anforderungsdokument verlangt selbst „ROL-04 früh einplanen“ (OP-6) und nennt das Risiko „unbemerkter Zugriff auf Daten von Kindern“. Echte Daten kommen ab E3 (Juni 2028), ROL-04 stand erst in P8. Kosten rund 4 Stunden (Annahme).
4. Wer den Code nicht liest, braucht ein Prüfwerkzeug in Klartext. Die Startprobe erfüllt die Gegenmaßnahme „Projekt ohne KI start- und testbar“ aus dem Anforderungsdokument. Lernzeit getrennt, damit das Stundenlog an E1 die tatsächliche Entwicklungszeit zeigt.

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, Phasen, Abschnitt 6), `docs/pruefung-2026-10-20.md`.

## 2026-10-20 · Django 6.1 mit django-allauth, Gestaltung ohne Build-Schritt

**Entscheidung** (KI, technisch):

- Start auf Django 6.1 mit django-allauth als Login-Baustein. Umstieg auf 6.2 LTS gleich zu Beginn von P3, auf Django 2029 in P8.
- Rückfall: Läuft allauth in P1 nicht mit dem Keycloak-Testzugang, Start auf Django 5.2 mit mozilla-django-oidc.
- Gestaltung mit einer CSS-Grundlage ohne Build-Schritt (Bootstrap oder Pico.css). Die Wahl fällt in P1 an der Musterseite. Alle Dateien kommen vom eigenen Server, nicht von fremden.

**Begründung:** Django 5.2 bekommt seit dem 03.12.2025 nur noch Sicherheitsupdates, bis April 2028. mozilla-django-oidc, der Login-Baustein des alten Tools, gibt Unterstützung nur bis Django 5.2 an (PyPI, Fassung 5.0.2 vom 19.12.2025). django-allauth gibt 6.0 und 6.1 an (PyPI, Fassung 65.20.0 vom 16.10.2026). Django 6.1 bekommt Sicherheitsupdates bis Dezember 2027, 6.2 LTS bis April 2030 (djangoproject.com, abgerufen am 20.10.2026). Tailwind braucht einen Build-Schritt; den vermeidet der Plan.

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, P1, P3, Risiken).

## 2026-10-20 · Neustart, Name, Lizenz, Umfang und Technik

**Entscheidung:**

- Neustart statt Weiterbau des alten Tools (`sebivtt/scout-participant-management`). Kein Programmcode wird übernommen, nur Regeln und Werkzeuge aus Sebastians Sitzungen seit dem 14.10.2026 (Sebastian).
- Name „DPV Anmeldetool“, Repo `sebivtt/dpv-participant-management`, Lizenz EUPL-1.2 (Sebastian).
- Liste 1: DSG-03, ORG-07, DSG-09 und der volle Nachweis von NFA-05 kommen fest nach der Generalprobe, jeweils mit Übergang (Sebastian).
- Start am 26.10.2026; 8 Stunden pro Woche im Jahresschnitt, Betrieb eingerechnet; Stundenlog ab P0 (Sebastian).
- Technik (KI): Django mit serverseitig erzeugten Seiten und htmx, Alpine.js für kleine Logik, SortableJS für den Formular-Baukasten, PostgreSQL. Login nur per OIDC über den Keycloak des DPV, ohne Schreibzugriff dort. Mails über einen Postausgang in der Datenbank, kein Celery und kein Redis.
- Arbeitsweise aus dem alten Repo übernommen (dort entschieden am 15. und 16.10.2026): Regeln in `CONTRIBUTING.md`; Fehler und Anforderungen nur als Issue; Issues erst mit `grill-me` klären und nur mit Label `geklärt` umsetzen; ein Issue ergibt einen Pull Request mit eigenem Test; unabhängige Prüfung vor jedem Pull Request.

**Begründung:** Fahrplan, Abschnitt 1 (fünf Punkte, am Code des alten Tools geprüft) und Abschnitt 3 (Machbarkeit bei 8 Stunden pro Woche).

**Umsetzung:** `LICENSE`, `docs/fahrplan.md`, `CONTRIBUTING.md`, `CLAUDE.md`.
