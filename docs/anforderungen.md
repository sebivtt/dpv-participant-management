# Anforderungsdokument DPV-Anmeldetool

Oct 19, 2026 · @Sebastian vetter

## Lesehinweise

Dieses Dokument beschreibt die fachlichen Anforderungen (Why und What) an ein Anmelde- und Veranstaltungstool für den DPV e.V. Die technische Umsetzung (How) ist nicht Teil dieses Dokuments. Stand: zweiter Entwurf nach kritischer Durchsicht auf Widersprüche, Lücken, Prioritäten und Datenschutz.

Jede Anforderung hat eine eindeutige ID (z. B. ANM-03) und eine Priorität:

| Priorität | Bedeutung | Zielzeitpunkt |
| --- | --- | --- |
| Muss | Ohne diese Funktion ist das Tool nicht einsetzbar | Erste Vorbereitungstreffen (Generalprobe) |
| Soll | Wichtig für den vollen Nutzen | Vor Öffnung der Anmeldung zum Verbandslager 2031 |
| Kann | Ausbau, Vision oder Komfort | Danach, nach Bedarf und Zeit |

Begriffe wie Einheit, Ansprechperson oder verwaltete Person sind im Glossar am Ende erklärt. Offene Punkte sind mit OP-Nummern markiert. Hängt eine Anforderung von einer anderen ab, steht an ihrem Ende „Setzt voraus: …“. Nach Abschluss aller Muss-Anforderungen werden Soll und Kann neu bewertet und schrittweise umgesetzt.

## Ausgangslage und Motivation

Anmeldung und Teilnehmendenverwaltung kosten bei Pfadfinderaktionen bis heute viel Handarbeit, weil kein vorhandenes Tool zu den Strukturen des DPV passt. Das neue Tool soll das lösen: ein Tool für alle, freundlich in der Bedienung, einfach und genau auf die Bedürfnisse der Pfadfinderei im DPV zugeschnitten.

**Erfahrungshintergrund.** Der Initiator ist seit 20 Jahren Pfadfinder, war Gruppen- und Stammesleitung, hat beim Verbandslager Via (ca. 3.500 Teilnehmende) einen Programmpunkt geplant und die Sippenaktion (ca. 1.000 Teilnehmende) geleitet. Er plant das nächste Verbandslager 2031 (ca. 5.000 Teilnehmende).

**Bisherige Lösungen und ihre Grenzen:**

| Lösung | Stärken | Schwächen |
| --- | --- | --- |
| DPV-Biber (Eigenentwicklung) | Viele passende Funktionen | Keine Wartung und Weiterentwicklung, daher viele Fehler; nicht mehr in Betrieb (Stand Oktober 2026) |
| Campflow (kommerziell) | Gute Bedienung, wenig fehleranfällig | Kaum an die Bedürfnisse eines großen Verbands anpassbar |
| Confluence, NextCloud (OnPrem) | Planung und Dokumentation | Funktionieren im Pfadfinderkontext eher schlecht; der DPV ist auf Google gewechselt |

**Projektform.** Das Tool ist eine Eigeninitiative des Initiators. Er entwickelt, pflegt und betreibt es langfristig und stellt es dem DPV kostenfrei zur Verfügung. Das Ziel ist ausdrücklich kein Großprojekt, sondern ein Tool, das eine einzelne Person realistisch bauen und pflegen kann.

## Ziele, Erfolgskriterien und Leitprinzipien

Das Tool ist erfolgreich, wenn das Verbandslager 2031 vollständig darüber läuft und Biber und Campflow im DPV nicht mehr gebraucht werden.

**Erfolgskriterien:**

1. Das Verbandslager 2031 läuft komplett über das Tool, ohne Excel-Listen nebenher. Exporte für eigene Auswertungen sind erlaubt, eine parallele Datenpflege außerhalb des Tools nicht.
2. Eine einfache Veranstaltung (Name, Datum, Ort, Einladungstext, Teilnahmekreis, fester Beitrag, Standardformular ohne Zusatzfragen) ist in unter 15 Minuten angelegt und veröffentlicht.
3. Biber und Campflow werden im DPV nicht mehr gebraucht.

**Leitprinzipien:**

- **Einfachheit vor Vollständigkeit.** Jede Funktion muss für eine einzelne Person baubar und wartbar bleiben. Im Zweifel wird eine Funktion als Kann eingestuft.
- **Vertrauen statt Kontrolle.** Pfadfinderinnen und Pfadfinder handeln verantwortungsbewusst. Statt harter Sperren gibt es Hinweise, Protokolle und Benachrichtigungen.
- **Datensparsamkeit.** Es wird nur erhoben und gespeichert, was eine Veranstaltung wirklich braucht. Was pro Anmeldung reicht, wird nicht pro Person abgefragt.
- **Optional statt Pflicht.** Fast alle Zusatzfunktionen (Preisstufen, Zahlungen, Erinnerungen, Warteliste) sind pro Veranstaltung abschaltbar und standardmäßig aus.
- **Mobil und am PC nutzbar.** Alle Funktionen sind im Browser auf Handy und PC bedienbar.
- **Open Source und Non-Profit bevorzugt.** Solche Lösungen werden gewählt, wenn sie ohne nennenswerten Qualitätsverlust einsetzbar sind (z. B. OpenStreetMap statt Google für die Adresssuche).
- **Barrierefreiheit mitdenken.** Grundlegende Barrierefreiheit gilt von Anfang an als Entwicklungsprinzip.

## Rahmenbedingungen und Abgrenzung

Das Tool ist für den DPV e.V. gebaut, läuft später auf DPV-Servern, nutzt den Keycloak-Login des DPV und muss bis zur Anmeldung zum Verbandslager 2031 einsatzreif sein.

**Zielgruppe.** Mitglieder des DPV e.V. mit seinen Bünden, Ringen (nur DPBM Mosaik), Stämmen und Gruppen. Externe können pro Veranstaltung als Gäste zugelassen werden.

**Zeitplan:**

1. Entwicklung und erste Tests lokal auf dem Rechner des Entwicklers, nur mit erfundenen Testdaten.
2. Erste vorzeigbare Version wird dem DPV vorgestellt und auf DPV-Servern betrieben.
3. Generalproben: Die Vorbereitungstreffen zum Verbandslager laufen über das Tool (alle Muss-Funktionen).
4. Pilotphase: Vor dem Anmeldestart zum Verbandslager laufen mehrere unterschiedliche Veranstaltungstypen über das Tool, z. B. ein Stammeswochenende mit Kindern, eine Bundesaktion mit Sammelanmeldungen, ein bundesübergreifendes AK-Treffen und eine Tagesveranstaltung ohne Übernachtung.
5. Einsatzreife für das Verbandslager 2031 (alle Soll-Funktionen), Anmeldestart voraussichtlich 2030. Entwicklungszeitraum ca. 1–2 Jahre.
6. Nach Abschluss aller Muss-Anforderungen werden Soll- und Kann-Anforderungen neu bewertet und schrittweise umgesetzt.

**Mengengerüst:**

| Größe | Wert |
| --- | --- |
| Personen im System | bis ca. 8.000 Mitglieder, dazu Gäste und Adressbuch-Einträge |
| Leitungen | ca. 500 |
| Aktive Accounts | zu Beginn ca. 250, Ziel ca. 1.000 |
| Gleichzeitig Nutzende | bis ca. 100 in Spitzenzeiten (Annahme, z. B. kurz vor Anmeldeschluss des Verbandslagers) |
| Veranstaltungen pro Jahr | zu Beginn 30–50, langfristig bis ca. 1.000 |
| Größte Veranstaltung | ca. 5.000 Teilnehmende (Verbandslager 2031) |
| Anmeldeverhalten | eher über Wochen verteilt, kein Ansturm zur Öffnung erwartet |

**Bewusst nicht enthalten (Abgrenzung):**

- Mandantenfähigkeit für andere Verbände. Sie soll durch die Struktur aber nicht dauerhaft ausgeschlossen werden.
- Kontingentanmeldungen („wir kommen mit ca. 25“). Das klärt die Veranstaltungsleitung persönlich.
- Weitere Preismodelle wie Leitungs-, Kinder-, Geschwister- oder Solipreise.
- Automatische Zuordnung von Zahlungseingängen und Online-Bezahlung.
- Auswahl von Zielgruppen nach Alter oder Stufe.
- Massenmails an „alle“.
- Upload und Download von Word-Dateien als Mailvorlagen.
- Eine eigene App im App Store. Das Tool ist eine Web-Anwendung im Browser.
- Mehrsprachigkeit. Die Oberfläche ist nur auf Deutsch, Texte werden aber so abgelegt, dass eine spätere Übersetzung möglich bleibt.
- Migration aus dem Biber und Massenimport von Personen. Leitungen legen ihre Personen manuell an, auch direkt während einer Anmeldung.
- Nacherfassung vergangener Veranstaltungen.
- Altersprüfung bei Accounts. Keycloak erhebt kein Alter (Auskunft des DPV-Admins vom 21.10.2026, OP-1). Was das für die Einwilligung von Personen mit Account bedeutet, klärt OP-2.

## Organisationsstruktur, Personen und Rollen

Personen gehören zu Einheiten der Hierarchie Verband → Bund → (Ring) → Stamm → Gruppe. Rechte an Personendaten ergeben sich aus der Leitungsrolle in einer Einheit, nicht aus der Person, die Daten angelegt hat. Veranstaltungen, eigene Kreise und Orte gehören dagegen den Personen, die sie anlegen.

### Organisationsstruktur und Login

| ID | Anforderung | Priorität |
| --- | --- | --- |
| ORG-01 | Hierarchie Verband → Bund → Ring (nur in Bünden mit Ringen, derzeit DPBM Mosaik) → Stamm → Gruppe. Verband und Bünde sind Pflichtstruktur. Den Verband und die Bünde zum Start legen Admins an; weitere Bünde legt die Verbandsleitung an und legt dabei fest, ob der Bund Ringe hat (ROL-03); danach entscheidet das die Bundesleitung (ORG-06). Ringe, Stämme und Gruppen sind optional. Gruppen werden frei benannt (z. B. Meute, Sippe, Runde); das System unterscheidet keine Gruppentypen. Personen können direkt einem Bund, einem Ring oder einem Stamm angehören, auch wenn es darunter weitere Einheiten gibt (Einzelmitglieder, ROL-01). Bünde sind eindeutig benannt; Stämme und Gruppen dürfen gleich heißen und werden über ihre übergeordnete Einheit unterschieden. | Muss |
| ORG-02 | Mitglieder melden sich ausschließlich per Single Sign-on über den Keycloak des DPV an. | Muss |
| ORG-03 | Keycloak ist führend für Identität und Login (Name, Mail, Account). Das Tool ist führend für alles, was Keycloak nicht kennt (eigene Kreise, verwaltete Personen, Veranstaltungs- und Anmeldedaten, Ernährung). | Muss |
| ORG-04 | Ändert eine Person ihre Stammdaten (z. B. Name, Geburtsdatum), kommt die Änderung auch in Keycloak an. Variante A: Das Tool schreibt direkt zurück (falls der DPV Schreibrechte vergibt). Variante B: Weiterleitung zum Keycloak-Profil, Übernahme beim nächsten Login. | Soll |
| ORG-05 | Die Zuordnung einer Person zur Organisationsstruktur wird im Tool mindestens angezeigt. Quelle: das Tool (OP-1, entschieden am 20.10.2026). | Muss |
| ORG-06 | Das Tool pflegt die Struktur selbst (OP-1). Einheiten legen an und löschen: die Bundesleitung Ringe, in Bünden ohne Ringe auch Stämme, und Gruppen im ganzen Bund; die Ringleitung Stämme und Gruppen in ihrem Ring; die Stammesleitung Gruppen in ihrem Stamm. Gelöscht werden nur Einheiten ohne Einheiten darunter. Mitglieder und verwaltete Personen der gelöschten Einheit werden der Ebene darüber zugeordnet; ihre Leitungsrollen in dieser Einheit enden. Das Tool nennt beides vorher. Einzelheiten regelt #108. Umbenennen darf jede Leitung ihre eigene Einheit und alle Einheiten darunter. Die Bundesleitung ordnet Stämme einem Ring zu oder wechselt ihn und schaltet „hat Ringe“ ein. Ausgeschaltet wird „hat Ringe“ in einem Schritt: Alle Stämme werden aus ihren Ringen genommen, die Ringe gelöscht (ihre Mitglieder kommen zum Bund, die Ringleitungen enden, wie beim Löschen oben) und der Schalter ausgeschaltet; das Tool nennt vorher, was passiert. Bis zur Seite für Bünde (#107) tut das ein Admin per Befehl auf dem Server, auf Bitte der Bundesleitung. Hat eine Einheit keine Leitung mit Konto, springt die Leitung darüber ein (ROL-02). Jede Änderung an der Struktur (anlegen, umbenennen, löschen, Ring zuordnen oder wechseln, „hat Ringe“) wird protokolliert. | Muss |
| ORG-07 | Beim Löschen einer Einheit zeigt das Tool eine Zusammenfassung (Untereinheiten, Personen, laufende Anmeldungen). Verwaltete Personen werden wahlweise in eine andere Einheit verschoben (Fusion, Teilung) oder gelöscht. Personen mit Account werden nie gelöscht, sie verlieren nur Zuordnung und Rolle. Bestätigung durch Eintippen des Einheitennamens. | Muss |
| ORG-08 | Gelöschte Einheiten liegen 30 Tage im Papierkorb und können wiederhergestellt werden. | Soll |
| ORG-09 | Jeder Stamm hat eine Adresse (z. B. Stammesheim), gepflegt von der Stammesleitung. Sie ist Grundlage für entfernungsabhängige Preise. | Soll |

### Personentypen

| ID | Anforderung | Priorität |
| --- | --- | --- |
| PER-01 | **Person mit Account:** loggt sich ein, pflegt ihre eigenen Daten, meldet sich und je nach Rolle andere an. | Muss |
| PER-02 | **Verwaltete Person (Profil ohne Account):** typischerweise Kinder und Jugendliche aus Meute und Sippe oder Rover ohne Leitungsfunktion, ohne feste Altersgrenze. Sie gehört genau einer Einheit. Sehen und bearbeiten dürfen die jeweils aktuellen Leitungen dieser Einheit und der Ebenen darüber. Bei einem Leitungswechsel wechselt der Zugriff automatisch. Wechselt die Person die Einheit, ändert eine Leitung die Zugehörigkeit im Rahmen ihrer Zuständigkeit; sonst wird die Person gelöscht und von der aufnehmenden Leitung neu angelegt. Im Profil verwalteter Personen werden keine Gesundheitsangaben gespeichert (FRM-04). | Muss |
| PER-03 | **Gast:** weder Account noch gespeichertes Profil, meldet sich nur zu einer einzelnen Veranstaltung an (siehe ANM-04). | Soll |
| PER-04 | **Persönliches Adressbuch:** Personen außerhalb der eigenen Einheiten (z. B. eine Köchin von außerhalb) werden gespeichert und bei Anmeldungen wieder ausgewählt. Nur für die besitzende Person sichtbar, nicht übertragbar, wird mit dem Account gelöscht. Beim Speichern bestätigt man: „Die Person ist mit der Speicherung einverstanden.“ Wurde ein Eintrag 2 Jahre nicht für eine Anmeldung genutzt, fragt das Tool, ob er behalten oder gelöscht werden soll; keine automatische Löschung. | Soll |
| PER-05 | Bekommt eine verwaltete Person später einen Account, werden Profil und Account verknüpft. Anmeldungen innerhalb der Aufbewahrungsfrist werden mit dem Account verknüpft; danach bleibt nur das Datum der letzten Teilnahme (DSG-03). | Soll |
| PER-06 | Beim Anlegen einer verwalteten Person prüft das Tool auf Dubletten (Vorname + Nachname + Geburtsdatum) und gibt einen Hinweis, sperrt aber nicht. Liegt der Treffer außerhalb der eigenen Zuständigkeit, nennt der Hinweis die Einheit nicht. | Soll |
| PER-07 | Eine Leitungsrolle kann auch bei einer verwalteten Person eingetragen sein (nur Anzeige). Die Rechte einer Leitung gibt es nur mit Account; fehlt er, springt die nächsthöhere Ebene ein. | Muss |
| PER-08 | Optionales Feld „Kontakt Erziehungsberechtigte“ (Name, Mail) im Profil verwalteter Personen. | Kann |

### Rollen und Rollenvergabe

| ID | Anforderung | Priorität |
| --- | --- | --- |
| ROL-01 | Rollen: Mitglied, Gruppenleitung, Stammesleitung, Ringleitung, Bundesleitung, Verbandsleitung, DPV-Veranstaltungsteam, Admin. Eine Person kann mehrere Rollen in verschiedenen Einheiten haben. Eine Person mit Account ist Mitglied in höchstens einer Einheit, nie im Verband selbst. Leitungsrollen hat sie nur auf ihrem Leitungspfad: im eigenen Stamm einschließlich seiner Gruppen und in den Einheiten darüber; ist sie direkt Mitglied eines Rings oder Bundes, auch in allen Einheiten darunter. Wer als Leitung einer Gruppe, eines Stammes, eines Rings oder eines Bundes eingesetzt wird und noch keiner Einheit angehört, wird Mitglied der geleiteten Einheit. Verbandsleitung und DPV-Veranstaltungsteam brauchen keine Mitgliedschaft. Eine Person kann jederzeit selbst austreten und wählt dabei die Ebene, aus der sie austritt. Sie wird Einzelmitglied der Ebene darüber; wer aus dem Bund austritt, hat danach keine Zuordnung mehr. Entfernt eine Leitung die Person aus ihrer Einheit, wirkt das genauso, eine Ebene nach oben. Dabei enden alle Leitungsrollen in der verlassenen Einheit und den Einheiten darunter sowie alle, die danach nicht mehr auf ihrem Leitungspfad liegen; das Tool nennt sie vorher. Bestehende Anmeldungen bleiben erhalten. Ein Wechsel per Beitrittsanfrage gilt als Verlassen der bisherigen Einheit; die bisherige Leitung erfährt, dass die Person gegangen ist, nicht wohin. | Muss |
| ROL-02 | Vertrauensprinzip: Leitungen benennen und entfernen Leitungen in allen Einheiten unter ihrer eigenen: die Bundesleitung im ganzen Bund, die Ringleitung in ihrem Ring, die Stammesleitung in den Gruppen ihres Stammes. Benannt werden kann nur, wer die Rolle danach auf seinem Leitungspfad hat (ROL-01). Leitungen benennen und entfernen weitere Leitungen derselben Einheit, auch gegenseitig. Niemand gibt sich selbst eine Rolle; die eigene Rolle niederlegen darf jede Person. Eine Einheit ohne Leitung mit Konto löst keinen Automatismus aus; es wird keine Rolle vergeben. Solange sie keine Leitung mit Konto hat, hat die Leitung der Einheit direkt darüber dort alle Rechte einer Leitung. Fehlt auch diese, gilt das für die nächsthöhere, höchstens bis zur Bundesleitung, nie für die Verbandsleitung. | Muss |
| ROL-03 | Die Verbandsleitung hat als Verbandsleitung keinen Zugriff auf Personendaten der Bünde, Ringe, Stämme und Gruppen, außer nach BER-01, Grund 3 und 4. Sie legt Bünde an, benennt sie um und legt beim Anlegen fest, ob der Bund Ringe hat (ORG-01); danach entscheidet das die Bundesleitung (ORG-06). Sie benennt und entfernt Bundesleitungen, weitere Verbandsleitungen und die Mitglieder des DPV-Veranstaltungsteams; sich selbst gibt sie keine Rolle (ROL-02). Wird eine Person der Verbandsleitung von einer anderen zur Bundesleitung benannt, hat sie dort die Rechte der Bundesleitung, nicht als Verbandsleitung; die Benennung steht im Protokoll der Rollenänderungen. Für eine Einheit ohne Leitung springt sie nie ein. Ausnahme: Sie darf das Protokoll der Admin-Zugriffe einsehen (ADM-03). Die erste Verbandsleitung benennt ein Admin. | Muss |
| ROL-04 | Jede Rollenänderung wird protokolliert. Wer aus einer Rolle entfernt wird, bekommt eine Benachrichtigung. | Soll |
| ROL-05 | **DPV-Veranstaltungsteam**: Die Verbandsleitung benennt die Mitglieder. Die Rolle erlaubt nur, bundesübergreifende Einheiten, Rollen und „alle“ als Teilnahmekreis zu wählen; für Kreise gilt BER-04. Sie gibt keinen weiteren Zugriff auf Personendaten. | Muss |

## Berechtigungen und Sichtbarkeit

Personendaten sieht nur, wer einen Grund nach BER-01 hat, vor allem die Leitungen der Einheit und der Ebenen darüber. Die Verbandsleitung sieht Personendaten nur nach BER-01, Grund 3 und 4, Admins nur für Support und protokolliert.

**Beispiel:** Die Stammesleitung von Walhall sieht die Personen ihres Stammes, die Stammesleitung der Zugvögel nicht. Die Bundesleitung des Pfadfinderbunds Boreas sieht die Personen, die Stämmen und Gruppen in Boreas zugeordnet sind, nicht aber persönliche Adressbücher.

| Wer | Verwaltete Personen | Personen fremder Einheiten | Adressbücher anderer | Veranstaltungen |
| --- | --- | --- | --- | --- |
| Gruppenleitung | eigene Gruppe | nein | nein | eigene Teilnahmekreise, geleitete Veranstaltungen |
| Stammesleitung | eigener Stamm und seine Gruppen | nein | nein | wie oben |
| Ring-/Bundesleitung | eigener Ring/Bund und alles darunter | nein | nein | wie oben |
| Verbandsleitung | keine | nein | nein | wie oben |
| DPV-Veranstaltungsteam | keine | nein | nein | wie oben |
| Admin | technisch alles, Zugriffe protokolliert | technisch ja | technisch ja | alle |

### Anforderungen

| ID | Anforderung | Priorität |
| --- | --- | --- |
| BER-01 | Personendaten sieht nur, wer einen der folgenden Gründe hat; alles andere ist verboten:<br>1. die Person selbst ihre eigenen Daten;<br>2. die Leitungen ihrer Einheit und der Ebenen darüber (siehe Tabelle);<br>3. Name, Fahrtenname und Rolle einer Leitung: wer diese Leitung auf seiner Kette nach oben hat, mit ihr dieselbe Einheit leitet oder sie als Leitung einer Einheit in seinem Bereich hat; das gilt auch für angezeigte Leitungsrollen verwalteter Personen (Rechtematrix RO-01 bis RO-03, RO-09); die Verbandsleitung außerdem bei Bundesleitungen, weiteren Verbandsleitungen und dem DPV-Veranstaltungsteam (RO-05);<br>4. Name und Fahrtenname eines Kontos und ob es schon woanders Mitglied ist, ohne die Einheit: Leitungen und Verbandsleitung, die es über die genaue Mail oder den genauen Benutzernamen finden (PK-13);<br>5. die Veranstaltungsleitung: die Anmeldungen zu ihrer Veranstaltung (AN-01); die Ansprechperson: ihre eigene Anmeldung mit den angemeldeten Personen (AN-02);<br>6. ein Admin im Support-Zugang, mit den Rechten der Leitung der gewählten Einheit (BER-02);<br>7. die Protokolle nach ADM-03: Admins ab P8; das Protokoll der Admin-Zugriffe auch die Verbandsleitung (ROL-03).<br><br>Gesundheitsangaben aus Anmeldungen sieht nur die Veranstaltungsleitung; im eigenen Profil gespeicherte Gesundheitsangaben sieht nur die Person selbst. Namen von Einheiten sind keine Personendaten; wer welche Einheiten sieht, regelt die Rechtematrix. Kommen neue Daten oder Rollen hinzu (z. B. Kreise, Veranstaltungsteam), werden ihre Gründe im selben Pull Request hier und in der Rechtematrix ergänzt (Entscheidung vom 23.10.2026, Nr. 2). | Muss |
| BER-02 | Admins haben technischen Vollzugriff für Support und Fehlerbehebung. Jeder Zugriff auf Personendaten wird protokolliert. Admins können Protokolleinträge weder ändern noch löschen. | Muss |
| BER-03 | Eine Veranstaltung planen, zu einer Veranstaltung einladen, sich oder andere anmelden und öffentliche Veranstaltungen sehen kann nur, wer eine Zuordnung hat. Zuordnung heißt: Mitglied einer Gruppe, eines Stammes, eines Rings oder eines Bundes, oder die Rolle Verbandsleitung oder DPV-Veranstaltungsteam. Admin, Veranstaltungsleitung, Ansprechperson und Verwaltende eines Kreises sind keine Zuordnung. Veranstaltungsleitung oder Mitglied eines Veranstaltungsteams wird nur, wer eine Zuordnung hat. Was ein Konto ohne Zuordnung darf, regelt die Rechtematrix. Gäste über einen Gast-Link (ANM-04) melden sich ohne Konto an. Was beim Verlust der Zuordnung mit bestehenden Anmeldungen geschieht, regelt ROL-01. | Muss |
| BER-04 | **Teilnahmekreis:** legt fest, wer eine Veranstaltung sehen und sich anmelden darf (beides fällt immer zusammen). Bausteine, frei kombinierbar: Einheiten (auch mehrere), Rollen (z. B. „alle Bundesleitungen“ für eine MV), eigene Kreise oder „alle“. Wer eine Zuordnung hat (BER-03), wählt, wozu er gehört: Einheiten innerhalb des eigenen Bundes bzw. der eigenen Bünde sowie Kreise, in denen er Mitglied oder Verwaltende ist, auch bundesübergreifend. Andere Kreise kann man nicht wählen. Bundesleitungen, Verbandsleitung und DPV-Veranstaltungsteam dürfen außerdem bundesübergreifende Einheiten, Rollen und „alle“ wählen; für Kreise gilt auch für sie die Regel oben. Wer nur über einen eigenen Kreis zum Teilnahmekreis gehört, meldet sich nur selbst an (keine Mitanmeldung verwalteter Personen). Setzt voraus: GRP-01, ROL-05. | Muss |
| BER-05 | **Benachrichtigungskreis:** optional, legt fest, wer aktiv per Mail über die neue Veranstaltung informiert wird. Er ist gleich oder kleiner als der Teilnahmekreis. Wählbar sind nur Einheiten, in denen man selbst Leitung ist (und alles darunter), rollenbasierte Kreise im eigenen Bereich und selbst verwaltete eigene Kreise. Die Verbandsleitung darf jeden Benachrichtigungskreis wählen. „Alle“ ist als Benachrichtigungskreis nie wählbar. | Muss |
| BER-06 | Sind Gäste nicht zugelassen, hebelt der Anmeldelink den Teilnahmekreis nicht aus. Wer nicht dazugehört, sieht: „Diese Veranstaltung richtet sich an … Bitte wende dich an die Veranstaltungsleitung.“ Ist der Teilnahmekreis ein privater Kreis, steht dort nur: „Diese Veranstaltung richtet sich an einen geschlossenen Personenkreis.“ Sind Gäste zugelassen (VER-11), kann sich bewusst jede Person mit dem Link als Gast anmelden. | Muss |
| BER-07 | Admins sehen alle Veranstaltungen, unabhängig vom Teilnahmekreis. | Muss |

*Beispiel Vorbereitungstreffen:* Teilnahmekreis „alle“ (gewählt vom DPV-Veranstaltungsteam), Benachrichtigungskreis ist der eigene Kreis „Planungsteam“. Das Planungsteam bekommt eine Mail, alle anderen sehen die Veranstaltung im Dashboard und dürfen sich anmelden.

## Veranstaltung planen

Eine Veranstaltung entsteht als Entwurf, wird per Schalter veröffentlicht und ist erst ab Anmeldestart zur Anmeldung offen. Ihre Leitung kann aus mehreren Personen bestehen.

### Grunddaten und Einstellungen

| ID | Anforderung | Priorität |
| --- | --- | --- |
| VER-01 | Der Name der Veranstaltung wird als Erstes eingegeben und ist Pflicht. | Muss |
| VER-02 | Beginn- und Enddatum sind Pflicht, Uhrzeiten optional. Standard: Freitag 18:00 bis Sonntag 12:00. | Muss |
| VER-03 | Plausibilitätsprüfung beim Anlegen und Veröffentlichen: Ende vor Beginn und Beginn in der Vergangenheit sind nicht möglich. Bei einer Dauer über 4 Wochen fragt das Tool nach, ob das stimmt. | Muss |
| VER-04 | Ort mit Bezeichnung und Adresse, Adresssuche mit Vorschlägen (OpenStreetMap bevorzugt). Auswahl aus dem Ortsverzeichnis siehe ORT. | Muss |
| VER-05 | Einladungstext mit einfachem Editor (fett, kursiv, Listen, Links, Überschriften). | Muss |
| VER-06 | Banner und Bilder zur Gestaltung der Einladung. | Soll |
| VER-07 | Veranstaltungen lassen sich jederzeit als Entwurf zwischenspeichern. | Muss |
| VER-08 | Schalter „sichtbar“ in Übersicht und Bearbeitungsmaske. Die Anmeldung startet erst, wenn die Veranstaltung sichtbar ist und der Anmeldezeitraum begonnen hat. Wird eine Veranstaltung mit bestehenden Anmeldungen unsichtbar geschaltet, sind keine neuen Anmeldungen möglich; bestehende bleiben gültig und für die Ansprechpersonen unter „Meine Anmeldungen“ sichtbar und bearbeitbar. | Muss |
| VER-09 | Fristen pro Veranstaltung: Anmeldestart, Anmeldeschluss, Änderungsschluss. Es gilt: Anmeldestart ≤ Anmeldeschluss ≤ Änderungsschluss. Fristen lassen sich auch nach der Veröffentlichung ändern; wird der Anmeldeschluss verschoben, ist die Anmeldung wieder offen (Nachmeldephase). | Muss |
| VER-10 | Schalter „Einladungsseite öffentlich“ (Standard: aus). Öffentlich sieht jede Person mit Link die Einladung ohne Login; optional nur der Ort ohne genaue Adresse (z. B. „bei Kassel“). | Soll |
| VER-11 | Schalter „Gäste zulassen“ (Standard: aus). | Soll |
| VER-12 | Absage einer Veranstaltung jederzeit möglich, mit Pflichtmail an alle Angemeldeten. | Muss |
| VER-13 | Veranstaltung kopieren: alle Einstellungen, Formular, Mails und Preise, ohne Anmeldungen; Daten werden neu gesetzt. | Soll |
| VER-14 | Eigene Veranstaltungsvorlagen anlegen. | Kann |
| VER-15 | Mehrere Anmeldestrecken pro Veranstaltung (z. B. „Teilnehmende“ und „Helfende“) mit gemeinsamen Listen und Finanzen. | Kann |
| VER-16 | Dateien zum Download bereitstellen (Elternbrief, Packliste, Gesundheitsbogen, Anfahrt), verlinkt auf der Einladungsseite und in Mails. Upload durch Teilnehmende ist ein Kann. | Soll |

### Leitungsteam

| ID | Anforderung | Priorität |
| --- | --- | --- |
| TEAM-01 | Wer eine Veranstaltung erstellt, ist automatisch Veranstaltungsleitung. Weitere Personen mit Account können als Veranstaltungsleitung hinzugefügt werden. Es gibt immer mindestens eine Veranstaltungsleitung; die letzte kann sich nicht selbst entfernen. Die Veranstaltungsleitung sieht und darf alles. Alle, die eine Veranstaltung mitleiten, bilden ihr Leitungsteam. | Muss |
| TEAM-02 | Feineres Rollenmodell im Leitungsteam; eine Person kann mehrere Rollen haben: Mitleitung (bearbeiten, Anmeldungen ohne Gesundheitsdaten), Küche (Küchenübersicht, Ernährung), Gesundheit/Sani (Gesundheitsdaten, Notfallkontakte), Finanzen (Zahlungen, Budget, Ausgaben). Absagen, Löschen und das Verwalten des Leitungsteams bleiben der Veranstaltungsleitung vorbehalten. | Kann |
| TEAM-03 | Eigene Kreise lassen sich als Ganzes ins Leitungsteam aufnehmen, aber nur private Kreise. Wer dem Kreis beitritt, erhält die Rechte im Leitungsteam. Setzt voraus: GRP-02. | Kann |

Hinweis: Bis TEAM-02 umgesetzt ist, sieht jede Veranstaltungsleitung auch Gesundheitsdaten. Das Leitungsteam sollte daher bewusst klein gehalten werden; die Küche erhält von der Veranstaltungsleitung einen Auszug (Küchenliste, LIS-04).

### Lebenszyklus

&#91;embedded content: Lebenszyklus einer Veranstaltung · 8 Zustände\]

Nach dem Anmeldeschluss sind Änderungen und Nachmeldungen zu bestehenden Anmeldungen bis zum Änderungsschluss möglich. Wird der Anmeldeschluss verschoben, wechselt die Veranstaltung von „Geschlossen“ zurück zu „Anmeldung offen“. Die Veranstaltungsleitung kann eine Veranstaltung in jedem Zustand endgültig löschen (DSG-04).

## Anmeldeformular und Datenfelder

Jedes Formular besteht aus festen Standardblöcken und frei wählbaren Zusatzfragen. Zusatzfragen gelten standardmäßig einmal pro Anmeldung, nur Ernährung und Gesundheit immer pro Person.

**Aufbau:**

1. **Seite 1:** Banner und Bilder, Einladungstext, Datenschutzerklärung zum Bestätigen
2. **Auswahl:** Mit DPV-Account anmelden oder als Gast (wenn zugelassen); danach: mich selbst, meine Einheit (Personen auswählen) oder eine dritte Person
3. **Personendaten:** Standardblock pro Person, vorbefüllt aus dem Profil
4. **Gesundheitsblock** pro Person
5. **An- und Abreise** (optional) pro Anmeldung
6. **Zusatzfragen** der Veranstaltung
7. **Zusammenfassung und Absenden**

| ID | Anforderung | Priorität |
| --- | --- | --- |
| FRM-01 | Seite 1 zeigt Einladungstext und, falls vorhanden, Bilder (VER-06) und verlangt die Bestätigung der Datenschutzerklärung. Der Standardtext der Admins ist fest; die Veranstaltungsleitung kann einen eigenen Abschnitt ergänzen. | Muss |
| FRM-02 | Standardblock Person: Vorname, Nachname, Geburtsdatum und Einheit sind immer enthalten. Straße, Hausnummer, PLZ, Ort, Bundesland, Mail und Telefon sind pro Veranstaltung abwählbar (Standard: an). Beim Abwählen der Adresse weist das Tool darauf hin, dass Zuschusslisten sie meist benötigen. | Muss |
| FRM-03 | Daten bekannter Personen (Account, verwaltete Person, Adressbuch) werden aus dem Profil vorbefüllt und müssen nicht neu eingetippt werden. Gesundheitsangaben werden nur bei der Selbstanmeldung aus dem eigenen Profil vorbefüllt (FRM-04). | Muss |
| FRM-04 | Gesundheitsblock (pro Person, pro Veranstaltung abschaltbar, Standard: an): Ernährungsform (Einfachauswahl: alles, vegetarisch, vegan, kein Schweinefleisch …), Unverträglichkeiten und Allergien (Mehrfachauswahl: Laktose, Gluten/Zöliakie, Nüsse, Erdnüsse, Ei, Fisch …), Ankreuzfeld „lebensbedrohlich (z. B. Anaphylaxie)“, Medikamente, Freitext mit Hinweis „Bitte schwere Allergien und wichtige Details hier angeben“. Die Angaben werden pro Anmeldung gespeichert. Personen mit Account können ihre eigenen Angaben freiwillig im Profil speichern (Standard: aus), auch direkt aus der eigenen Anmeldung (Selbstanmeldung) über „Für künftige Anmeldungen speichern“; sie sind nur für sie selbst sichtbar, im Profil bearbeitbar, jederzeit löschbar und werden nur bei der Selbstanmeldung vorbefüllt. Gespeicherte Angaben werden regelmäßig automatisch gelöscht (Hinweis der Datenschutzperson vom 22.10.2026; Frist offen, wird beim Klären festgelegt). Im Profil verwalteter Personen werden keine Gesundheitsangaben gespeichert. Die Auswahllisten pflegen Admins zentral. Die Ernährungsform kann Rückschlüsse auf besonders geschützte Daten zulassen (z. B. Religion) und wird wie Gesundheitsdaten behandelt. | Muss |
| FRM-05 | Optionaler Block An- und Abreise: gilt pro Anmeldung, mit Option „einzelne Personen weichen ab“. | Soll |
| FRM-06 | Zusatzfragen pro Veranstaltung mit den Feldtypen: kurzer Text, langer Text, Einfachauswahl, Mehrfachauswahl, Ja/Nein, Zahl, Datum/Uhrzeit, Hinweistext, Bestätigungsfeld (muss angehakt werden, mit Text oder Link). Jedes Feld kann Pflicht sein. | Muss |
| FRM-07 | Feldtyp Mengenabfrage: Stückzahl pro Option (z. B. T-Shirts S: 2, M: 8, L: 5). | Soll |
| FRM-08 | Zusatzfragen gelten standardmäßig pro Anmeldung. | Muss |
| FRM-09 | Zusatzfragen können als „pro Person“ markiert werden. Beim Ausfüllen erscheinen sie als kompakte Tabelle (Zeile pro Person, Spalte pro Frage) mit Knopf „für alle übernehmen“. | Soll |
| FRM-10 | Visueller Formular-Baukasten: Blöcke hinzufügen, anordnen, Vorschau. | Soll |
| FRM-11 | Kostenpflichtige Optionen: Preis steht im Text der Option (z. B. „T-Shirt (+15 €)“), keine Berechnung. Der Platzhalter „Teilnahmebeitrag“ in Mails enthält diese Optionen nicht; die gewählten Optionen werden in der Mail aufgelistet. | Muss |
| FRM-12 | Optionen mit Preis, der automatisch zum Beitrag addiert und in Mails und Finanzen übernommen wird. | Kann |
| FRM-13 | Bedingte Fragen (z. B. „Größe?“ nur bei „T-Shirt: Ja“). | Kann |
| FRM-14 | Erklärungsbausteine (z. B. Fotoerklärung, Schwimmerklärung, Lagerregeln), von Admins zentral gepflegt, pro Veranstaltung an- oder abwählbar und bei der Anmeldung zu bestätigen. Pro Veranstaltung wird eine Kopie gespeichert; spätere Änderungen am Baustein wirken nicht auf bestehende Veranstaltungen. Wer mit einem Baustein nicht einverstanden ist, wählt ihn ab und nutzt ein eigenes Bestätigungsfeld (FRM-06). Setzt voraus: FRM-09 (für Bausteine pro Person). | Kann |

Weitere übliche Abfragen wie Notfallkontakt, Krankenversicherung, Ausweisnummer, Fotoeinwilligung oder Schwimmerlaubnis werden über Zusatzfragen und Bestätigungsfelder abgebildet, nicht als eigene Standardblöcke. Weil Zusatzfragen pro Person erst mit FRM-09 möglich sind, muss FRM-09 umgesetzt sein, bevor Veranstaltungen mit Sammelanmeldungen von Kindern über das Tool laufen.

## Anmeldung durchführen und bearbeiten

Wer eine Anmeldung abschickt, ist ihre Ansprechperson und kann sie bis zum Änderungsschluss über drei klar getrennte Vorgänge ändern. Danach ändert nur noch die Veranstaltungsleitung.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| ANM-01 | Bei einer Einladung wählt die Person: mich selbst anmelden, Personen meiner Einheit anmelden (je nach Rolle: Gruppe, Stamm, Ring, Bund; Auswahl aus den gespeicherten Personen; neue verwaltete Personen lassen sich dabei direkt anlegen, inkl. Bestätigung nach DSG-02) oder eine dritte Person anmelden (Daten für diese Anmeldung eingeben; Laden aus dem und Speichern im Adressbuch siehe PER-04). Die Verbandsleitung meldet keine Einheiten an. | Muss |
| ANM-02 | Es gibt nur namentliche Anmeldungen, keine Kontingente: Personen werden konkret mit ihren Daten angemeldet. Umfasst eine Anmeldung mehrere Personen, heißt sie Sammelanmeldung. | Muss |
| ANM-03 | **Ansprechperson-Prinzip:** Die anmeldende Person (Ansprechperson) bekommt alle Mails zur Anmeldung. Mitangemeldete Personen der eigenen Einheit bekommen keine Mails. Angemeldete Dritte bekommen die Mails zusätzlich, sofern eine Mailadresse angegeben ist. Gäste melden sich selbst an und sind ihre eigene Ansprechperson. | Muss |
| ANM-04 | **Gastanmeldung:** Zu Beginn wählt man „Mit DPV-Account anmelden“ (hervorgehoben, Standard) oder „Als Gast anmelden“ (nur wenn zugelassen). Gäste geben ihre Daten für diese eine Anmeldung ein. Eine Gastanmeldung umfasst genau eine Person. Bei Minderjährigen können Erziehungsberechtigte die Anmeldung ausfüllen und ihre eigene Mailadresse angeben. Im Gastformular steht: „Du hast einen DPV-Account? Dann melde dich lieber damit an, das geht schneller.“ Setzt voraus: VER-11. | Soll |
| ANM-05 | **Bearbeitungslink für Gäste:** persönlicher Link in der Bestätigungsmail zum Ändern oder Stornieren ohne Account. Bis dahin ändert die Veranstaltungsleitung auf Zuruf. Setzt voraus: ANM-04. | Kann |
| ANM-06 | Mitangemeldete Personen mit Account sehen die Anmeldung unter „Meine Anmeldungen“ („angemeldet durch …“) und dürfen ihre eigenen Angaben bis zum Änderungsschluss ändern. | Soll |
| ANM-07 | Dublettenprüfung: Personen mit Account werden über den Account erkannt, alle anderen über Vorname + Nachname + Geburtsdatum. Bei einem Treffer erscheint ein neutraler Hinweis („Eine Person mit diesen Daten ist möglicherweise bereits angemeldet. Bitte prüfe das oder wende dich an die Veranstaltungsleitung.“), keine Sperre. Wer die andere Anmeldung abgeschickt hat, sieht nur die Veranstaltungsleitung, außer beide Anmeldungen kommen aus derselben Einheit. Mögliche Dubletten sind für die Veranstaltungsleitung markiert. | Soll |
| ANM-08 | Bearbeiten einer bestehenden Anmeldung über drei Vorgänge: **Person hinzufügen** (Nachmeldung; auch nach dem Anmeldeschluss bis zum Änderungsschluss möglich; Kapazität und, falls aktiv, Warteliste gelten; für zeitliche Preisstufen zählt das Datum des Hinzufügens), **Person abmelden** (Stornoregeln und Nachrücken gelten, falls aktiv), **Angaben ändern** (z. B. Allergie, Anreise). Jeder Vorgang löst die passende Bestätigung und ggf. Benachrichtigung aus. | Muss |
| ANM-09 | Bis zum Änderungsschluss ändert die Ansprechperson selbst, danach nur die Veranstaltungsleitung. Die Veranstaltungsleitung kann jede Anmeldung jederzeit bearbeiten. | Muss |
| ANM-10 | Optionale Stornogebühren (Standard: aus) mit Staffeln nach Zeit, z. B. „ab 14 Tage vorher 50 %“. | Kann |
| ANM-11 | Profiländerungen und Anmeldungen: Ändert man ein Profil, fragt das Tool „Diese Person ist für 2 kommende Veranstaltungen angemeldet. Änderung dort übernehmen?“ Alle betroffenen Veranstaltungen sind vorausgewählt. Gilt nur für kommende Veranstaltungen bis zum jeweiligen Änderungsschluss. Gesundheitsangaben werden nicht aus dem Profil übernommen, sondern direkt in der Anmeldung geändert (ANM-12). | Soll |
| ANM-12 | Ausnahme Gesundheitsdaten (Allergien, Unverträglichkeiten, Medikamente): Die Ansprechperson kann sie auch nach dem Änderungsschluss bis zum Ende der Veranstaltung direkt in der Anmeldung ändern; Gäste wenden sich dafür an die Veranstaltungsleitung. Solche Änderungen werden in der Teilnehmendenliste als „geändert nach Änderungsschluss“ markiert, und die Veranstaltungsleitung wird immer benachrichtigt (BEN-02). | Muss |
| ANM-13 | Ist der Kontakt der Erziehungsberechtigten ausgefüllt, geht eine Kopie der Anmeldebestätigung bzw. der Absage an sie. Setzt voraus: PER-08. | Kann |

## Kapazität und Warteliste

Eine Veranstaltung kann eine Obergrenze haben. Ist sie voll, entscheidet der Wartelisten-Modus, ob und wie nachgerückt wird; Sammelanmeldungen rücken immer nur vollständig nach.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| KAP-01 | Optional eine maximale Teilnehmendenzahl für die gesamte Veranstaltung (nicht pro Einheit). Ist sie erreicht, erscheint ein deutlicher Hinweis; ohne aktive Warteliste ist die Anmeldung dann geschlossen. Passt eine Sammelanmeldung nicht mehr vollständig hinein, wird sie abgelehnt mit dem Hinweis: „Es sind nur noch 6 Plätze frei. Bitte melde weniger an oder wende dich an die Veranstaltungsleitung.“ | Muss |
| KAP-02 | Wartelisten-Modus pro Veranstaltung: **Aus** (Standard: Anmeldung geschlossen, nur Hinweis). Wird die Warteliste eingeschaltet, gilt standardmäßig **Manuell** (Eintrag auf Warteliste, Veranstaltungsleitung wird bei freien Plätzen benachrichtigt und entscheidet selbst, wer nachrückt). | Soll |
| KAP-03 | Sammelanmeldungen kommen nur vollständig auf die Warteliste und rücken nur vollständig nach. Hinweis bei der Anmeldung: „Für deine 10 Personen sind nur noch 6 Plätze frei. Die gesamte Anmeldung kommt auf die Warteliste. Alternativ kannst du weniger Personen anmelden.“ Setzt voraus: KAP-02. | Soll |
| KAP-04 | Modus **Automatisch:** Die Warteliste wird einmal täglich gesammelt abgearbeitet. Freie Plätze gehen an den ersten Eintrag, der vollständig hineinpasst; größere Einträge werden übersprungen und behalten ihren Platz. Nachgerückte werden per Pflichtmail informiert. Setzt voraus: KAP-02. | Kann |
| KAP-05 | Optionale Bestätigungsfrist beim Nachrücken (z. B. 3 Tage, von der Veranstaltungsleitung festgelegt). Ohne Bestätigung ist der nächste Eintrag dran. Setzt voraus: KAP-02. | Kann |

Wer eine strenge Reihenfolge ohne Überspringen will, wählt den manuellen Modus.

## Preise und Zahlungen

Der Beitrag ist ein fester Betrag, optional gestaffelt nach Entfernung des Stammes und nach Anmeldedatum. Bezahlt wird per Überweisung; das Tool liefert die Zahlungsangaben, verarbeitet aber kein Geld.

### Preise

| ID | Anforderung | Priorität |
| --- | --- | --- |
| PRE-01 | Fester Teilnahmebeitrag pro Person, angezeigt in Einladung, Anmeldung und Bestätigungsmail. | Muss |
| PRE-02 | Optionale Preisstufen nach Entfernung: Luftlinie zwischen der Adresse des Stammes, dem die Person angehört, und dem Veranstaltungsort, auch wenn die Person selbst woanders wohnt. Stufen sind feste Endpreise; es gilt die Stufe mit der größten Entfernung, die erreicht wird. Ziel ist eine faire Kostenverteilung. Setzt voraus: ORG-09. | Soll |
| PRE-03 | Personen ohne Stamm (Gäste, Dritte, Mitglieder direkt im Bund) wählen ihre Preisstufe bei der Anmeldung selbst, auf Vertrauensbasis. Die Veranstaltungsleitung kann korrigieren. Setzt voraus: PRE-02. | Soll |
| PRE-04 | Optionale zeitliche Stufen als fester Auf- oder Abschlag nach Anmeldedatum (z. B. „ab 01.06.: +10 €“, „Frühbucher bis 01.03.: −5 €“). Damit ist auch ein Nachmeldezuschlag abbildbar. Bei Nachmeldungen zählt das Datum des Hinzufügens. | Soll |

*Beispiel Entfernungsstufen:* bis 100 km 40 €, über 100 km 30 €, über 200 km 20 €. Ein Stamm in 250 km Entfernung zahlt 20 €; bei Anmeldung nach dem 01.06. mit +10 € Aufschlag 30 €.

### Zahlungen

| ID | Anforderung | Priorität |
| --- | --- | --- |
| ZAH-01 | Die Veranstaltungsleitung trägt einmal pro Veranstaltung Empfänger, IBAN und Zahlungsfrist ein. Die Bestätigungsmail enthält per Platzhalter Teilnahmebeitrag, Empfänger, IBAN, Verwendungszweck und Frist. Bis ZAH-02 umgesetzt ist, setzt der Platzhalter Verwendungszweck Veranstaltungsname und Name der Ansprechperson ein. | Muss |
| ZAH-02 | Das Tool erzeugt pro Anmeldung einen eindeutigen Verwendungszweck (z. B. „SIPPA26-WALHALL-0042“). | Soll |
| ZAH-03 | Zahlungsstatus pro Anmeldung (offen, bezahlt, Erstattung offen) von Hand pflegen: Übersicht mit Filtern (z. B. nach Bund, Stamm) und Mehrfachauswahl, um etwa „alle Anmeldungen des Stammes Walhall → bezahlt“ in einem Schritt zu setzen. Bis dahin laufen Zahlungsabgleich und Erstattungen außerhalb des Tools. | Kann |
| ZAH-04 | Rechnungsdokument (PDF) aus einer Standardvorlage, pro Person oder gesammelt pro Einheit (Gruppe, Stamm, Ring, Bund). Absender, Adresse und Bankverbindung füllt die Veranstaltungsleitung pro Veranstaltung aus. Fortlaufende Rechnungsnummern sind nicht nötig. | Kann |

## Kommunikation und Mails

Pflicht sind nur Bestätigungen und Mails, ohne die jemand etwas Wichtiges verpasst; alle anderen Mails sind optional. Entwicklungspriorität: manuelle Nachrichten vor zeitgesteuerten vor ereignisgesteuerten.

### Mails an Teilnehmende und Ansprechpersonen

| ID | Anforderung | Priorität |
| --- | --- | --- |
| MAIL-01 | Pflichtmails (nicht abschaltbar): Anmeldebestätigung, Bestätigung einer Änderung, Nachgerückt/Platz frei (sofern Warteliste aktiv), Veranstaltung abgesagt. Inhalt veranstaltungsspezifisch über Vorlagen. Sobald ANM-05 kommt, enthält die Gastbestätigung den Bearbeitungslink. | Muss |
| MAIL-02 | Ankündigungsmail an den Benachrichtigungskreis, sobald die Veranstaltung veröffentlicht wird. Nie an „alle“. | Muss |
| MAIL-03 | Manuelle Nachrichten: Die Veranstaltungsleitung schreibt frei an alle Ansprechpersonen, die gewählten Kriterien entsprechen (z. B. Bund, Stamm, Warteliste, sofern aktiv). | Muss |
| MAIL-04 | Automatische Mails nach Zeit, relativ zu Fristen der Veranstaltung (z. B. „3 Tage vor Anmeldeschluss“, „7 Tage vor Ende der kostenlosen Stornierung“, „7 Tage vor Beginn“), mit Standardvorlagen und Empfängerfiltern. Es gilt jeweils der aktuelle Stand der Fristen. Alle optional, standardmäßig aus. | Soll |
| MAIL-05 | Automatische Mails nach Ereignis (z. B. „50 % der Plätze belegt“). | Kann |
| MAIL-06 | Admins pflegen Standardvorlagen für alle automatischen Mails. Pro Veranstaltung werden sie kopiert und dort bearbeitet; spätere Änderungen an der Vorlage wirken nicht auf bestehende Veranstaltungen. | Muss |
| MAIL-07 | Einfacher Editor im Tool mit Platzhalter-Auswahl per Klick und Vorschau mit Beispieldaten. Kein Word-Import. | Muss |
| MAIL-08 | Eigene Vorlagen für Bünde und Stämme. | Kann |
| MAIL-10 | In manuellen Nachrichten (MAIL-03) und in der Teilnehmendenliste (LIS-01) nach Zahlungsstatus filtern, z. B. für Zahlungserinnerungen. Setzt voraus: ZAH-03. | Kann |
| MAIL-09 | Schlichtes, einheitliches Mail-Layout, optional mit dem Banner der Veranstaltung im Kopf. | Soll |

**Platzhalter:** Vor- und Nachname der Ansprechperson, Liste der angemeldeten Personen, Name der Veranstaltung, Beginn, Ende, Ort und Adresse, Teilnahmebeitrag gesamt und pro Person, gewählte kostenpflichtige Optionen, Empfänger, IBAN, Verwendungszweck, Zahlungsfrist, Anmeldeschluss, Änderungsschluss, Link zur Anmeldung, Name und Mail der Veranstaltungsleitung.

### Benachrichtigungen für die Veranstaltungsleitung

Benachrichtigungen enthalten keine Gesundheitsdaten, nur einen Hinweis mit Link ins Tool, z. B. „Bei 1 Anmeldung zur Sippenaktion wurden Gesundheitsangaben nach dem Änderungsschluss geändert.“ Die genaue Ausgestaltung ist offen (OP-7).

| ID | Anforderung | Priorität |
| --- | --- | --- |
| BEN-01 | Standardmäßig keine Benachrichtigungen. Jede Person aus der Leitung wählt selbst Ereignisse (neue Anmeldung, Absage, geänderte Allergie, Zahlungseingang, Platz frei …) und Weg: Mail einzeln, Mail als tägliche Zusammenfassung oder Benachrichtigung im Tool. | Soll |
| BEN-02 | Einzige Pflichtbenachrichtigung: Gesundheitsdaten wurden nach dem Änderungsschluss geändert (siehe ANM-12). | Muss |
| BEN-03 | Weitere Kanäle wie Push-Nachrichten oder Messenger (z. B. Signal). Setzt voraus: BEN-01. | Kann |

## Listen, Exporte und Auswertungen

Die Veranstaltungsleitung arbeitet mit einer filterbaren Teilnehmendenliste im Tool und exportiert alles Weitere (Check-in-, Abhak-, Zuschusslisten) mit frei wählbaren Spalten.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| LIS-01 | Teilnehmendenliste im Tool, filter- und sortierbar (Bund, Stamm, Alter, Status, „geändert nach Änderungsschluss“; Warteliste und mögliche Dubletten, sofern umgesetzt). Lebensbedrohliche Allergien sind hervorgehoben. | Muss |
| LIS-02 | Export als Excel und CSV mit frei wählbaren Spalten. Spaltenauswahlen lassen sich als Exportvorlage speichern (z. B. „Check-in-Liste“). Enthält ein Export Gesundheitsspalten, erscheint der Hinweis „Diese Datei enthält Gesundheitsdaten. Gib sie nur an Personen weiter, die sie brauchen, und lösche sie nach der Veranstaltung.“; der Export wird protokolliert (wer, wann). | Soll |
| LIS-03 | Fertige Exportvorlage für Zuschusslisten (z. B. KJP-Listen), nutzbar als Abhakliste. Setzt voraus: LIS-02. | Soll |
| LIS-04 | Küchenübersicht: Anzahlen pro Ernährungsform und Unverträglichkeit, wenn möglich pro Tag bzw. Mahlzeit anhand der An- und Abreise (z. B. „Freitagabend: 640 × alles, 280 × vegetarisch, 80 × vegan, 12 × glutenfrei“). Lebensbedrohliche Allergien sind hervorgehoben. Dazu eine fertige Exportvorlage „Küchenliste“: oben die Anzahlen, darunter Name, Einheit, Ernährungsform, Unverträglichkeiten, Kennzeichen „lebensbedrohlich“ und Freitext, ohne Medikamente. Setzt voraus: LIS-02 (für die Küchenliste). | Soll |
| LIS-05 | Statistiken im Tool (Anmeldungen über die Zeit, Verteilung nach Bünden, Altersstruktur). | Kann |
| LIS-06 | Digitaler Check-in vor Ort (z. B. per Handy oder QR-Code). | Kann |

## Finanzmodul

Das gesamte Finanzmodul ist ein Kann: eine rudimentäre Kalkulation mit Soll-Ist-Vergleich, sichtbar nur für die Veranstaltungsleitung.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| FIN-01 | Erwartete Einnahmen werden automatisch aus den Anmeldungen berechnet (Anzahl × Beitrag je Preisstufe). Weitere Einnahmen wie Zuschüsse, Spenden oder Verkäufe werden von Hand ergänzt. | Kann |
| FIN-02 | Budget mit frei wählbaren Kategorien (z. B. Küche, Programm, Technik) und geplantem Betrag je Kategorie. | Kann |
| FIN-03 | Ausgaben erfassen: Datum, Betrag, Kategorie, Beschreibung und die Person, die das Geld ausgelegt hat. Kein Upload von Belegen. | Kann |
| FIN-04 | Erstattungsstatus pro Ausgabe („ausgelegt“ → „erstattet“), damit klar ist, wem noch Geld zurücküberwiesen werden muss. Setzt voraus: FIN-03. | Kann |
| FIN-05 | Soll-Ist-Vergleich pro Kategorie und gesamt, als Tabelle und Grafik. Setzt voraus: FIN-02, FIN-03. | Kann |
| FIN-06 | Schnittstelle zum Ausgabentool des DPV, das erfasste Ausgaben direkt übermittelt (siehe OP-3). Setzt voraus: FIN-03. | Kann |

## Dashboard und Kalender

Nach dem Login landet jede Person auf einem festen Dashboard, das sich automatisch an ihre Rolle anpasst: Wer nur teilnimmt, sieht Anmeldungen und offene Einladungen, wer leitet, zusätzlich die eigenen Veranstaltungen. Die optische Gestaltung wird separat geplant.

Reihenfolge von oben nach unten (auch auf dem Handy):

1. **Was ist zu tun?** (nur wenn es etwas gibt), z. B. „Anmeldeschluss Sippenaktion in 3 Tagen“, „4 Personen in Stamm Walhall seit 2 Jahren inaktiv“, „Du bist von der Warteliste nachgerückt“
2. **Schnellzugriffe:** Anmelden, Veranstaltung planen, Meine Leute (nur Leitungen), Kreise
3. **Meine Anmeldungen:** Veranstaltung, Datum, Anzahl Personen, Status, Knopf „Bearbeiten“
4. **Meine Veranstaltungen** (nur wenn ich leite): Status, Anmeldungen im Verhältnis zur Kapazität, nächste Frist, Knopf „Verwalten“
5. **Offene Anmeldungen für mich**, sortiert nach Anmeldeschluss
6. **Kalender** mit Veranstaltungen und Anmeldephasen

| ID | Anforderung | Priorität |
| --- | --- | --- |
| DSH-01 | Festes Dashboard mit den Bereichen oben, rollenabhängig eingeblendet. | Muss |
| DSH-02 | Bereich „Was ist zu tun?“ mit Hinweisen und direkten Links. | Soll |
| DSH-03 | Schnellzugriffe auf die zentralen Funktionen. | Muss |
| DSH-04 | „Meine Anmeldungen“, inklusive Anmeldungen, bei denen ich mit angemeldet wurde. | Muss |
| DSH-05 | „Meine Veranstaltungen“ mit Kurzstatus. | Muss |
| DSH-06 | „Offene Anmeldungen“: alle Veranstaltungen, in deren Teilnahmekreis ich bin und deren Anmeldung offen ist. | Muss |
| DSH-07 | Kalender (Handy: Liste der nächsten Termine, PC: Monatsansicht) mit Veranstaltungen und Anmeldephasen. | Soll |
| DSH-08 | Bausteine des Dashboards ein- und ausblenden. | Kann |
| DSH-09 | Kalenderdatei (.ics) pro Veranstaltung herunterladen. | Kann |

## Eigene Kreise

Neben der festen Hierarchie kann jede Person eigene Kreise bilden, etwa Arbeitskreise oder Planungsteams. Sie dienen als Teilnahme- und Benachrichtigungskreise und können bundesübergreifend sein; die Generalprobe braucht sie für das Planungsteam.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| GRP-01 | Jede Person mit Account kann einen Kreis erstellen, gehört automatisch zu den Verwaltenden des Kreises und kann weitere Verwaltende benennen. Mitglieder sind nur Personen mit Account. | Muss |
| GRP-02 | **Privater Kreis:** für andere unsichtbar. Mitglieder kommen nur hinein, wenn die Verwaltenden sie aktiv hinzufügen; sie werden darüber benachrichtigt. Kein Einladungslink. | Muss |
| GRP-03 | **Öffentlicher Kreis:** für alle sichtbar, jede Person kann beitreten; optional müssen die Verwaltenden den Beitritt bestätigen. | Soll |
| GRP-04 | Mitglieder können einen Kreis jederzeit verlassen. | Muss |

## Ortsverzeichnis

Aus einer einfachen Adresseingabe soll schrittweise ein gemeinsames Verzeichnis und langfristig eine Lagerplatz- und Häuserdatenbank des Verbands werden.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| ORT-02 | Gemeinsames Ortsverzeichnis für den Verband. Pflichtangaben: Bezeichnung und Adresse. Gespeicherte Orte sind bei neuen Veranstaltungen auswählbar. | Soll |
| ORT-03 | Jeder Ort wird von einer Person oder einer Einheit verwaltet (bei einer Einheit von all ihren Leitungen) und ist entweder privat oder für alle freigegeben. Andere dürfen freigegebene Orte nutzen, aber nicht bearbeiten. Setzt voraus: ORT-02. | Soll |
| ORT-04 | Veranstaltungen speichern die Ortsdaten zum Zeitpunkt der Auswahl. Ändert sich ein Ort, bleiben bestehende Veranstaltungen unverändert; die Leitung kommender Veranstaltungen wird gefragt, ob sie die Änderung übernehmen möchte. Setzt voraus: ORT-02. | Soll |
| ORT-05 | Funktion „Änderung melden“, mit der Nutzende die Verwaltenden eines Ortes auf veraltete Daten hinweisen. Setzt voraus: ORT-02. | Kann |
| ORT-06 | Lagerplatz- und Häuserdatenbank mit erweiterten Infos: Ansprechperson, Kapazität, Ausstattung (Küche, Strom, Wasser, Feuerstelle), Notizen, ggf. Bilder. Setzt voraus: ORT-02. | Kann |

## Datenschutz, Aufbewahrung und Löschung

Ein großer Teil der Daten betrifft Minderjährige und Gesundheitsangaben. Deshalb gilt: Einwilligung dokumentieren, Gesundheitsdaten pro Anmeldung speichern (im eigenen Profil nur freiwillig, siehe FRM-04), Anmeldedaten 6 Monate nach der Veranstaltung anonymisieren, inaktive Profile regelmäßig prüfen.

Das Tool unterscheidet zwei Verarbeitungen: die **Anmeldung zu einer Veranstaltung** (abgedeckt durch die Datenschutzerklärung der Veranstaltung, gelöscht nach 6 Monaten) und die **dauerhafte Speicherung im Profil** einer Einheit (abgedeckt durch eine separate Einwilligung, z. B. über den Mitgliedsantrag des Stammes). Hinzu kommt die freiwillige Speicherung eigener Gesundheitsangaben im Profil einer Person mit Account (FRM-04); die Datenschutzperson des DPV hält freiwillige Angaben im eigenen Profil für in Ordnung, bei regelmäßiger automatischer Löschung (22.10.2026). Ab welchem Alter Personen mit Account selbst einwilligen können, ist noch offen (OP-2).

| ID | Anforderung | Priorität |
| --- | --- | --- |
| DSG-01 | Bei jeder Anmeldung wird die Datenschutzerklärung der Veranstaltung bestätigt. Bei Sammelanmeldungen bestätigt die anmeldende Leitung stellvertretend: „Ich bestätige, dass die angemeldeten Personen bzw. ihre Erziehungsberechtigten der Teilnahme und der Verarbeitung ihrer Daten für diese Veranstaltung zugestimmt haben.“ Die Verantwortung liegt bei der anmeldenden Leitung; gespeichert wird, wer wann bestätigt hat. Die Datenschutzperson des DPV hält diese Abfrage für ausreichend (22.10.2026: Vertrauen statt übermäßiger Kontrolle) und regt an, zusätzlich abzufragen, dass die Personen die Teilnahmekriterien erfüllen; der Wortlaut wird beim Klären festgelegt. Dass Erziehungsberechtigte zusätzlich selbst bestätigen, etwa über einen Link der Leitung, ist als Idee vorgemerkt (#44). | Muss |
| DSG-02 | Beim Anlegen einer verwalteten Person bestätigt die Leitung: „Die Person bzw. bei Minderjährigen die Erziehungsberechtigten haben der Speicherung der Daten zugestimmt.“ Das Tool speichert, wer wann bestätigt hat. Die Bestätigung als Abfrage genügt laut Datenschutzperson des DPV (22.10.2026; Auslegung der Antwort zu DSG-01). Die Einwilligung gilt nach Volljährigkeit fort; keine erneute Bestätigung (Annahme, dazu steht die Antwort noch aus, siehe OP-2). | Muss |
| DSG-03 | Anmeldedaten bleiben 6 Monate nach Ende der Veranstaltung vollständig erhalten. 30 Tage vor der Anonymisierung wird die Veranstaltungsleitung informiert und an das Löschen eigener Exporte erinnert. Nach 6 Monaten wird automatisch archiviert: Personendaten werden anonymisiert, nur Statistiken bleiben (Anzahl gesamt, pro Einheit, ggf. Altersverteilung). Im Profil bleibt nur das Datum der letzten Teilnahme. Exporte und Ausdrucke, z. B. für Zuschussabrechnungen, bewahren die Veranstaltenden nach den Regeln der jeweiligen Abrechnung außerhalb des Tools auf. | Muss |
| DSG-04 | Die Veranstaltungsleitung kann eine Veranstaltung jederzeit endgültig löschen. Gibt es Anmeldungen und ist die Veranstaltung nicht beendet, fragt das Tool: „Sollen die bereits angemeldeten Personen informiert werden?“ (vorausgewählt: ja); dann wird die Absagemail verschickt. | Muss |
| DSG-05 | Die Archivierung kann einmalig um 6 Monate verlängert werden, mit Begründung (z. B. offene Zuschussabrechnung, Versicherungsfall). | Kann |
| DSG-06 | Finanzdaten bleiben nach der Archivierung erhalten; Personenbezüge (z. B. „Auslage von …“) werden anonymisiert. Setzt voraus: FIN-03. | Kann |
| DSG-07 | Wurde eine verwaltete Person 2 Jahre zu keiner Veranstaltung angemeldet, fragt das Tool die zuständigen Leitungen, ob sie noch aktiv ist (bestätigen oder löschen). Keine automatische Löschung. Grundlage ist das Datum der letzten Teilnahme im Profil (DSG-03). | Soll |
| DSG-08 | Entwicklung und Tests nur mit erfundenen Testdaten; echte Personendaten erst auf den DPV-Servern. Echte Personendaten gelangen nie in KI-Werkzeuge, auch nicht im Betrieb oder zur Fehlersuche. | Muss |
| DSG-09 | **Betroffenenrechte**: Personen mit Account sehen ihre Daten im Profil und unter „Meine Anmeldungen“ und können ihr Profil selbst löschen. Für verwaltete Personen wenden sich Erziehungsberechtigte an die Leitung der Einheit; ein Widerruf der Einwilligung führt zur Löschung des Profils, aktive Anmeldungen werden auf Wunsch storniert. Weitere Anfragen (Auskunft, Berichtigung) bearbeitet ein Admin. | Muss |
| DSG-10 | Datenexport der eigenen Daten per Knopfdruck. | Kann |

Die Datenschutzperson des DPV hat das Einwilligungsmodell am 22.10.2026 im Grundsatz bestätigt: nach bestem Wissen umsetzen, handhabbar und brauchbar bleiben, Vertrauen statt übermäßiger Kontrolle. Verantwortlich im Sinne der DSGVO ist der DPV als Betreiber. Was noch offen ist, steht unter OP-2.

## Administration

Admins betreuen das System technisch und pflegen die zentralen Vorgaben. Zu Beginn ist der Entwickler einziger Admin; ein zweiter Admin wird benannt (empfohlen, keine Pflicht).

| ID | Anforderung | Priorität |
| --- | --- | --- |
| ADM-01 | Admins ernennen und entfernen. | Muss |
| ADM-02 | Zentrale Pflege von Ernährungs-Auswahllisten, Standard-Mailvorlagen und Standard-Datenschutzerklärung. | Muss |
| ADM-03 | Einsicht in Protokolle (Rollenänderungen, Strukturänderungen, Kontosuchen, Admin-Zugriffe auf Personendaten, Exporte mit Gesundheitsdaten). Das Protokoll der Admin-Zugriffe kann auch die Verbandsleitung einsehen; es nennt Zeitpunkt, Admin, Art des Zugriffs und Bereich, aber keine Namen einzelner Personen. Das Protokoll der Kontosuchen nennt Zeitpunkt, suchende Person und gefundenes Konto oder „kein Treffer“, aber nie den Suchbegriff; es erfasst alle Suchen ohne Treffer und alle Suchen, deren Treffer außerhalb des eigenen Bereichs liegt. | Soll |
| ADM-04 | Eingreifen bei Missbrauch, z. B. eine Veranstaltung sperren. | Soll |
| ADM-05 | Systemweite Hinweise anzeigen, z. B. „Am Sonntag 20–22 Uhr Wartungsarbeiten“. | Soll |
| ADM-06 | Nutzungsstatistik: Anzahl Veranstaltungen, Anmeldungen, aktive Accounts. | Kann |
| ADM-07 | Hat eine Veranstaltung keine Veranstaltungsleitung mehr (z. B. nach Austritt aus dem DPV), weisen Admins auf Anfrage eine neue zu. Die Zuweisung wird protokolliert (BER-02). | Soll |

## Nicht-funktionale Anforderungen

Das Tool ist eine deutschsprachige Web-Anwendung für Handy und PC, läuft auf DPV-Servern und ist so gebaut, dass eine Person es dauerhaft betreiben kann.

| ID | Anforderung | Priorität |
| --- | --- | --- |
| NFA-01 | Web-Anwendung im Browser, vollständig auf Handy und PC bedienbar (responsiv). Keine App im App Store. | Muss |
| NFA-02 | Oberfläche nur auf Deutsch; Texte nicht fest im Code verteilt, damit eine spätere Übersetzung möglich bleibt. | Muss |
| NFA-03 | Grundlegende Barrierefreiheit von Anfang an: gut lesbare Schrift, ausreichende Kontraste, beschriftete Formularfelder, Bedienung per Tastatur, verständliche Fehlermeldungen, keine Information nur über Farbe. | Muss |
| NFA-04 | Formale Prüfung nach WCAG 2.1 AA und Optimierung für Screenreader. | Kann |
| NFA-05 | Leistung für das Mengengerüst: bis ca. 100 gleichzeitige Nutzende in Spitzenzeiten (z. B. kurz vor Anmeldeschluss des Verbandslagers), Veranstaltungen bis ca. 5.000 Teilnehmende, mehrere Tausend Mails pro Veranstaltung. | Muss |
| NFA-06 | Betrieb auf DPV-Servern ab der ersten vorzeigbaren Version; Serverstandort Deutschland oder EU; regelmäßige Backups (siehe OP-4). | Muss |
| NFA-07 | Verfügbarkeit: kurze Ausfälle sind vertretbar, Datenverlust nicht. Keine geplanten Wartungen in den 48 Stunden vor einem Anmelde- oder Änderungsschluss von Veranstaltungen mit mehr als 100 Anmeldungen. | Muss |
| NFA-08 | Wartbarkeit: verständliche Dokumentation für Betrieb und Weiterentwicklung, damit eine zweite Person das Tool übernehmen kann. | Soll |
| NFA-09 | Oberflächentexte, Mailvorlagen und die Standard-Datenschutzerklärung sind gendersensibel formuliert. | Muss |
| NFA-10 | Grundlegende Sicherheit: mehrstufige Anmeldung für Admins, Sicherheitsupdates zeitnah eingespielt, keine Passwörter oder Schlüssel im Code, ein veröffentlichter Meldeweg für Sicherheitslücken. | Muss |

## Offene Punkte und Risiken

Vier Klärungen mit dem DPV bestimmen, wie viel das Tool selbst verwalten muss; die größten Risiken sind die Abhängigkeit von einer Person und der Umfang.

### Offene Punkte

- [ ] **OP-1 Keycloak:** Entschieden am 20.10.2026: Struktur, Rollen und Kreise pflegt das Tool selbst; Keycloak dient nur dazu, Personen zu verifizieren. Ein Lesekonto gibt es nicht. Laut Sebastian (20.10.2026) ist die Selbstregistrierung erlaubt; Benutzername und Mail sind bei jedem Konto vorhanden und ändern sich nicht, Vor- und Nachname können fehlen oder sich ändern. Auskunft des DPV-Admins vom 21.10.2026: Er kann einen Test-Client anlegen. Eine Meldung gelöschter oder gesperrter Konten kennt er nicht; das Tool merkt es wahrscheinlich erst, wenn der Login bei Keycloak scheitert. Keycloak erhebt kein Alter. Entschieden am 21.10.2026: Der Test-Client kommt in einen eigenen Test-Realm mit erfundenen Konten. Offen: Einrichtung des Test-Clients, später Schreibrechte für ORG-04 Variante A. Dass Keycloak kein Alter kennt, gehört zur Prüfung, ob Personen mit Account selbst einwilligen dürfen (OP-2). Klärung mit den Keycloak-Verantwortlichen.
- [ ] **OP-2 Datenschutz:** Antworten der Datenschutzperson des DPV vom 22.10.2026: Verantwortlich im Sinne der DSGVO ist der DPV als Betreiber. Die stellvertretende Bestätigung als Abfrage genügt (DSG-01, DSG-02). Freiwillige Gesundheitsangaben im eigenen Profil sind in Ordnung, bei regelmäßiger automatischer Löschung (FRM-04). Die Verträge zur Auftragsverarbeitung (u. a. Microsoft Azure, Google Workspace) liegen vor; Google Workspace soll laut Datenschutzperson DSGVO-konform sein. Das Tool bekommt ein eigenes Impressum und eine eigene Datenschutzerklärung (#12). Noch offen: ob eine Datenschutz-Folgenabschätzung (Art. 35 DSGVO) vor dem Bau des Gesundheitsblocks nötig ist; ab welchem Alter Personen mit Account selbst einwilligen können (Keycloak kennt kein Alter); ob die Einwilligung nach Volljährigkeit fortgilt (DSG-02); Verzeichnis der Verarbeitungen und Meldeweg für Datenpannen (72 Stunden); ob das Fehlerprotokoll einen Bezug zum Konto braucht (#11); ob für Entwicklung und Betrieb des Tools ein eigener Vertrag mit dem DPV nötig ist (früher hier als „Vertrag zur Auftragsverarbeitung mit dem DPV“ genannt).
- [ ] **OP-3 Ausgabentool:** Welches Ausgabentool nutzt der DPV, und hat es eine Schnittstelle (FIN-06)?
- [ ] **OP-4 Betrieb:** Mit der DPV-IT Serverstandort, Mailversand (über das Google Workspace des DPV, wenn technisch möglich; Limits für Massenmails), Backups (verschlüsselt, an einem zweiten Ort, Zurückspielen geübt, Aufbewahrung passend zur 6-Monats-Anonymisierung) und eine Ansprechperson für den Betrieb klären. Auskunft des DPV-Admins vom 21.10.2026: Er ist die Ansprechperson für den Betrieb. Der Produktivserver läuft mit Docker Compose bei Azure, PostgreSQL läuft dort; Mails gehen über das SMTP-Relay von Google Workspace, für das der Server freigeschaltet ist. Einen Testserver gibt es nicht; die Testumgebung läuft getrennt auf dem Produktivserver (`docs/entscheidungen.md`, 21.10.2026). Offen: Region bei Azure, Fassung von PostgreSQL, Backups, Aufbewahrung, Absenderkonto, Limits für Massenmails, SPF und DKIM.
- [ ] **OP-5 Optik:** Optische Planung von Dashboard, Einladungsseite und Formular-Baukasten.
- [ ] **OP-6 Prioritäten prüfen:** Prioritäten, die im Interview nicht ausdrücklich festgelegt wurden (u. a. ORG-04, ORG-08, PER-04 bis PER-06, VER-06, VER-10, PRE-02 bis PRE-04, DSH-02, DSH-07), werden nach Abschluss der Muss-Anforderungen neu bewertet. Dabei auch prüfen: ROL-04 früh einplanen (entschieden am 20.10.2026: das Protokoll in P2, die Benachrichtigung in P8); FRM-12 vorziehen, falls das Verbandslager kostenpflichtige Optionen anbietet.
- [ ] **OP-7 Benachrichtigungen:** Genaue Ausgestaltung von BEN-01 bis BEN-03: Ereignisse, Inhalte (ohne Gesundheitsdaten) und Kanäle.

### Risiken

| Risiko | Auswirkung | Gegenmaßnahme |
| --- | --- | --- |
| Eine Person trägt Entwicklung und Betrieb | Ausfall oder Burnout gefährdet das Tool, wie beim Biber | zweiter Admin, Dokumentation (NFA-08), strenge Priorisierung |
| Umfang wächst zum Großprojekt | Muss-Funktionen werden nicht rechtzeitig fertig | Muss/Soll/Kann konsequent einhalten; nach Abschluss der Muss-Anforderungen Soll und Kann neu bewerten und schrittweise umsetzen |
| Tool pflegt Struktur und Rollen selbst (OP-1, entschieden am 20.10.2026) | Mehr Pflegeaufwand für Leitungen und Admins | ORG-06 ist als Muss eingeplant |
| Leitungen ohne Account | Einheiten können nicht selbst anmelden | nächsthöhere Ebene springt ein (PER-07) |
| Sensible Daten von Minderjährigen | Rechtliche und vertrauensbezogene Folgen bei Fehlern | OP-2, Gesundheitsdaten pro Anmeldung und nie im Profil verwalteter Personen, Protokollierung, Anonymisierung, keine Echtdaten lokal |
| Erster Großeinsatz mit 5.000 Personen | Fehler treffen viele Menschen | Generalproben bei den Vorbereitungstreffen, Pilotphase mit mehreren Veranstaltungstypen |
| Bis TEAM-02 sieht jede Veranstaltungsleitung Gesundheitsdaten | Bei großen Lagern sehen viele Personen sensible Daten | Leitungsteam klein halten, Küchenliste statt Vollzugriff (LIS-04) |
| Rollenvergaben sind bis ROL-04 nicht nachvollziehbar | Unbemerkter Zugriff auf Daten von Kindern | Vertrauensprinzip; das Protokoll der Rollenänderungen (ROL-04) kommt in P2, vor echten Daten (entschieden am 20.10.2026) |
| Abhängigkeit von KI-Werkzeugen | Werkzeug wird teurer, ändert sich oder fällt weg; Fehler werden nicht erkannt | Regeln werkzeugneutral dokumentiert, Projekt ohne KI start- und testbar, menschliche Prüfung kritischer Änderungen, Lernpfad |
| Kein äußerer Termindruck bis zur Generalprobe | Projekt zerfasert, Soll und Kann rutschen vor die Muss-Anforderungen | selbst gesetzte Meilensteine mit echten Veranstaltungen; erst alle Muss, dann Soll und Kann neu bewerten |

## Glossar

| Begriff | Bedeutung |
| --- | --- |
| Admin | Technische Betreuung des Tools mit Vollzugriff für Support |
| Ansprechperson | Person, die eine Anmeldung abschickt; bekommt alle Mails dazu |
| Anmeldeschluss | Ende des Zeitraums für neue Anmeldungen |
| Änderungsschluss | Ende des Zeitraums, in dem Ansprechpersonen bestehende Anmeldungen ändern und Personen nachmelden dürfen |
| Benachrichtigungskreis | Personen, die per Mail über eine neue Veranstaltung informiert werden |
| DPV-Veranstaltungsteam | Von der Verbandsleitung benannte Rolle, die bundesübergreifende Einheiten, Rollen und „alle“ als Teilnahmekreis wählen darf; für Kreise gilt BER-04 |
| Eigener Kreis | Frei gebildeter Personenkreis außerhalb der Hierarchie, z. B. Arbeitskreis, Planungsteam; kann bundesübergreifend sein |
| Einheit | Organisationseinheit: Verband, Bund, Ring, Stamm oder Gruppe |
| Gast | Person ohne Account und ohne gespeichertes Profil, angemeldet zu einer einzelnen Veranstaltung |
| Gruppe | Unterste Einheit der Hierarchie, frei benannt (z. B. Meute, Sippe, Runde) |
| Keycloak | Zentrales Login-System des DPV |
| Leitungsteam | Alle Personen, die eine Veranstaltung mitleiten |
| Persönliches Adressbuch | Nur für die besitzende Person sichtbare Liste externer Personen |
| Sammelanmeldung | Anmeldung mehrerer Personen durch eine Ansprechperson |
| Teilnahmekreis | Personen, die eine Veranstaltung sehen und sich anmelden dürfen |
| Veranstaltungsleitung | Person im Leitungsteam einer Veranstaltung mit allen Rechten |
| Verwaltete Person | Profil ohne Account, das einer Einheit gehört und von deren Leitungen gepflegt wird |
| Warteliste | Liste für Anmeldungen, wenn die Kapazität erreicht ist |
