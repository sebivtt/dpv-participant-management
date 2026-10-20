# Entscheidungen

Fachliche und technische Entscheidungen mit Begründung. Neue Einträge oben. Wer eine Regel ändern will, ergänzt einen neuen Eintrag, statt einen alten zu überschreiben.

Format: Datum · Entscheidung · Begründung · Umsetzung

---

## 2026-10-20 · Klärungen zu OP-1, OP-2 und OP-4, Gesundheitsdaten im Anforderungsdokument

**Entscheidung** (Sebastian):

- OP-1: Struktur, Rollen und Kreise verwaltet das Tool selbst (ORG-06). Der Keycloak-Login dient nur dazu, Personen zu verifizieren; mehr aus Keycloak kann später nachgeholt werden. Ein Lesekonto gibt es nicht. Personen mit Account dürfen selbst einwilligen. Test-Client und Meldung gelöschter oder gesperrter Konten klärt Sebastian.
- OP-2 (Arbeitsannahme, keine Freigabe): Sebastian schätzt ein, dass die stellvertretende Bestätigung durch die anmeldende Leitung reicht (DSG-01), die Einwilligung nach Volljährigkeit fortgilt (DSG-02) und die Folgenabschätzung die Speicherung im eigenen Profil (FRM-04) mit abdeckt. Bestätigen oder verwerfen muss das die Datenschutzperson des DPV, vor dem Gesundheitsblock und vor E3. Die übrigen OP-2-Schritte folgen wie im Fahrplan.
- OP-4: Ansprechperson für den Betrieb und Testserver klärt Sebastian. Mails gehen über das Google Workspace des DPV, wenn die Anbindung technisch möglich ist.
- Anforderungsdokument: Die drei Sätze zu Gesundheitsdaten (Einleitung und Verarbeitungen im Abschnitt Datenschutz, Risikotabelle) sind an FRM-04 angepasst (Vorschläge der KI, von Sebastian angenommen).

**Begründung:** Die Abhängigkeit vom Verbands-Keycloak bleibt so klein wie möglich (ORG-03). Den Google Workspace nutzt der DPV bereits. Hinweise der KI: Ohne Lesekonto findet das Tool nur Personen, die sich schon einmal angemeldet haben. Ein Konto in Google Workspace darf laut Google 2.000 Mails pro Tag senden; bei Überschreitung ist der Versand bis zu 24 Stunden gesperrt, deshalb verteilt der Postausgang den Versand. Ob Jugendliche mit Account selbst einwilligen können, hängt am Alter (in Deutschland in der Regel 16 Jahre für Einwilligungen bei Online-Diensten, Art. 8 DSGVO; keine Rechtsberatung) und wird unter OP-2 mitgeprüft.

**Umsetzung:** `docs/anforderungen.md`, `docs/fahrplan.md` (Planungsgrundlagen, P5, OP-Tabelle mit OP-1, OP-2 und OP-4, Risiken).

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
