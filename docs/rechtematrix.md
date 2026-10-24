# Rechtematrix

Wer im Tool welche Daten sehen und was damit tun darf, in Alltagssprache. Die Matrix ist das Prüfwerkzeug für die Rechte (Entscheidung 4 vom 20.10.2026): Sie lässt sich gegen `docs/anforderungen.md` lesen, ohne Code zu lesen. Sie wird dauerhaft fortgeschrieben; wer neue Daten ins Tool bringt, ergänzt im selben Pull Request ihre Zeilen (`CONTRIBUTING.md`, Abschnitt 4).

Erster Entwurf für P2 vom 23.10.2026 (#87), korrigiert am 24.10.2026 nach dem externen Review (#136, Protokolle Teil 1 bis 3 und Nachtrag). Spätere Phasen ergänzen ihre Zeilen in ihren eigenen Issues. Den Umbau ins kompakte Format (Rollen als Spalten) plant #139.

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

**Grundregel:** Was hier nicht ausdrücklich erlaubt ist, ist verboten (`CONTRIBUTING.md`, Abschnitt 4). Hat eine Person mehrere Rollen, darf sie alles, was eine davon erlaubt (#90). Rechte an Personen und Einheiten entstehen nur aus Rollen und Mitgliedschaften im Tool, nie aus Keycloak und nie daraus, wer etwas angelegt hat (#89). Ausnahmen: Eigene Rechte haben die Veranstaltungsleitung (wer eine Veranstaltung anlegt, leitet sie, TEAM-01) und die Ansprechperson einer Anmeldung (#90). Rechte werden bei jedem Klick neu berechnet; wer eine Rolle verliert, verliert das Recht beim nächsten Klick (#90). Niemand gibt sich selbst eine Rolle; die eigene Rolle niederlegen darf jede Person (ROL-02).

**Spalten:**

- **Kennung:** zwei Großbuchstaben, ein Bindestrich und eine zweistellige Nummer, z. B. `VP-02`. Tests nennen die Kennung ihrer Zeile.
- **Wer:** Rolle oder Art des Kontos (Begriffe unten).
- **Daten** und **Aktion:** was genau gesehen oder getan wird.
- **Ergebnis:** erlaubt oder verboten. Verbotene Einträge mit Kennung in der Adresse zeigen „nicht gefunden“ (404) wie ein nicht vorhandener Eintrag; ganze Bereiche ohne Kennung zeigen „kein Zugriff“ (403) (#64).
- **Quelle:** Anforderung aus `docs/anforderungen.md`, Entscheidung aus `docs/entscheidungen.md` oder das Issue, in dem die Regel geklärt wurde.
- **Stand:** „geplant“ mit dem Issue, das die Zeile baut, oder „gebaut“ mit den Tests für den erlaubten und den verbotenen Fall.

Entfällt ein Recht, wird seine Zeile zum Verbot und behält ihre Kennung, weil Issues und Tests sie nennen (RO-12, RO-16, PK-11). Was für P3 schon entschieden ist, steht mit dem Vermerk „ändert sich ab P3 (#136)“ in der Zeile; die neuen Zeilen kommen mit den Daten (Entscheidung vom 23.10.2026, Nr. 2).

**Wer:**

- **Leitung:** Gruppenleitung, Stammesleitung, Ringleitung oder Bundesleitung einer Einheit. Ihr **Bereich** ist die geleitete Einheit mit allen Einheiten darunter; der Bereich einer Gruppenleitung ist nur ihre Gruppe. Im Bereich sieht sie die Personen (BER-01). Was sie dort anlegen, zuordnen und benennen darf, hat je Zeile eine eigene Reichweite; es gibt keine pauschale Vererbung nach unten (#136, Grundsatz 1).
- **Einspringende Leitung:** Hat eine Einheit keine Leitung mit Konto, hat die Leitung der Einheit direkt darüber dort alle Rechte einer Leitung dieser Einheit; fehlt auch sie, die nächsthöhere, höchstens bis zur Bundesleitung, nie die Verbandsleitung (ROL-02). Das wird bei jedem Klick berechnet, nicht als Rolle gespeichert, und endet, sobald eine Leitung mit Konto benannt ist. Eine verwaltete Person mit angezeigter Leitungsrolle zählt nicht als Leitung (VP-16). Für einen Stamm ohne Ring in einem Bund mit Ringen ist die Bundesleitung die Leitung direkt darüber (#136, F2.7). Eine kommissarische Leitung außerhalb des eigenen Leitungspfads ist in #138 vorgemerkt.
- **Mitglied:** Person mit Konto und Mitgliedschaft in einer Einheit, ohne Leitungsrolle.
- **Zuordnung:** Mitgliedschaft in einer Gruppe, einem Stamm, einem Ring oder einem Bund, auch mit Leitungsrolle, oder die Rolle Verbandsleitung oder DPV-Veranstaltungsteam. Admin, Veranstaltungsleitung, Ansprechperson und Verwaltende eines Kreises sind keine Zuordnung (BER-03).
- **Konto ohne Zuordnung:** Person mit Konto ohne Zuordnung (#9, BER-03). Sie pflegt im Tool nur das eigene Profil; ab P3 stellt sie Beitrittsanfragen (#140). Was sie darf, steht nur in dieser Matrix (Entscheidung vom 24.10.2026).
- **Verbandsleitung**, **DPV-Veranstaltungsteam:** Rollen im Verband, ohne Mitgliedschaft (ROL-01).
- **Admin:** technische Rolle (BER-02). Ohne Support-Zugang hat ein Admin keine Rechte einer Leitung (#89); **Admin im Support-Zugang** hat für eine Einheit die Rechte ihrer Leitung (#92).
- **Veranstaltungsleitung:** wer eine Veranstaltung angelegt hat oder hinzugefügt wurde (TEAM-01).
- **Ansprechperson:** wer eine Anmeldung abgegeben hat.
- **Jede Person mit Konto:** alle oben, egal mit welcher Rolle.

**Reichweite:**

- **Kette nach oben:** die eigene Einheit und alle Einheiten darüber bis zum Bund. Gilt für das Sehen von Leitungen (RO-01, RO-02). Ein Mitglied, das direkt im Bund ist, hat nur den Bund auf seiner Kette; ein Mitglied einer Gruppe hat eine andere Gruppe im selben Stamm nicht darauf (#136, B3).
- **Leitungspfad (#89):** wo eine Person Leitung sein darf (ROL-01): im eigenen Stamm einschließlich seiner Gruppen und in den Einheiten darüber; ist sie direkt Mitglied eines Rings oder Bundes, auch in allen Einheiten darunter. Gilt für das Benennen und Zuordnen (RO-10, RO-11, PK-19).

**Verbotszeilen** sagen, was eine Rolle nicht gibt. Hat eine Person zusätzlich eine andere Rolle oder ist sie Veranstaltungsleitung oder Ansprechperson, darf sie, was diese Zeilen erlauben. Gilt ein Verbot für alle, steht „Jede Person mit Konto“. Ausnahmen aus anderen Zeilen nennt die Spalte „Ergebnis“ mit Kennung.

**Kennungen:** Die Buchstaben stehen für den Abschnitt oder einen Teil davon (im Abschnitt „Veranstaltungen und Anmeldungen“: VA und AN).

**Wie die Tests die Zeilen prüfen:** Eine Zeile „erlaubt“ prüft als verbotenen Fall den nächsten Nachbarn, etwa eine andere Einheit oder eine Ebene darunter. Eine Zeile „verboten“ prüft als erlaubten Fall die Gegenprobe, dass der vorgesehene Weg weiter funktioniert. Beides auch über direkte Adressen, htmx-Anfragen und manipulierte Formulare (#90). Nennt eine Zeile mehrere Rollen, Daten oder Aktionen, prüft je Fall ein eigener Test; „gebaut“ heißt: alle Fälle (#136, A17).

**Außerhalb des Tools:** Befehle auf dem Server (Verband und Bünde anlegen und umbenennen, „hat Ringe“ beim Anlegen eines Bundes festlegen und bis zur Seite für Bünde (#107) ausschalten, Admins und die erste Verbandsleitung benennen, im Notfall eine leere Einheit löschen) braucht Zugang zum Server; sie stehen im `README.md` und schreiben ins Protokoll. Die Matrix regelt, was im Tool geht.

## Eigenes Profil

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| EP-01 | Jede Person mit Konto | eigenes Profil: Vorname, Nachname, Benutzername, Mail, Fahrtenname, Mitgliedschaft und Rollen | ansehen („Mein Profil“) | erlaubt | PER-01, ORG-05, #96 | geplant (#96) |
| EP-02 | Jede Person mit Konto, auch Leitungen und Admins | Profil einer anderen Person über „Mein Profil“ (andere Adresse, angehängter Parameter, htmx) | ansehen | verboten; die Seite zeigt immer die angemeldete Person | PER-01, BER-01, #96 | geplant (#96) |
| EP-03 | Jede Person mit Konto | eigener Fahrtenname | eintragen, ändern, löschen | erlaubt | PER-01, #111 | geplant (#111) |
| EP-04 | Alle außer der Person selbst, auch Leitungen und Admins im Support-Zugang | Fahrtenname einer Person mit Konto | ändern | verboten | #111 | geplant (#111) |
| EP-05 | Jede Person mit Konto, auch Leitungen und Admins | Vorname, Nachname, Benutzername und Mail eines Kontos | ändern im Tool | verboten; sie kommen aus dem DPV-Konto, auch wenn sie dort leer sind (Pflichtfelder in Keycloak: Anfrage in #148). Ein Geburtsdatum haben Konten in P2 nicht (#143) | #96, #65, #136 (F2.14) | geplant (#96) |
| EP-06 | Jede Person mit Mitgliedschaft, auch Leitungen | eigene Mitgliedschaft | beenden (austreten), dabei die Ebene wählen, aus der sie austritt | erlaubt, jederzeit. Sie wird Einzelmitglied der Ebene darüber; wer aus dem Bund austritt, hat danach keine Zuordnung. Es enden alle Leitungsrollen in der verlassenen Einheit und den Einheiten darunter sowie alle, die danach nicht mehr auf ihrem Leitungspfad liegen; das Tool zeigt sie vorher und tritt erst nach Bestätigung aus. Bestehende Anmeldungen bleiben (#146) | ROL-01, #65, #136 (F2.4, Nachtrag) | geplant (#65) |
| EP-07 | Jede Person mit Konto | Mitgliedschaft einer anderen Person | über „austreten“ beenden | verboten | #65 | geplant (#65) |
| EP-08 | Jede Person mit Konto, auch Konto ohne Zuordnung | sich selbst einer Einheit zuordnen | über „Aufnehmen“ als Mitglied eintragen | verboten; außer der automatischen Mitgliedschaft beim Einsetzen als Leitung (ROL-01; RO-10, RO-11, RO-15). Ab P3 stellt sie eine Beitrittsanfrage, über die die Leitung entscheidet (#140) | #65, #89, #136 (A4) | geplant (#65) |
| EP-09 | Jede Person mit Konto, auch Leitungen und Admins | Konto, auch das eigene | im Tool anlegen oder löschen | verboten in P2; Konten entstehen nur beim ersten Login (ORG-02); „Profil selbst löschen“ (DSG-09) kommt nach Liste 1 später | ORG-02, DSG-09, #136 (A11) | geplant (#90) |

## Personen mit Konto

Was Leitungen sehen: Name, Fahrtenname, Mail, Organisation und Rollen (#87, Frage 4; #111). Von Leitungen, die man nur über die Ansicht „Leitungen“ sieht (RO-01 bis RO-03, RO-05), sieht man Name, Fahrtenname und Rolle; Mail und weitere Angaben nur, wer die Person nach BER-01 ohnehin sieht (#136, B2). Sichtbarkeit je Profilfeld ist in #137 vorgemerkt; sie wartet auf die Fragen an die Datenschutzperson (#149). Personen ohne Konto stehen unter „Verwaltete Personen“; die Liste „Personen“ einer Einheit zeigt beide (#117).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| PK-01 | Gruppenleitung | Mitglieder ihrer Gruppe | ansehen | erlaubt | BER-01, #87 | geplant (#65) |
| PK-02 | Stammesleitung | Mitglieder ihres Stammes und seiner Gruppen | ansehen | erlaubt | BER-01, #87 | geplant (#65) |
| PK-03 | Ringleitung, Bundesleitung | Mitglieder ihres Rings bzw. Bundes und aller Einheiten darunter | ansehen | erlaubt | BER-01, #87 | geplant (#65) |
| PK-04 | Leitung | Personen mit Konto außerhalb ihres Bereichs, z. B. Stammesleitung der Zugvögel bei Walhall, Gruppenleitung bei einer anderen Gruppe ihres Stammes | ansehen | verboten, „nicht gefunden“; außer Name, Fahrtenname und Rolle der Leitungen auf ihrer Kette nach oben (RO-01) und in ihrem Bereich (RO-03). Die Treffer aus PK-13 zeigen nur Name und Fahrtenname | BER-01, #136 (A2, B2) | geplant (#65) |
| PK-05 | Mitglied | andere Personen mit Konto, auch in der eigenen Einheit | ansehen | verboten; außer Name, Fahrtenname und Rolle der Leitungen auf seiner Kette nach oben (RO-02). Mehr Sichtbarkeit nur nach eigener Freigabe ist in #137 vorgemerkt | BER-01; #87, Frage 5; #136 (B2, Grundsatz 3a) | geplant (#65) |
| PK-06 | Konto ohne Zuordnung | andere Personen mit Konto | ansehen | verboten | BER-01, #9 | geplant (#9) |
| PK-07 | Verbandsleitung, DPV-Veranstaltungsteam | Personen mit Konto in Bünden, Ringen, Stämmen und Gruppen | ansehen | verboten; außer: Verbandsleitung sieht Name, Fahrtenname und Rolle der Bundesleitungen (RO-05) und findet Konten über die genaue Mail oder den Benutzernamen (PK-13) | ROL-03, ROL-05, #94, #136 (B2) | geplant (#94) |
| PK-08 | Admin ohne Support-Zugang | Personen mit Konto | ansehen | verboten | BER-02, #92 | geplant (#92) |
| PK-09 | Leitung | Personen mit Konto in ihrem Bereich | suchen nach Vorname, Nachname, Fahrtenname | erlaubt | #93, #111 | geplant (#93) |
| PK-10 | Leitung | Personen mit Konto außerhalb ihres Bereichs | suchen nach Namen | verboten, kein Treffer | #93 | geplant (#93) |
| PK-11 | Bundesleitung | Konten ohne Zuordnung im ganzen Tool | suchen nach Namen | verboten, kein Treffer; die Namenssuche ist entfallen. Neue Konten findet sie über die genaue Mail oder den Benutzernamen (PK-13), ab P3 auch über Beitrittsanfragen (#140) | #93, #136 (C2) | geplant (#93) |
| PK-12 | Gruppenleitung, Stammesleitung, Ringleitung, Verbandsleitung | Konten ohne Zuordnung | suchen nach Namen | verboten, kein Treffer; wie für die Bundesleitung (PK-11) | #93, #94, #136 (C2) | geplant (#93) |
| PK-13 | Leitung, Verbandsleitung | jedes Konto, das sich schon einmal angemeldet hat; der Treffer zeigt Name und Fahrtenname und ob es schon woanders Mitglied ist, nie die Einheit | finden über die genaue Mail oder den genauen Benutzernamen | erlaubt, höchstens 20 Suchen je Person und Stunde (PK-24). Suchen ohne Treffer und Suchen mit einem Treffer außerhalb des eigenen Bereichs kommen ins Protokoll der Kontosuchen (ADM-03), sobald es gebaut ist (#144, spätestens P6) | BER-01, #93, #94, #136 (C3, Frage 15) | geplant (#93) |
| PK-14 | Mitglied, DPV-Veranstaltungsteam, Konto ohne Zuordnung, Admin ohne Support-Zugang | Konten | suchen oder finden | verboten | #93, ROL-05 | geplant (#93) |
| PK-15 | Jede Person mit Konto | alle Konten | durchblättern | verboten; eine Liste aller Konten gibt es nicht | #93 | geplant (#93) |
| PK-16 | Leitung, Verbandsleitung | Einheit einer gefundenen Person außerhalb des eigenen Bereichs, auch in Meldungen | erfahren | verboten; Meldungen nennen die Einheit nicht | BER-01, #93, #94, #65 | geplant (#93) |
| PK-17 | Leitung | Person mit Konto ohne Mitgliedschaft | als Mitglied aufnehmen in die eigene Einheit | erlaubt; als einspringende Leitung auch in der Einheit ohne Leitung. Ab P3 auch über Beitrittsanfragen (#140) | #65, #136 (Grundsatz 1, Frage 2) | geplant (#65) |
| PK-18 | Leitung | Person, die außerhalb des Bereichs Mitglied ist | aufnehmen | verboten; Meldung ohne Einheit. Ab P3 wechselt sie per Beitrittsanfrage (#140) | #65, #136 (Frage 5) | geplant (#65) |
| PK-19 | Stammesleitung, Ringleitung, Bundesleitung | Mitglieder der eigenen Einheit | in eine Einheit direkt darunter verschieben | erlaubt, wenn danach alle Leitungsrollen der Person auf ihrem Leitungspfad liegen (#89, sonst PK-25); als einspringende Leitung auch in der Einheit ohne Leitung | #65, #89, #136 (Grundsatz 1, A5) | geplant (#65) |
| PK-20 | Leitung | Mitglieder, die nicht ihrer eigenen Einheit angehören; Ziele, die nicht direkt unter der eigenen Einheit liegen, z. B. Bundesleitung ein Mitglied eines Stammes in eine Gruppe | verschieben | verboten; außer als einspringende Leitung | #65, #136 (Grundsatz 1) | geplant (#65) |
| PK-21 | Leitung der eigenen Einheit der Person; fehlt sie, die einspringende Leitung | Mitglied dieser Einheit | entfernen (austragen) | erlaubt. Die Person wird Einzelmitglied der Ebene darüber; wer aus dem Bund entfernt wird, hat danach keine Zuordnung. Es enden alle Leitungsrollen in der verlassenen Einheit und den Einheiten darunter sowie alle, die danach nicht mehr auf ihrem Leitungspfad liegen; das Tool zeigt sie vorher und führt erst nach Bestätigung aus. Bestehende Anmeldungen bleiben (#146) | ROL-01, #65, #136 (Frage 1, F2.4, Nachtrag) | geplant (#65) |
| PK-22 | Leitung | Mitglieder, die nicht ihrer eigenen Einheit angehören, auch in Einheiten darunter, z. B. Stammesleitung bei einem Mitglied einer Gruppe ihres Stammes | entfernen | verboten; außer als einspringende Leitung | #65, #136 (Frage 1) | geplant (#65) |
| PK-23 | Alle außer Leitungen (PK-17, PK-19, PK-21) und Admins im Support-Zugang (SZ-03): Verbandsleitung, DPV-Veranstaltungsteam, Mitglied, Konto ohne Zuordnung, Admin ohne Support-Zugang | Mitgliedschaften anderer | aufnehmen, verschieben, entfernen | verboten | #65, #136 (A9) | geplant (#65) |
| PK-24 | Leitung, Verbandsleitung | mehr als 20 Suchen über die genaue Mail oder den Benutzernamen je Person und Stunde, beide zusammengezählt | finden (PK-13) | verboten; Meldung „Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in einer Stunde noch einmal.“ | #93, #136 (Frage 15) | geplant (#93) |
| PK-25 | Leitung, auch die einspringende | Mitglied, von dessen Leitungsrollen nach dem Verschieben eine nicht mehr auf seinem Leitungspfad läge | verschieben | verboten; das Tool nennt die Rolle und weist darauf hin, dass sie zuerst beendet werden kann (ROL-02). Leitungsrollen enden nur, wenn die Person selbst geht oder ausdrücklich entfernt wird; das Löschen einer Einheit und das Ausschalten von „hat Ringe“ (ORG-06, EH-21, EH-25) bleiben davon unberührt | #89, #136; Entscheidung vom 24.10.2026 | geplant (#65) |
| PK-26 | Leitung | Person mit Konto ohne Mitgliedschaft | als Mitglied aufnehmen in eine Einheit unter der eigenen, z. B. Stammesleitung in eine Gruppe ihres Stammes | verboten; außer als einspringende Leitung. Die automatische Mitgliedschaft beim Benennen als Leitung bleibt (ROL-01; RO-10) | #65, #136 (Grundsatz 1) | geplant (#65) |

## Verwaltete Personen

Verwaltete Personen sind Profile ohne Konto (PER-02). Angaben in P2: Vorname, Nachname, Geburtsdatum, Fahrtenname (#117). Gesundheitsangaben gibt es im Profil verwalteter Personen nie (FRM-04, siehe GA-05). Personen, die nur jemand privat speichert, sind keine verwalteten Personen, sondern Einträge im persönlichen Adressbuch (PER-04, vorgemerkt in #142).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| VP-01 | Leitung | verwaltete Person in der eigenen Einheit | anlegen | erlaubt; als einspringende Leitung auch in der Einheit ohne Leitung | PER-02, #117, #136 (Grundsatz 1) | geplant (#117) |
| VP-02 | Leitung | verwaltete Personen ihres Bereichs | ansehen (auch in der Liste „Personen“ und ihrer Suche), bearbeiten | erlaubt | BER-01, PER-02, #136 (A16) | geplant (#117) |
| VP-03 | Leitung | verwaltete Personen außerhalb ihres Bereichs, z. B. Stammesleitung der Zugvögel bei Walhall, Gruppenleitung bei einer anderen Gruppe | anlegen, ansehen, suchen, bearbeiten | verboten, „nicht gefunden“; in der Suche kein Treffer | BER-01, #136 (A16) | geplant (#117) |
| VP-04 | Leitung, die entfernt wurde | verwaltete Personen der früheren Einheit, auch im schon geöffneten Formular | ansehen, bearbeiten | verboten ab dem nächsten Klick | PER-02, #90 | geplant (#117) |
| VP-05 | Wer eine verwaltete Person angelegt hat, ohne Leitungsrolle dort | diese Person | ansehen, bearbeiten | verboten | PER-02, #89 | geplant (#117) |
| VP-06 | Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | verwaltete Personen | anlegen, ansehen, bearbeiten | verboten | BER-01, ROL-03, ROL-05, #92 | geplant (#117) |
| VP-07 | Stammesleitung, Ringleitung, Bundesleitung | verwaltete Person der eigenen Einheit | in eine Einheit direkt darunter verschieben | erlaubt; als einspringende Leitung auch in der Einheit ohne Leitung | PER-02, #118, #136 (Grundsatz 1) | geplant (#118) |
| VP-08 | Gruppenleitung; jede Leitung bei verwalteten Personen, die nicht ihrer eigenen Einheit angehören, oder mit einem Ziel, das nicht direkt unter der eigenen Einheit liegt | verwaltete Person | verschieben | verboten; außer als einspringende Leitung | PER-02, #118, #136 (Grundsatz 1) | geplant (#118) |
| VP-09 | Leitung der eigenen Einheit der Person; fehlt sie, die einspringende Leitung | verwaltete Person dieser Einheit | löschen, endgültig | erlaubt | #118, #136 (Grundsatz 1) | geplant (#118) |
| VP-10 | Alle außer VP-09: Leitungen darüber, wenn die Einheit eine Leitung mit Konto hat; Leitungen außerhalb, Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | verwaltete Person | löschen | verboten | #118, #136 | geplant (#118) |
| VP-11 | Leitung beim Anlegen | Bestätigung der Einwilligung (welches Konto wann bestätigt hat) | setzen, nur beim Anlegen und nur im eigenen Namen | erlaubt | DSG-02, #98 | geplant (#98) |
| VP-12 | Jede Person mit Konto, auch Admins im Support-Zugang | Bestätigung der Einwilligung | ansehen im Tool | verboten in P2 | #98 | geplant (#98) |
| VP-13 | Jede Person mit Konto, auch Admins im Support-Zugang | Bestätigung der Einwilligung | nachträglich ändern oder für ein anderes Konto setzen | verboten | #98 | geplant (#98) |
| VP-14 | Wer Leitungen dieser Einheit benennen darf (RO-10, RO-11): die Bundesleitung im ganzen Bund, die Ringleitung in ihrem Ring, die Stammesleitung in den Gruppen ihres Stammes, Leitungen derselben Einheit; die einspringende Leitung; nicht die Verbandsleitung (VP-15) | angezeigte Leitungsrolle einer verwalteten Person („nur Anzeige“) | eintragen, entfernen | erlaubt; die Anzeige gibt keine Rechte (VP-16), die Einwilligung nach #98 und #99 gilt unabhängig davon, wer einträgt | PER-07, ROL-02, #99, #136 (A13); Entscheidung vom 24.10.2026 | geplant (#99) |
| VP-15 | Alle anderen: Leitungen bei Einheiten außerhalb ihres Bereichs oder über ihrer eigenen, Mitglied, Konto ohne Zuordnung, Verbandsleitung (sie sieht verwaltete Personen nicht, VP-06), DPV-Veranstaltungsteam, Admin ohne Support-Zugang | angezeigte Leitungsrolle | eintragen, entfernen | verboten | ROL-03, #99, #136 | geplant (#99) |
| VP-16 | Jede Person | Rechte einer Leitung über eine angezeigte Leitungsrolle | bekommen | verboten; die Anzeige gibt niemandem Rechte und zählt nicht als Leitung | PER-07, #99 | geplant (#99) |
| VP-17 | Leitung | verwaltete Person in einer Einheit unter der eigenen, z. B. Stammesleitung in einer Gruppe ihres Stammes | anlegen | verboten; außer als einspringende Leitung | PER-02, #117, #136 (Grundsatz 1) | geplant (#117) |

## Einheiten

Einheiten sind Verband, Bünde, Ringe, Stämme und Gruppen (ORG-01); im Tool heißen sie „Organisation“ (#96).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| EH-01 | Leitung | Namen aller Einheiten des eigenen Bundes | ansehen | erlaubt | #87, Frage 5 | geplant (#93) |
| EH-02 | Mitglied | Namen aller Einheiten des eigenen Bundes | ansehen | erlaubt; ändert sich ab P3 (#136): dazu, ob die Einheit gerade eine Leitung hat, ohne Namen (#134) | #87, Frage 5; #136 (Frage 4) | geplant (#134), noch keine Seite in P2 |
| EH-03 | Mitglied, Leitung (ohne Rolle im Verband) | Namen von Einheiten anderer Bünde | ansehen | verboten; ändert sich ab P3 (#136): die Namen der Bünde, Ringe und Stämme, ohne Gruppen und ohne Leitungsstatus, für eine Beitrittsanfrage (#140) | #87, Frage 5; #136 (Frage 3) | geplant (#93) |
| EH-04 | Verbandsleitung, DPV-Veranstaltungsteam | Namen aller Bünde | ansehen | erlaubt | #87, Frage 5; #94; Entscheidung vom 23.10.2026 | geplant: Verbandsleitung mit #94; DPV-Veranstaltungsteam mit #134, noch keine Seite in P2 |
| EH-05 | Verbandsleitung, DPV-Veranstaltungsteam (ohne weitere Rolle) | Namen von Ringen, Stämmen und Gruppen | ansehen | verboten; nicht ausdrücklich erlaubt. Ändert sich ab P3 (#136): die Namen der Ringe und Stämme, ohne Gruppen (#140) | #87, Frage 5; #136 (Frage 3) | geplant (#94) |
| EH-06 | Admin | Namen aller Einheiten, um einen Support-Zugang zu starten | ansehen | erlaubt | #92 | geplant (#92) |
| EH-07 | Konto ohne Zuordnung | Einheiten und ihre Namen | ansehen | verboten; ändert sich ab P3 (#136): die Namen der Bünde, Ringe und Stämme, ohne Gruppen, ohne Leitungsstatus und ohne Personen, für eine Beitrittsanfrage (#140) | #9, #87, #136 (Frage 3) | geplant (#9) |
| EH-08 | Leitung, Verbandsleitung, Admin | Navigationspunkt „Organisation“ (Leitung: die geleiteten Einheiten mit denen darunter; Verbandsleitung: die Bünde; Admin: Start des Support-Zugangs) | sehen und öffnen | erlaubt | #93, #94, #92 | geplant (#93) |
| EH-09 | Mitglied, Konto ohne Zuordnung, DPV-Veranstaltungsteam | Navigationspunkt „Organisation“ | sehen und öffnen | verboten; der Punkt fehlt, die Adresse zeigt „kein Zugriff“ | #93, #64 | geplant (#93) |
| EH-10 | Bundesleitung | Ringe (nur in Bünden mit Ringen), Stämme (nur in Bünden ohne Ringe) und Gruppen im ganzen eigenen Bund | anlegen | erlaubt | ORG-06, #95, #136 (Grundsatz 1) | geplant (#95) |
| EH-11 | Ringleitung | Stämme und Gruppen im eigenen Ring | anlegen | erlaubt | ORG-06, #95, #136 (Grundsatz 1) | geplant (#95) |
| EH-12 | Stammesleitung | Gruppen im eigenen Stamm | anlegen | erlaubt | ORG-06, #95 | geplant (#95) |
| EH-13 | Gruppenleitung; Leitungen bei Einheiten außerhalb ihres Bereichs; Ring- und Stammesleitung Einheiten der eigenen Ebene; Bundesleitung Stämme in einem Bund mit Ringen (außer beim Einspringen für einen Ring, EH-18); Verbandsleitung, DPV-Veranstaltungsteam, Mitglied, Konto ohne Zuordnung, Admin ohne Support-Zugang | Ringe, Stämme, Gruppen | anlegen | verboten | ORG-06, #95, #136 (Grundsatz 1, A10) | geplant (#95) |
| EH-14 | Jede Leitung, auch die Bundesleitung für ihren Bund | Name der eigenen Einheit und aller Einheiten darunter | umbenennen | erlaubt | ORG-06, #95, #136 (F2.8, A10) | geplant (#95) |
| EH-15 | Leitungen bei Einheiten außerhalb ihres Bereichs, auch darüber; Mitglied, Konto ohne Zuordnung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang; Verbandsleitung bei Ringen, Stämmen und Gruppen | Name einer Einheit | umbenennen | verboten; außer beim Einspringen (EH-18) | ORG-06, #95, #136 | geplant (#95) |
| EH-16 | Bundesleitung | Stamm ihres Bundes | einem Ring zuordnen oder in einen anderen Ring desselben Bundes verschieben | erlaubt | #88, #95 | geplant (#95) |
| EH-17 | Alle außer der Bundesleitung des Bundes (EH-16): Ringleitung, Stammesleitung, Leitungen anderer Bünde, Verbandsleitung, DPV-Veranstaltungsteam, Mitglied, Konto ohne Zuordnung, Admin ohne Support-Zugang | Stamm | einem Ring zuordnen oder Ring wechseln | verboten | #95, #136 (A9) | geplant (#95) |
| EH-18 | Einspringende Leitung (siehe „So liest man die Matrix“) | Einheit ohne Leitung mit Konto | alles, was eine Leitung dieser Einheit darf: Einheiten darunter anlegen und umbenennen, Mitglieder und verwaltete Personen aufnehmen, verschieben und entfernen, verwaltete Personen löschen, ab P3 Beitrittsanfragen entscheiden (#140) | erlaubt; endet, sobald wieder eine Leitung mit Konto benannt ist. Beispiel: Hat die Sippe Falken keine Gruppenleitung, nimmt die Stammesleitung von Walhall dort Mitglieder auf und entfernt sie | ROL-02, #95, #99, #136 (Grundsatz 4, A10) | geplant (#95, #65, #117, #118) |
| EH-19 | Leitung darüber, wenn die Einheit eine Leitung mit Konto hat | Rechte, die nur die Leitung der Einheit selbst hat, z. B. Mitglieder der Einheit aufnehmen, verschieben und entfernen, verwaltete Personen dort anlegen, verschieben und löschen, als Bundesleitung Stämme in einem Ring anlegen; ab P3 Beitrittsanfragen an die Einheit entscheiden | ausüben | verboten | ROL-02, #95, #136 (Grundsatz 4, A10) | geplant (#95, #65, #117, #118) |
| EH-20 | Jede Person mit Konto, auch Verbandsleitung, Bundesleitung und Admins | Verband; Bünde, soweit EH-14 und EH-22 es nicht erlauben | anlegen, umbenennen | verboten im Tool; den Verband und die Bünde zum Start legen Admins per Befehl auf dem Server an (ORG-01) | ORG-01, #88, #95, #107, #136 (F2.8) | geplant (#95) |
| EH-21 | Jede Person mit Konto, auch Admins | Einheit | löschen | verboten im Tool, bis #108 das Löschen nach ORG-06 baut (nur Einheiten ohne Einheiten darunter); bis dahin gibt es keinen Löschknopf (W5) | ORG-06, #88, #95, #108 | geplant (#95) |
| EH-22 | Verbandsleitung | Bünde | anlegen und dabei „hat Ringe“ festlegen; umbenennen | erlaubt ab der Seite für Bünde (#107); bis dahin legt ein Admin auf Bitte der Verbandsleitung per Befehl auf dem Server an und benennt um (EH-20) | ROL-03, ORG-01, #136 (F2.8) | geplant (#107) |
| EH-23 | Bundesleitung | Schalter „hat Ringe“ des eigenen Bundes | einschalten | erlaubt | ORG-06, #95, #136 (F2.8) | geplant (#95) |
| EH-24 | Alle außer der Bundesleitung (EH-23), dem Admin im Support-Zugang für den Bund (SZ-03) und der Verbandsleitung beim Anlegen eines Bundes (EH-22) | Schalter „hat Ringe“ | einschalten im Tool | verboten | ORG-06, #136 (F2.8) | geplant (#95) |
| EH-25 | Jede Person mit Konto, auch Bundesleitung und Admins | Schalter „hat Ringe“ | ausschalten im Tool | verboten bis zur Seite für Bünde (#107). Bis dahin schaltet ein Admin auf Bitte der Bundesleitung per Befehl aus, in einem Schritt: Alle Stämme werden aus ihren Ringen genommen, die Ringe gelöscht (ihre Mitglieder kommen zum Bund, die Ringleitungen enden). Der Befehl zeigt vorher, was passiert, mit den betroffenen Personen und Rollen, führt erst nach Bestätigung aus und schreibt ins Protokoll der Strukturänderungen, wer ihn ausgeführt hat und auf wessen Bitte | ORG-06, #95, #136 (Frage 28) | geplant (#95) |
| EH-26 | Jede Person mit Konto, auch Bundesleitung und Admins | Stamm in einem Bund mit Ringen | aus seinem Ring nehmen | verboten; „Ring ist Pflicht“, solange der Bund Ringe hat, außer beim Ausschalten von „hat Ringe“ (EH-25) | #88, #136 (Frage 28) | geplant (#95) |
| EH-27 | Verbandsleitung | Bund ohne Bundesleitung mit Konto und die Einheiten darunter | einspringen | verboten; sie springt nie ein. Ab P3 bleiben Beitrittsanfragen an einen solchen Bund offen (#140) | ROL-02, ROL-03, #136 (Grundsatz 4) | geplant (#95) |

## Leitungen und Rollen

Rollen nach ROL-01; die Mitgliedschaft steht unter „Personen mit Konto“, die Rolle Admin unter „Support-Zugang der Admins“.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| RO-01 | Leitung | Leitungen der Einheiten auf ihrer Kette nach oben: Name, Fahrtenname und Rolle | ansehen | erlaubt; Mail und weitere Angaben nur, wenn sie die Person nach BER-01 ohnehin sieht | #87, Frage 5; #136 (A1, B2) | geplant (#93) |
| RO-02 | Mitglied | Leitungen der Einheiten auf seiner Kette nach oben: Name, Fahrtenname und Rolle; direkt im Bund nur die Bundesleitung | ansehen | erlaubt | #87, Frage 5; #136 (B2, B3) | geplant (#134), noch keine Seite in P2 |
| RO-03 | Leitung | Leitungen aller Einheiten in ihrem Bereich (Ansicht „Leitungen“): Name, Fahrtenname und Rolle | ansehen | erlaubt; Mail und weitere Angaben nur, wenn sie die Person nach BER-01 ohnehin sieht. Beispiel: Berta ist Mitglied des Bundes und Stammesleitung von Walhall; Erika, die zweite Stammesleitung von Walhall, sieht Bertas Mail nicht | #87, Frage 5; #93; #136 (B2) | geplant (#93) |
| RO-04 | Mitglied, Leitung | Leitungen von Einheiten, die weder auf der Kette nach oben noch im eigenen Bereich liegen, z. B. Nachbarstamm, anderer Bund; für ein Mitglied einer Gruppe eine andere Gruppe im selben Stamm | ansehen | verboten | #87, Frage 5; #136 (B3) | geplant (#93) |
| RO-05 | Verbandsleitung | Bundesleitungen, Verbandsleitungen, Mitglieder des DPV-Veranstaltungsteams: Name, Fahrtenname und Rolle | ansehen | erlaubt | BER-01; #87, Frage 5; #94; #136 (B2) | geplant (#94) |
| RO-06 | Verbandsleitung (ohne weitere Rolle) | Leitungen von Ringen, Stämmen und Gruppen | ansehen | verboten | ROL-03, #94 | geplant (#94) |
| RO-07 | DPV-Veranstaltungsteam (ohne weitere Rolle) | Leitungen jeder Ebene, auch Bundesleitungen | ansehen | verboten | ROL-05, Entscheidung vom 23.10.2026 | geplant (#94) |
| RO-08 | Konto ohne Zuordnung, Admin ohne Support-Zugang | Leitungen | ansehen | verboten | BER-01, #9, #87, #136 (A9) | geplant (#9) |
| RO-09 | Wer die Leitungen einer Einheit sehen darf (RO-01 bis RO-03, RO-05), auch Mitglieder | angezeigte Leitungsrollen verwalteter Personen (Name bzw. Fahrtenname und Rolle, „ohne Konto, nur Anzeige“) | ansehen | erlaubt | BER-01, #99, #136 (BER-01, Grund 3) | geplant (#99) |
| RO-10 | Leitung | Leitungen aller Einheiten unter ihrer eigenen: die Bundesleitung im ganzen Bund, die Ringleitung in ihrem Ring, die Stammesleitung in den Gruppen ihres Stammes | benennen, entfernen | erlaubt; benennen nur, wenn die Person die Rolle danach auf ihrem Leitungspfad hat (ROL-01, #89) | ROL-02, #93, #136 (Grundsatz 1, A5) | geplant (#93) |
| RO-11 | Leitung | weitere Leitungen derselben Einheit, auch gegenseitig, nicht sich selbst | benennen, entfernen | erlaubt; benennen nur, wenn die Person die Rolle danach auf ihrem Leitungspfad hat (ROL-01, #89) | ROL-02, #93, #136 (Grundsatz 2, A5) | geplant (#93) |
| RO-12 | Jede Person mit Konto, auch Leitungen, Verbandsleitung und Admins | sich selbst eine Rolle, z. B. als Leitung einer Einheit unter der eigenen | vergeben im Tool | verboten; eine andere Leitung derselben Einheit oder darüber benennt sie (RO-10, RO-11). Die eigene Rolle niederlegen geht (RO-20) | ROL-02, #93, #136 (Grundsatz 2) | geplant (#93) |
| RO-13 | Leitungen bei Einheiten außerhalb ihres Bereichs, z. B. Stammesleitung der Zugvögel bei Walhall, und bei Einheiten über ihrer eigenen; beim Benennen jede Leitung, wenn die Rolle danach nicht auf dem Leitungspfad der Person läge, z. B. bei einer Person aus einem anderen Bund | Leitungen | benennen, entfernen | verboten | ROL-01, ROL-02, #89, #93, #136 (Grundsatz 1, A5) | geplant (#93) |
| RO-14 | Alle ohne Recht aus RO-10, RO-11, RO-15 oder SZ-03: Mitglied, Konto ohne Zuordnung, DPV-Veranstaltungsteam, Admin ohne Support-Zugang | Rollen anderer | vergeben, entfernen | verboten im Tool; Admins und die erste Verbandsleitung benennt ein Admin per Befehl auf dem Server (RO-19, ROL-03) | ROL-05, #93, #94, #136 (A9) | geplant (#93) |
| RO-15 | Verbandsleitung | Bundesleitungen, weitere Verbandsleitungen (auch gegenseitig, nicht sich selbst), Mitglieder des DPV-Veranstaltungsteams | benennen, entfernen | erlaubt; eine Bundesleitung nur, wenn die Person sie danach auf ihrem Leitungspfad hat (ROL-01, #89) | ROL-03, #94, #136 (Grundsatz 2) | geplant (#94) |
| RO-16 | Verbandsleitung | sich selbst als Bundesleitung | einsetzen | verboten (RO-12). Benennt eine andere Verbandsleitung sie zur Bundesleitung, hat sie im Bund die Rechte der Bundesleitung, nicht als Verbandsleitung; die Benennung steht im Protokoll der Rollenänderungen | ROL-02, ROL-03, #94, #136 (Grundsatz 2, C1) | geplant (#94) |
| RO-17 | Verbandsleitung (ohne weitere Rolle) | Leitungen von Ringen, Stämmen und Gruppen | benennen, entfernen | verboten | ROL-03, #94 | geplant (#94) |
| RO-18 | Alle außer der Verbandsleitung | Verbandsleitungen, Mitglieder des DPV-Veranstaltungsteams | benennen, entfernen | verboten im Tool | ROL-03, #94 | geplant (#94) |
| RO-19 | Jede Person mit Konto, auch Admins | Rolle Admin | vergeben, entfernen | verboten im Tool; bis ADM-01 (P6) nur per Befehl auf dem Server | ADM-01, #89 | geplant (#90) |
| RO-20 | Jede Person mit einer Leitungsrolle oder einer Rolle im Verband (Verbandsleitung, DPV-Veranstaltungsteam) | eigene Rolle | niederlegen | erlaubt; die Mitgliedschaft beendet man durch Austritt (EP-06). Ist sie die letzte Leitung einer Gruppe, eines Stammes oder Rings, springt die Leitung darüber ein (EH-18); für einen Bund springt niemand ein (EH-27). Die Rolle Admin regelt RO-19 | ROL-02, #136 (Grundsatz 2) | geplant (#93, #94) |

## Veranstaltungen und Anmeldungen

In P2 als Probe: Veranstaltungen mit Name, Beginn und Ende (#100); Anmeldungen entstehen nur über den Testdaten-Befehl (#101, #103). Teilnahmekreise und BER-07 kommen in P3. Alles rund um Veranstaltungen braucht eine Zuordnung (BER-03, #136, Grundsatz 5); in P2 gilt davon nur das Anlegen (VA-01, VA-05). Ab P3 wird auch Veranstaltungsleitung oder Mitglied eines Veranstaltungsteams nur, wer eine Zuordnung hat. Was mit Anmeldungen und Veranstaltungen geschieht, wenn jemand die Zuordnung verliert, klärt #146; Zeilen für Kreise kommen mit #141.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| VA-01 | Wer eine Zuordnung hat: Mitgliedschaft in einer Gruppe, einem Stamm, einem Ring oder einem Bund (auch Leitungen), Verbandsleitung, DPV-Veranstaltungsteam | neue Veranstaltung; wer sie anlegt, ist ihre Veranstaltungsleitung | anlegen | erlaubt | BER-03, TEAM-01, #9, #136 (Grundsatz 5) | geplant (#100) |
| VA-02 | Veranstaltungsleitung | eigene Veranstaltung: Name, Beginn, Ende | ansehen, bearbeiten | erlaubt | TEAM-01, #100 | geplant (#100) |
| VA-03 | Alle, die nicht ihre Veranstaltungsleitung sind: Leitungen jeder Ebene, Verbandsleitung, DPV-Veranstaltungsteam, Admins (auch im Support-Zugang), Konto ohne Zuordnung | Veranstaltung | ansehen (in P2), bearbeiten | verboten, „nicht gefunden“. Ab P3 sehen Personen im Teilnahmekreis die Veranstaltung (BER-04) und Admins alle (BER-07) | TEAM-01, #100, #136 (A8) | geplant (#100) |
| VA-04 | Jede Person mit Konto | Veranstaltung | löschen | verboten in P2 | DSG-04, #100, #136 (A15) | geplant (#100) |
| VA-05 | Konto ohne Zuordnung, auch als Admin, Veranstaltungsleitung oder Ansprechperson | Veranstaltung | anlegen | verboten | BER-03, #9, #100, #136 (Grundsatz 5) | geplant (#100) |
| AN-01 | Veranstaltungsleitung | Anmeldungen zur eigenen Veranstaltung: Ansprechperson, angemeldete Personen | ansehen | erlaubt | TEAM-01, #90, #101 | geplant (#101) |
| AN-02 | Ansprechperson | eigene Anmeldung ohne Gesundheitsangaben, auch nach Verlust einer Leitungsrolle oder der Zuordnung | ansehen | erlaubt | ROL-01, #90, #101, #136 (F2.4) | geplant (#101) |
| AN-03 | Alle anderen, z. B. Leitungen der Einheit der angemeldeten Person und darüber, Verbandsleitung, DPV-Veranstaltungsteam, Admins (auch im Support-Zugang) | Anmeldung | ansehen | verboten in P2, „nicht gefunden“ (Leitungen später vielleicht, #110). Später sehen mitangemeldete Personen mit Konto ihre Anmeldung (DSH-04, ANM-06) | BER-01, #90, #101, #136 (A8) | geplant (#101) |
| AN-04 | Jede Person mit Konto, ab P3 nur, wer eine Zuordnung hat (BER-03); wird damit Ansprechperson | sich selbst; Personen, die sie verwalten darf (verwaltete Personen und Mitglieder mit Konto ihres Bereichs) | anmelden (in P2 nur im Datenmodell) | erlaubt | ANM-01, BER-03, #101, #136 (A14, Grundsatz 5) | geplant (#101) |
| AN-05 | Jede Person mit Konto (wird damit Ansprechperson) | Personen außerhalb ihres Bereichs; wer keinen Bereich leitet, jede andere Person (#101); ab P3 ein Konto ohne Zuordnung auch sich selbst (BER-03) | anmelden | verboten | ANM-01, BER-03, #9, #101, #136 (A14, Grundsatz 5) | geplant (#101) |
| AN-06 | Jede Person mit Konto | Anmeldungen | im Tool (Formular) anlegen, ändern, löschen | verboten in P2; nur der Testdaten-Befehl legt sie an | #101, #136 (A14) | geplant (#101) |

## Gesundheitsangaben

In P2 nur als Probe in Anmeldungen (#102), und nur, wenn bis 31.05.2027 die Folgenabschätzung fertig ist oder die Datenschutzperson schriftlich bestätigt, dass keine nötig ist (W2, #102); sonst in P4. Gesundheitsangaben im eigenen Profil kommen frühestens in P4 (FRM-04, unter Vorbehalt).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| GA-01 | Veranstaltungsleitung | Gesundheitsangaben in Anmeldungen zur eigenen Veranstaltung | ansehen | erlaubt | BER-01, TEAM-01, #102 | geplant (#102) |
| GA-02 | Ansprechperson | Gesundheitsangaben in der eigenen Anmeldung, auch dass es welche gibt | ansehen | verboten in P2; der Abschnitt fehlt ganz. Ab P4 ändert die Ansprechperson sie (ANM-08, ANM-09, ANM-12); das klärt #121 | BER-01, #90, #102, #136 (A8) | geplant (#102) |
| GA-03 | Alle außer der Veranstaltungsleitung (GA-01), z. B. Gruppen-, Stammes-, Ring- und Bundesleitung der angemeldeten Person, Verbandsleitung, DPV-Veranstaltungsteam, Mitglied, Konto ohne Zuordnung, Admin (auch im Support-Zugang); zur Ansprechperson GA-02 | Gesundheitsangaben in Anmeldungen | ansehen | verboten | BER-01, #102, #136 (A9) | geplant (#102) |
| GA-04 | Jede Person mit Konto | Gesundheitsangaben in Anmeldungen | im Tool eingeben, ändern | verboten in P2; nur der Testdaten-Befehl legt sie an | #102 | geplant (#102) |
| GA-05 | Jede Person mit Konto | Gesundheitsangaben im Profil einer verwalteten Person | speichern | verboten; das Feld gibt es nicht | PER-02, FRM-04, #117 | geplant (#117) |

## Support-Zugang der Admins

Der „technische Vollzugriff“ der Admins (BER-02) besteht im Tool nur als Support-Zugang mit den Rechten der Leitung einer Einheit (#92). Admin wird man bis ADM-01 nur per Befehl auf dem Server (RO-19).

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| SZ-01 | Admin | Support-Zugang für genau eine Einheit (nicht den Verband), mit Anlass aus einer festen Liste, höchstens 60 Minuten | starten, beenden | erlaubt | BER-02, #92 | geplant (#92) |
| SZ-02 | Leitung, Mitglied, Konto ohne Zuordnung, Verbandsleitung, DPV-Veranstaltungsteam | Support-Zugang | starten | verboten | #92 | geplant (#92) |
| SZ-03 | Admin im Support-Zugang | alles, was die Leitung der gewählten Einheit dort und darunter sehen und ändern darf | wie diese Leitung | erlaubt, außer Rollen für sich selbst (SZ-05); jeder Zugriff steht im Protokoll der Admin-Zugriffe | BER-02, #92, #136 (A6) | geplant (#92) |
| SZ-04 | Admin im Support-Zugang | Einheiten außerhalb der gewählten; alles nach Ablauf, Abmelden oder Beenden | ansehen, ändern | verboten ab dem nächsten Klick | #92, #90 | geplant (#92) |
| SZ-05 | Admin im Support-Zugang | Rolle für sich selbst, als Leitung oder Mitglied | vergeben | verboten | #92 | geplant (#92) |
| SZ-06 | Admin ohne Support-Zugang | Personendaten: Personen mit Konto, verwaltete Personen, Anmeldungen | ansehen, suchen, anlegen, ändern, löschen | verboten | BER-02, #89, #92, #136 (A6) | geplant (#92) |

## Protokolle

In P2 werden die Protokolle nur geschrieben; die Einsicht kommt mit ADM-03 in P8 (Entscheidung W4). Der Testdaten-Befehl (#103) darf die Datenbank lokal und in der Testumgebung vollständig leeren, auch die Protokolle. Das Protokoll der Kontosuchen ist vorgemerkt (#144, spätestens P6); seine Zeilen kommen mit ihm. Wie lange Einträge bleiben und wie abgelaufene kontrolliert gelöscht oder anonymisiert werden, klärt #147 (P6, mit der Datenschutzperson, #149); bis dahin gilt die Sperre aus PR-02, PR-04 und PR-06.

| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| PR-01 | Jede Person mit Konto, auch Admins und Verbandsleitung | Protokoll der Rollenänderungen | ansehen im Tool | verboten in P2 (W4); ab P8 Admins (ADM-03) | ROL-04, ADM-03, #91 | geplant (#90) |
| PR-02 | Jede Person, auch Admins | Einträge im Protokoll der Rollenänderungen | ändern, löschen | verboten, im Programm und in der Datenbank; Einträge entstehen nur beim Vergeben und Entfernen von Rollen, mit #118 auch beim Anlegen, Verschieben und Löschen verwalteter Personen | BER-02, ROL-04, #91, #118, #136 (A12) | gebaut: erlaubt `tests/test_rollen_protokoll.py::test_jede_rolle_kommt_ins_protokoll`; verboten `tests/test_rollen_protokoll.py::test_eintrag_laesst_sich_im_programm_nicht_aendern_oder_loeschen`, `tests/test_rollen_protokoll.py::test_sammelaenderungen_scheitern_an_der_datenbank`, `tests/test_rollen_protokoll.py::test_aendern_per_sql_scheitert_an_der_datenbank` |
| PR-03 | Jede Person mit Konto, auch Admins und Verbandsleitung | Protokoll der Strukturänderungen | ansehen im Tool | verboten in P2 (W4); ab P8 Admins (ADM-03) | ORG-06, ADM-03, #131 | geplant (#90) |
| PR-04 | Jede Person, auch Admins | Einträge im Protokoll der Strukturänderungen | ändern, löschen | verboten, im Programm und in der Datenbank; Einträge entstehen nur beim Anlegen und Ändern von Einheiten | BER-02, ORG-06, #131 | gebaut: erlaubt `tests/test_einheiten_protokoll.py::test_gruppe_umbenennen`; verboten `tests/test_einheiten_protokoll.py::test_eintrag_laesst_sich_im_programm_nicht_aendern_oder_loeschen`, `tests/test_einheiten_protokoll.py::test_sammelaenderungen_scheitern_an_der_datenbank`, `tests/test_einheiten_protokoll.py::test_aendern_per_sql_scheitert_an_der_datenbank` |
| PR-05 | Jede Person mit Konto, auch Admins und Verbandsleitung | Protokoll der Admin-Zugriffe (Zeitpunkt, Admin, Art des Zugriffs, Bereich; keine Namen einzelner Personen, ADM-03) | ansehen im Tool | verboten in P2 (W4); ab P8 Admins und Verbandsleitung (ADM-03, ROL-03) | ADM-03, ROL-03, #92, #136 (A7) | geplant (#92) |
| PR-06 | Jede Person, auch Admins | Einträge im Protokoll der Admin-Zugriffe | ändern, löschen | verboten, im Programm und in der Datenbank; Einträge entstehen nur beim Start und Ende eines Support-Zugangs, bei jeder Seite mit Personendaten, jeder Änderung und dem Notfall-Löschen per Befehl | BER-02, #92, #136 (A12) | geplant (#92) |

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
