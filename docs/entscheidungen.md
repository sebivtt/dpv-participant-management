# Entscheidungen

Fachliche und technische Entscheidungen mit Begründung. Neue Einträge oben. Wer eine Regel ändern will, ergänzt einen neuen Eintrag, statt einen alten zu überschreiben.

Format: Datum · Entscheidung · Begründung · Umsetzung

---

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
