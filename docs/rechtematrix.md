# Rechtematrix

Wer im Tool welche Daten sehen und was damit tun darf, in Alltagssprache. Die Matrix ist das Prüfwerkzeug für die Rechte (Entscheidung 4 vom 20.10.2026): Sie lässt sich gegen `docs/anforderungen.md` lesen, ohne Code zu lesen. Sie wird dauerhaft fortgeschrieben; wer neue Daten ins Tool bringt, ergänzt im selben Pull Request ihre Zeilen (`CONTRIBUTING.md`, Abschnitt 4).

Erster Entwurf für P2 vom 23.10.2026 (#87). Spätere Phasen ergänzen ihre Zeilen in ihren eigenen Issues.

## Inhalt

1. [So liest man die Matrix](#so-liest-man-die-matrix)
2. [Eigenes Profil](#eigenes-profil)
3. [Personen mit Konto](#personen-mit-konto)
4. [Verwaltete Personen](#verwaltete-personen)
5. [Einheiten](#einheiten)
6. [Leitungen und Rollen](#leitungen-und-rollen)
7. [Veranstaltungen und Anmeldungen](#veranstaltungen-und-anmeldungen)
8. [Gesundheitsangaben](#gesundheitsangaben)
9. [Support-Zugang der Admins](#support-zugang-der-admins)
10. [Protokolle](#protokolle)
11. [Technische Daten des Logins](#technische-daten-des-logins)
12. [Tabellen in der Datenbank](#tabellen-in-der-datenbank)

## So liest man die Matrix

**Grundregel:** Was hier nicht ausdrücklich erlaubt ist, ist verboten (`CONTRIBUTING.md`, Abschnitt 4). Hat eine Person mehrere Rollen, darf sie alles, was eine davon erlaubt (#90). Rechte entstehen nur aus Rollen und Mitgliedschaften im Tool, nie aus Keycloak und nie daraus, wer etwas angelegt hat (#89). Rechte werden bei jedem Klick neu berechnet; wer eine Rolle verliert, verliert das Recht beim nächsten Klick (#90).

**Spalten:**

- **Kennung:** zwei Buchstaben für den Abschnitt und eine Nummer, z. B. `VP-02`. Tests nennen die Kennung ihrer Zeile.
- **Wer:** Rolle oder Art des Kontos (Begriffe unten).
- **Daten** und **Aktion:** was genau gesehen oder getan wird.
- **Ergebnis:** erlaubt oder verboten. Verbotene Einträge mit Kennung in der Adresse zeigen „nicht gefunden“ (404) wie ein nicht vorhandener Eintrag; ganze Bereiche ohne Kennung zeigen „kein Zugriff“ (403) (#64).
- **Quelle:** Anforderung aus `docs/anforderungen.md`, Entscheidung aus `docs/entscheidungen.md` oder das Issue, in dem die Regel geklärt wurde.
- **Stand:** „geplant“ mit dem Issue, das die Zeile baut, oder „gebaut“ mit den Tests für den erlaubten und den verbotenen Fall.

**Wer:**

- **Leitung:** Gruppenleitung, Stammesleitung, Ringleitung oder Bundesleitung einer Einheit. Ihr **Bereich** ist die geleitete Einheit mit allen Einheiten darunter; der Bereich einer Gruppenleitung ist nur ihre Gruppe.
- **Mitglied:** Person mit Konto und Mitgliedschaft in einer Einheit, ohne Leitungsrolle.
- **Konto ohne Zuordnung:** Person mit Konto, ohne Mitgliedschaft und ohne Rolle (#9).
- **Verbandsleitung**, **DPV-Veranstaltungsteam:** Rollen im Verband, ohne Mitgliedschaft (ROL-01).
- **Admin:** technische Rolle (BER-02). Ohne Support-Zugang hat ein Admin keine Rechte einer Leitung (#89); **Admin im Support-Zugang** hat für eine Einheit die Rechte ihrer Leitung (#92).
- **Veranstaltungsleitung:** wer eine Veranstaltung angelegt hat oder hinzugefügt wurde (TEAM-01).
- **Ansprechperson:** wer eine Anmeldung abgegeben hat.
- **Jede Person mit Konto:** alle oben, egal mit welcher Rolle.

**Wie die Tests die Zeilen prüfen:** Eine Zeile „erlaubt“ prüft als verbotenen Fall den nächsten Nachbarn, etwa eine andere Einheit oder eine Ebene darunter. Eine Zeile „verboten“ prüft als erlaubten Fall die Gegenprobe, dass der vorgesehene Weg weiter funktioniert. Beides auch über direkte Adressen, htmx-Anfragen und manipulierte Formulare (#90).

**Außerhalb des Tools:** Befehle auf dem Server (Verband und Bünde anlegen, Admins und die erste Verbandsleitung benennen, im Notfall eine leere Einheit löschen) braucht Zugang zum Server; sie stehen im `README.md` und schreiben ins Protokoll. Die Matrix regelt, was im Tool geht.

## Eigenes Profil

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| EP-01 | Jede Person mit Konto | eigenes Profil: Vorname, Nachname, Benutzername, Mail, Fahrtenname, Mitgliedschaft und Rollen | ansehen („Mein Profil“) | erlaubt | PER-01, ORG-05, #96 | geplant (#96) |
| EP-02 | Jede Person mit Konto, auch Leitungen und Admins | Profil einer anderen Person über „Mein Profil“ (andere Adresse, angehängter Parameter, htmx) | ansehen | verboten; die Seite zeigt immer die angemeldete Person | PER-01, BER-01, #96 | geplant (#96) |
| EP-03 | Jede Person mit Konto | eigener Fahrtenname | eintragen, ändern, löschen | erlaubt | PER-01, #111 | geplant (#111) |
| EP-04 | Alle außer der Person selbst, auch Leitungen und Admins im Support-Zugang | Fahrtenname einer Person mit Konto | ändern | verboten | #111 | geplant (#111) |
| EP-05 | Jede Person mit Konto, auch Leitungen und Admins | Vorname, Nachname, Benutzername und Mail eines Kontos | ändern im Tool | verboten; sie kommen aus dem DPV-Konto | #96, #65 | geplant (#96) |
| EP-06 | Mitglied | eigene Mitgliedschaft | beenden (austreten) | erlaubt, nur ohne Leitungsrollen in Einheiten | ROL-01, #65 | geplant (#65) |
| EP-07 | Jede Person mit Konto | Mitgliedschaft einer anderen Person | über „austreten“ beenden | verboten | #65 | geplant (#65) |
| EP-08 | Jede Person mit Konto, auch Konto ohne Zuordnung | sich selbst einer Einheit zuordnen | als Mitglied eintragen | verboten | #65 | geplant (#65) |

## Personen mit Konto

Was Leitungen sehen: Name, Fahrtenname, Mail, Organisation und Rollen (#87, Frage 4; #111). Personen ohne Konto stehen unter „Verwaltete Personen“; die Liste „Personen“ einer Einheit zeigt beide (#117).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| PK-01 | Gruppenleitung | Mitglieder ihrer Gruppe | ansehen | erlaubt | BER-01, #87 | geplant (#65) |
| PK-02 | Stammesleitung | Mitglieder ihres Stammes und seiner Gruppen | ansehen | erlaubt | BER-01, #87 | geplant (#65) |
| PK-03 | Ringleitung, Bundesleitung | Mitglieder ihres Rings bzw. Bundes und aller Einheiten darunter | ansehen | erlaubt | BER-01, #87 | geplant (#65) |
| PK-04 | Leitung | Personen mit Konto außerhalb ihres Bereichs, z. B. Stammesleitung der Zugvögel bei Walhall, Gruppenleitung bei einer anderen Gruppe ihres Stammes | ansehen | verboten, „nicht gefunden“ | BER-01 | geplant (#65) |
| PK-05 | Mitglied | andere Personen mit Konto, auch in der eigenen Einheit | ansehen | verboten | BER-01 | geplant (#65) |
| PK-06 | Konto ohne Zuordnung | andere Personen mit Konto | ansehen | verboten | BER-01, #9 | geplant (#9) |
| PK-07 | Verbandsleitung, DPV-Veranstaltungsteam | Personen mit Konto in Bünden, Ringen, Stämmen und Gruppen | ansehen | verboten | ROL-03, ROL-05, #94 | geplant (#94) |
| PK-08 | Admin ohne Support-Zugang | Personen mit Konto | ansehen | verboten | BER-02, #92 | geplant (#92) |
| PK-09 | Leitung | Personen mit Konto in ihrem Bereich | suchen nach Vorname, Nachname, Fahrtenname | erlaubt | #93, #111 | geplant (#93) |
| PK-10 | Leitung | Personen mit Konto außerhalb ihres Bereichs | suchen nach Namen | verboten, kein Treffer | #93 | geplant (#93) |
| PK-11 | Bundesleitung | Konten ohne Zuordnung im ganzen Tool; Treffer zeigen Name, Fahrtenname, Mail | suchen nach Namen, ab 3 Buchstaben | erlaubt | #93 | geplant (#93) |
| PK-12 | Gruppenleitung, Stammesleitung, Ringleitung, Verbandsleitung | Konten ohne Zuordnung | suchen nach Namen | verboten | #93, #94 | geplant (#93) |
| PK-13 | Leitung, Verbandsleitung | jedes Konto, das sich schon einmal angemeldet hat; Treffer zeigt Name und Fahrtenname | finden über die genaue Mail oder den genauen Benutzernamen | erlaubt | #93, #94 | geplant (#93) |
| PK-14 | Mitglied, DPV-Veranstaltungsteam, Konto ohne Zuordnung, Admin ohne Support-Zugang | Konten | suchen oder finden | verboten | #93, ROL-05 | geplant (#93) |
| PK-15 | Jede Person mit Konto | alle Konten | durchblättern | verboten; eine Liste aller Konten gibt es nicht | #93 | geplant (#93) |
| PK-16 | Leitung, Verbandsleitung | Einheit einer gefundenen Person außerhalb des eigenen Bereichs, auch in Meldungen | erfahren | verboten; Meldungen nennen die Einheit nicht | BER-01, #93, #94, #65 | geplant (#93) |
| PK-17 | Leitung | Person mit Konto ohne Mitgliedschaft | als Mitglied aufnehmen in die eigene Einheit oder eine darunter | erlaubt | #65 | geplant (#65) |
| PK-18 | Leitung | Person, die außerhalb des Bereichs Mitglied ist | aufnehmen | verboten; Meldung ohne Einheit | #65 | geplant (#65) |
| PK-19 | Stammesleitung, Ringleitung, Bundesleitung | Mitglieder ihres Bereichs | verschieben innerhalb des Bereichs | erlaubt | #65 | geplant (#65) |
| PK-20 | Leitung | Mitglieder | verschieben, wenn Herkunft oder Ziel außerhalb des Bereichs liegt | verboten | #65 | geplant (#65) |
| PK-21 | Leitung | Mitgliedschaft in ihrem Bereich | beenden (austragen) | erlaubt, wenn die Leitungsrollen der Person danach auf ihrem Pfad liegen | #65, #89 | geplant (#65) |
| PK-22 | Leitung | Mitgliedschaft außerhalb ihres Bereichs | beenden | verboten | #65 | geplant (#65) |
| PK-23 | Verbandsleitung, DPV-Veranstaltungsteam, Mitglied, Konto ohne Zuordnung | Mitgliedschaften anderer | aufnehmen, verschieben, beenden | verboten | #65 | geplant (#65) |

## Verwaltete Personen

Verwaltete Personen sind Profile ohne Konto (PER-02). Angaben in P2: Vorname, Nachname, Geburtsdatum, Fahrtenname (#117). Gesundheitsangaben gibt es im Profil verwalteter Personen nie (FRM-04, siehe GA-05).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| VP-01 | Leitung | verwaltete Person in der eigenen Einheit oder einer darunter | anlegen | erlaubt | PER-02, #117 | geplant (#117) |
| VP-02 | Leitung | verwaltete Personen ihres Bereichs | ansehen, bearbeiten | erlaubt | BER-01, PER-02 | geplant (#117) |
| VP-03 | Leitung | verwaltete Personen außerhalb ihres Bereichs, z. B. Stammesleitung der Zugvögel bei Walhall, Gruppenleitung bei einer anderen Gruppe | anlegen, ansehen, bearbeiten | verboten, „nicht gefunden“ | BER-01 | geplant (#117) |
| VP-04 | Leitung, die entfernt wurde | verwaltete Personen der früheren Einheit, auch im schon geöffneten Formular | ansehen, bearbeiten | verboten ab dem nächsten Klick | PER-02, #90 | geplant (#117) |
| VP-05 | Wer eine verwaltete Person angelegt hat, ohne Leitungsrolle dort | diese Person | ansehen, bearbeiten | verboten | PER-02, #89 | geplant (#117) |
| VP-06 | Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | verwaltete Personen | anlegen, ansehen, bearbeiten | verboten | BER-01, ROL-03, ROL-05, #92 | geplant (#117) |
| VP-07 | Stammesleitung, Ringleitung, Bundesleitung | verwaltete Person ihres Bereichs | verschieben innerhalb des Bereichs | erlaubt | PER-02, #118 | geplant (#118) |
| VP-08 | Gruppenleitung; jede Leitung, wenn Herkunft oder Ziel außerhalb des Bereichs liegt | verwaltete Person | verschieben | verboten | PER-02, #118 | geplant (#118) |
| VP-09 | Leitung | verwaltete Person ihres Bereichs | löschen, endgültig | erlaubt | #118 | geplant (#118) |
| VP-10 | Leitung außerhalb des Bereichs, Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | verwaltete Person | löschen | verboten | #118 | geplant (#118) |
| VP-11 | Leitung beim Anlegen | Bestätigung der Einwilligung (welches Konto wann bestätigt hat) | setzen, nur beim Anlegen und nur im eigenen Namen | erlaubt | DSG-02, #98 | geplant (#98) |
| VP-12 | Jede Person mit Konto, auch Admins im Support-Zugang | Bestätigung der Einwilligung | ansehen im Tool | verboten in P2 | #98 | geplant (#98) |
| VP-13 | Jede Person mit Konto, auch Admins im Support-Zugang | Bestätigung der Einwilligung | nachträglich ändern oder für ein anderes Konto setzen | verboten | #98 | geplant (#98) |
| VP-14 | Leitung der direkt darüberliegenden Einheit; Leitungen derselben Einheit | angezeigte Leitungsrolle einer verwalteten Person („nur Anzeige“) | eintragen, entfernen | erlaubt | PER-07, #99 | geplant (#99) |
| VP-15 | Alle anderen: höhere Ebenen, Leitungen außerhalb, Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | angezeigte Leitungsrolle | eintragen, entfernen | verboten | #99 | geplant (#99) |
| VP-16 | Jede Person | Rechte einer Leitung über eine angezeigte Leitungsrolle | bekommen | verboten; die Anzeige gibt niemandem Rechte und zählt nicht als Leitung | PER-07, #99 | geplant (#99) |

## Einheiten

Einheiten sind Verband, Bünde, Ringe, Stämme und Gruppen (ORG-01); im Tool heißen sie „Organisation“ (#96).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| EH-01 | Leitung | Namen aller Einheiten des eigenen Bundes | ansehen | erlaubt | #87, Frage 5 | geplant (#93) |
| EH-02 | Mitglied | Namen aller Einheiten des eigenen Bundes | ansehen | erlaubt | #87, Frage 5 | geplant (#134), noch keine Seite in P2 |
| EH-03 | Mitglied, Leitung (ohne Rolle im Verband) | Namen von Einheiten anderer Bünde | ansehen | verboten | #87, Frage 5 | geplant (#93) |
| EH-04 | Verbandsleitung, DPV-Veranstaltungsteam | Namen aller Bünde | ansehen | erlaubt | #87, Frage 5; #94; Entscheidung vom 23.10.2026 | geplant: Verbandsleitung mit #94; DPV-Veranstaltungsteam mit #134, noch keine Seite in P2 |
| EH-05 | Verbandsleitung, DPV-Veranstaltungsteam (ohne weitere Rolle) | Namen von Ringen, Stämmen und Gruppen | ansehen | verboten; nicht ausdrücklich erlaubt | #87, Frage 5 | geplant (#94) |
| EH-06 | Admin | Namen aller Einheiten, um einen Support-Zugang zu starten | ansehen | erlaubt | #92 | geplant (#92) |
| EH-07 | Konto ohne Zuordnung | Einheiten und ihre Namen | ansehen | verboten | #9, #87 | geplant (#9) |
| EH-08 | Leitung, Verbandsleitung, Admin | Navigationspunkt „Organisation“ (Leitung: die geleiteten Einheiten mit denen darunter; Verbandsleitung: die Bünde; Admin: Start des Support-Zugangs) | sehen und öffnen | erlaubt | #93, #94, #92 | geplant (#93) |
| EH-09 | Mitglied, Konto ohne Zuordnung, DPV-Veranstaltungsteam | Navigationspunkt „Organisation“ | sehen und öffnen | verboten; der Punkt fehlt, die Adresse zeigt „kein Zugriff“ | #93, #64 | geplant (#93) |
| EH-10 | Bundesleitung | Ringe (nur in einem Bund mit Ringen) und Stämme im eigenen Bund | anlegen | erlaubt | ORG-06, #95 | geplant (#95) |
| EH-11 | Ringleitung | Stämme im eigenen Ring | anlegen | erlaubt | ORG-06, #95 | geplant (#95) |
| EH-12 | Stammesleitung | Gruppen im eigenen Stamm | anlegen | erlaubt | ORG-06, #95 | geplant (#95) |
| EH-13 | Gruppenleitung; Leitungen außerhalb ihres Bereichs; höhere Ebenen zwei Stufen tiefer, z. B. Bundesleitung Gruppen in einem Stamm (außer beim Einspringen, EH-18) | Einheiten | anlegen | verboten | #95 | geplant (#95) |
| EH-14 | Leitung der direkt darüberliegenden Einheit; Leitung der Einheit selbst | Name einer Einheit | umbenennen | erlaubt | ORG-06, #95 | geplant (#95) |
| EH-15 | Höhere Ebenen, Leitungen außerhalb, Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | Name einer Einheit | umbenennen | verboten | #95 | geplant (#95) |
| EH-16 | Bundesleitung | Stamm ihres Bundes | einem Ring zuordnen oder in einen anderen Ring desselben Bundes verschieben | erlaubt | #88, #95 | geplant (#95) |
| EH-17 | Ringleitung, Stammesleitung, Leitungen anderer Bünde | Stamm | einem Ring zuordnen oder Ring wechseln | verboten | #95 | geplant (#95) |
| EH-18 | Leitung der direkt darüberliegenden Einheit, solange die Einheit keine Leitung mit Konto hat | Einheiten unter dieser Einheit | anlegen, bearbeiten (einspringen) | erlaubt; endet, sobald wieder eine Leitung benannt ist | #95, #99 | geplant (#95) |
| EH-19 | Leitung der direkt darüberliegenden Einheit, wenn die Einheit eine Leitung mit Konto hat | Einheiten unter dieser Einheit | anlegen, bearbeiten | verboten | #95 | geplant (#95) |
| EH-20 | Jede Person mit Konto, auch Verbandsleitung und Admins | Verband und Bünde | anlegen | verboten im Tool; geht nur per Befehl auf dem Server | #88, #95 | geplant (#95) |
| EH-21 | Jede Person mit Konto, auch Admins | Einheit | löschen | verboten im Tool, es gibt keinen Löschknopf (W5) | #88, #95 | geplant (#95) |

## Leitungen und Rollen

Rollen nach ROL-01; die Mitgliedschaft steht unter „Personen mit Konto“, die Rolle Admin unter „Support-Zugang der Admins“.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| RO-01 | Leitung | Leitungen der Einheiten auf dem eigenen Pfad (eigene Einheit und darüber bis zum Bund) | ansehen | erlaubt | #87, Frage 5 | geplant (#93) |
| RO-02 | Mitglied | Leitungen der Einheiten auf dem eigenen Pfad | ansehen | erlaubt | #87, Frage 5 | geplant (#134), noch keine Seite in P2 |
| RO-03 | Leitung | Leitungen aller Einheiten in ihrem Bereich (Ansicht „Leitungen“) | ansehen | erlaubt | #87, Frage 5; #93 | geplant (#93) |
| RO-04 | Mitglied, Leitung | Leitungen von Einheiten, die weder auf dem Pfad noch im eigenen Bereich liegen, z. B. Nachbarstamm, anderer Bund | ansehen | verboten | #87, Frage 5 | geplant (#93) |
| RO-05 | Verbandsleitung | Bundesleitungen, Verbandsleitungen, Mitglieder des DPV-Veranstaltungsteams | ansehen | erlaubt | #87, Frage 5; #94 | geplant (#94) |
| RO-06 | Verbandsleitung (ohne weitere Rolle) | Leitungen von Ringen, Stämmen und Gruppen | ansehen | verboten | ROL-03, #94 | geplant (#94) |
| RO-07 | DPV-Veranstaltungsteam (ohne weitere Rolle) | Leitungen jeder Ebene, auch Bundesleitungen | ansehen | verboten | ROL-05, Entscheidung vom 23.10.2026 | geplant (#94) |
| RO-08 | Konto ohne Zuordnung | Leitungen | ansehen | verboten | #9, #87 | geplant (#9) |
| RO-09 | Wer die Ansicht „Leitungen“ einer Einheit sehen darf | angezeigte Leitungsrollen verwalteter Personen (Name bzw. Fahrtenname, „ohne Konto, nur Anzeige“) | ansehen | erlaubt | #99 | geplant (#99) |
| RO-10 | Leitung der direkt darüberliegenden Einheit (Bund: Ring oder Stamm direkt am Bund; Ring: Stamm; Stamm: Gruppe) | Leitungen der Einheit darunter | benennen, entfernen | erlaubt | ROL-02, #93 | geplant (#93) |
| RO-11 | Leitung | weitere Leitungen derselben Einheit, auch gegenseitig und sich selbst | benennen, entfernen | erlaubt | ROL-02, #93 | geplant (#93) |
| RO-12 | Leitung | sich selbst als Leitung einer Einheit direkt unter der eigenen | einsetzen | erlaubt | ROL-02, #93 | geplant (#93) |
| RO-13 | Leitung zwei oder mehr Ebenen darüber, z. B. Bundesleitung bei einer Gruppe; Leitungen außerhalb | Leitungen | benennen, entfernen | verboten | ROL-02, #93 | geplant (#93) |
| RO-14 | Mitglied, Konto ohne Zuordnung, DPV-Veranstaltungsteam | Rollen anderer | vergeben, entfernen | verboten | ROL-05, #93, #94 | geplant (#93) |
| RO-15 | Verbandsleitung | Bundesleitungen, weitere Verbandsleitungen (auch gegenseitig und sich selbst), Mitglieder des DPV-Veranstaltungsteams | benennen, entfernen | erlaubt | ROL-03, #94 | geplant (#94) |
| RO-16 | Verbandsleitung | sich selbst als Bundesleitung; sie sieht dann über diese Rolle die Personen des Bundes | einsetzen | erlaubt | ROL-02, #94 | geplant (#94) |
| RO-17 | Verbandsleitung (ohne weitere Rolle) | Leitungen von Ringen, Stämmen und Gruppen | benennen, entfernen | verboten | ROL-03, #94 | geplant (#94) |
| RO-18 | Alle außer der Verbandsleitung | Verbandsleitungen, Mitglieder des DPV-Veranstaltungsteams | benennen, entfernen | verboten im Tool | ROL-03, #94 | geplant (#94) |
| RO-19 | Jede Person mit Konto, auch Admins | Rolle Admin | vergeben, entfernen | verboten im Tool; bis ADM-01 (P6) nur per Befehl auf dem Server | ADM-01, #89 | geplant (#90) |

## Veranstaltungen und Anmeldungen

In P2 als Probe: Veranstaltungen mit Name, Beginn und Ende (#100); Anmeldungen entstehen nur über den Testdaten-Befehl (#101, #103). Teilnahmekreise und BER-07 kommen in P3.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| VA-01 | Jede Person mit Konto, auch Konto ohne Zuordnung | neue Veranstaltung; wer sie anlegt, ist ihre Veranstaltungsleitung | anlegen | erlaubt | BER-03, TEAM-01, #9 | geplant (#100) |
| VA-02 | Veranstaltungsleitung | eigene Veranstaltung: Name, Beginn, Ende | ansehen, bearbeiten | erlaubt | TEAM-01, #100 | geplant (#100) |
| VA-03 | Alle, die nicht ihre Veranstaltungsleitung sind: Leitungen jeder Ebene, Verbandsleitung, DPV-Veranstaltungsteam, Admins (auch im Support-Zugang), Konto ohne Zuordnung | Veranstaltung | ansehen, bearbeiten | verboten, „nicht gefunden“ | TEAM-01, #100 | geplant (#100) |
| VA-04 | Jede Person mit Konto | Veranstaltung | löschen | verboten in P2 | #100 | geplant (#100) |
| AN-01 | Veranstaltungsleitung | Anmeldungen zur eigenen Veranstaltung: Ansprechperson, angemeldete Personen | ansehen | erlaubt | TEAM-01, #90, #101 | geplant (#101) |
| AN-02 | Ansprechperson | eigene Anmeldung ohne Gesundheitsangaben, auch nach Verlust einer Leitungsrolle | ansehen | erlaubt | #90, #101 | geplant (#101) |
| AN-03 | Alle anderen, z. B. Leitungen der Einheit der angemeldeten Person und darüber, Verbandsleitung, DPV-Veranstaltungsteam, Admins (auch im Support-Zugang) | Anmeldung | ansehen | verboten, „nicht gefunden“ (Leitungen später vielleicht, #110) | BER-01, #90, #101 | geplant (#101) |
| AN-04 | Ansprechperson | sich selbst; Personen, die sie verwalten darf (verwaltete Personen und Mitglieder mit Konto ihres Bereichs) | anmelden (in P2 nur im Datenmodell) | erlaubt | ANM-01, #101 | geplant (#101) |
| AN-05 | Ansprechperson | Personen außerhalb ihres Bereichs; bei Verbandsleitung und Konto ohne Zuordnung jede andere Person | anmelden | verboten | ANM-01, #9, #101 | geplant (#101) |
| AN-06 | Jede Person mit Konto | Anmeldungen | im Tool anlegen, ändern, löschen | verboten in P2; nur der Testdaten-Befehl legt sie an | #101 | geplant (#101) |

## Gesundheitsangaben

In P2 nur als Probe in Anmeldungen (#102), unter der Bedingung aus W2; sonst in P4. Gesundheitsangaben im eigenen Profil kommen frühestens in P4 (FRM-04, unter Vorbehalt).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| GA-01 | Veranstaltungsleitung | Gesundheitsangaben in Anmeldungen zur eigenen Veranstaltung | ansehen | erlaubt | BER-01, TEAM-01, #102 | geplant (#102) |
| GA-02 | Ansprechperson | Gesundheitsangaben in der eigenen Anmeldung, auch dass es welche gibt | ansehen | verboten; der Abschnitt fehlt ganz | BER-01, #90, #102 | geplant (#102) |
| GA-03 | Gruppen-, Stammes-, Ring- und Bundesleitung der angemeldeten Person, Verbandsleitung, Admin (auch im Support-Zugang) | Gesundheitsangaben in Anmeldungen | ansehen | verboten | BER-01, #102 | geplant (#102) |
| GA-04 | Jede Person mit Konto | Gesundheitsangaben in Anmeldungen | im Tool eingeben, ändern | verboten in P2; nur der Testdaten-Befehl legt sie an | #102 | geplant (#102) |
| GA-05 | Jede Person mit Konto | Gesundheitsangaben im Profil einer verwalteten Person | speichern | verboten; das Feld gibt es nicht | PER-02, FRM-04, #117 | geplant (#117) |

## Support-Zugang der Admins

Der „technische Vollzugriff“ der Admins (BER-02) besteht im Tool nur als Support-Zugang mit den Rechten der Leitung einer Einheit (#92). Admin wird man bis ADM-01 nur per Befehl auf dem Server (RO-19).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| SZ-01 | Admin | Support-Zugang für genau eine Einheit (nicht den Verband), mit Anlass aus einer festen Liste, höchstens 60 Minuten | starten, beenden | erlaubt | BER-02, #92 | geplant (#92) |
| SZ-02 | Leitung, Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam | Support-Zugang | starten | verboten | #92 | geplant (#92) |
| SZ-03 | Admin im Support-Zugang | alles, was die Leitung der gewählten Einheit dort und darunter sehen und ändern darf | wie diese Leitung | erlaubt; jeder Zugriff steht im Protokoll der Admin-Zugriffe | BER-02, #92 | geplant (#92) |
| SZ-04 | Admin im Support-Zugang | Einheiten außerhalb der gewählten; alles nach Ablauf, Abmelden oder Beenden | ansehen, ändern | verboten ab dem nächsten Klick | #92, #90 | geplant (#92) |
| SZ-05 | Admin im Support-Zugang | Rolle für sich selbst, als Leitung oder Mitglied | vergeben | verboten | #92 | geplant (#92) |
| SZ-06 | Admin ohne Support-Zugang | Personendaten: Personen mit Konto, verwaltete Personen, Anmeldungen | ansehen, ändern | verboten | BER-02, #89, #92 | geplant (#92) |

## Protokolle

In P2 werden die Protokolle nur geschrieben; die Einsicht kommt mit ADM-03 in P8 (Entscheidung W4). Der Testdaten-Befehl (#103) darf die Datenbank lokal und in der Testumgebung vollständig leeren, auch die Protokolle.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| PR-01 | Jede Person mit Konto, auch Admins und Verbandsleitung | Protokoll der Rollenänderungen | ansehen im Tool | verboten in P2 (W4); ab P8 Admins (ADM-03) | ROL-04, ADM-03, #91 | geplant (#90) |
| PR-02 | Jede Person, auch Admins | Einträge im Protokoll der Rollenänderungen | ändern, löschen | verboten, im Programm und in der Datenbank; Einträge entstehen nur beim Vergeben und Entfernen von Rollen | BER-02, ROL-04, #91 | gebaut: erlaubt `tests/test_rollen_protokoll.py::test_jede_rolle_kommt_ins_protokoll`; verboten `tests/test_rollen_protokoll.py::test_eintrag_laesst_sich_im_programm_nicht_aendern_oder_loeschen`, `tests/test_rollen_protokoll.py::test_sammelaenderungen_scheitern_an_der_datenbank`, `tests/test_rollen_protokoll.py::test_aendern_per_sql_scheitert_an_der_datenbank` |
| PR-03 | Jede Person mit Konto, auch Admins und Verbandsleitung | Protokoll der Strukturänderungen | ansehen im Tool | verboten in P2 (W4); ab P8 Admins (ADM-03) | ORG-06, ADM-03, #131 | geplant (#90) |
| PR-04 | Jede Person, auch Admins | Einträge im Protokoll der Strukturänderungen | ändern, löschen | verboten, im Programm und in der Datenbank; Einträge entstehen nur beim Anlegen und Ändern von Einheiten | BER-02, ORG-06, #131 | gebaut: erlaubt `tests/test_einheiten_protokoll.py::test_gruppe_umbenennen`; verboten `tests/test_einheiten_protokoll.py::test_eintrag_laesst_sich_im_programm_nicht_aendern_oder_loeschen`, `tests/test_einheiten_protokoll.py::test_sammelaenderungen_scheitern_an_der_datenbank`, `tests/test_einheiten_protokoll.py::test_aendern_per_sql_scheitert_an_der_datenbank` |
| PR-05 | Jede Person mit Konto, auch Admins und Verbandsleitung | Protokoll der Admin-Zugriffe | ansehen im Tool | verboten in P2 (W4); ab P8 Admins und Verbandsleitung (ADM-03, ROL-03) | ADM-03, ROL-03, #92 | geplant (#92) |
| PR-06 | Jede Person, auch Admins | Einträge im Protokoll der Admin-Zugriffe | ändern, löschen | verboten, im Programm und in der Datenbank | BER-02, #92 | geplant (#92) |

## Technische Daten des Logins

Tabellen, die die Bausteine für Login und Sitzung selbst anlegen. Was Leitungen von Personen mit Konto sehen, regelt allein der Abschnitt „Personen mit Konto“.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| TD-01 | Jede Person mit Konto, auch Admins (auch im Support-Zugang) | Sitzungen, Verknüpfung mit dem DPV-Konto samt dem, was Keycloak beim Login mitschickt, Mail-Liste des Login-Bausteins, Zugang zum Keycloak, Djangos Berechtigungen und Tabellenverzeichnis | ansehen, ändern im Tool | verboten; nur der Login selbst schreibt sie | Entscheidung vom 23.10.2026 (#87) | geplant (#90) |

## Tabellen in der Datenbank

Jede Tabelle der Datenbank steht hier mit dem Abschnitt, der ihre Rechte regelt. Ein Test (`tests/test_rechtematrix.py`) wird rot, wenn eine fehlt. Verbindungstabellen, die Django selbst zu einer Tabelle anlegt, gehören zu dieser Tabelle.

| Tabelle | Inhalt | Abschnitt |
| --- | --- | --- |
| `accounts.User` | Konten: Vorname, Nachname, Benutzername, Mail | Eigenes Profil; Personen mit Konto |
| `units.Unit` | Einheiten | Einheiten |
| `roles.Role` | Rollen und Mitgliedschaften | Leitungen und Rollen; Personen mit Konto; Support-Zugang der Admins (Rolle Admin) |
| `roles.RoleChange` | Protokoll der Rollenänderungen | Protokolle |
| `units.UnitChange` | Protokoll der Strukturänderungen | Protokolle |
| `sessions.Session` | Sitzungen | Technische Daten des Logins |
| `socialaccount.SocialAccount` | Verknüpfung mit dem DPV-Konto und was Keycloak beim Login mitschickt | Technische Daten des Logins |
| `socialaccount.SocialApp` | Zugang zum Keycloak | Technische Daten des Logins |
| `socialaccount.SocialToken` | Schlüssel aus dem Login; das Tool speichert keine | Technische Daten des Logins |
| `account.EmailAddress` | Mail-Liste des Login-Bausteins | Technische Daten des Logins |
| `account.EmailConfirmation` | Mail-Bestätigungen des Login-Bausteins; ungenutzt, der Login läuft nur über Keycloak | Technische Daten des Logins |
| `auth.Group` | Djangos Berechtigungsgruppen; ungenutzt, Rechte entstehen nur aus Rollen | Technische Daten des Logins |
| `auth.Permission` | Djangos Liste von Berechtigungen; ungenutzt | Technische Daten des Logins |
| `contenttypes.ContentType` | Djangos Verzeichnis der Tabellen | Technische Daten des Logins |
