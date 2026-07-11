# Frontier Command Online – Build 31

## Öffentlicher Online-Multiplayer

Das Paket enthält eine `render.yaml` für ein öffentliches Deployment. Sie erstellt einen WebSocket-Spielserver und einen separaten Player-Wins-Speicher. Nach dem Deployment öffnen alle Spieler dieselbe öffentliche HTTPS-Adresse; eine Serveradresse muss im Spiel nicht eingegeben werden.

1. Dateien in ein GitHub-Repository hochladen.
2. Im Render-Dashboard `New` → `Blueprint` auswählen.
3. Das Repository verbinden und die `render.yaml` bestätigen.
4. Die erzeugte `onrender.com`-Adresse mit allen Spielern teilen.

## Start

1. Installiere Node.js 20 oder neuer.
2. Öffne in diesem Ordner ein Terminal.
3. Führe `npm install` aus.
4. Starte den Server mit `npm start`.
5. Öffne `http://localhost:8080` im Browser.

Für Spieler aus dem Internet muss Port 8080 erreichbar sein oder der Server auf einem Node.js-Host betrieben werden. Hinter einem HTTPS-Reverse-Proxy wird automatisch eine sichere WebSocket-Verbindung verwendet.

## Enthalten

- Echtes WebSocket-Matchmaking ohne Bots für 1v1, 3v3 und 5v5
- Start erst bei exakt 2, 6 oder 10 verbundenen Spielern
- Autoritative Server-Simulation für Bewegung, Kampf, Basen, Einkommen und Produktion
- Dauerhafte Top-100-Rangliste nach Player-Wins in `data/player-wins.json`
- Allianzanfragen, Annahme, Ablehnung und Auflösung während einer Partie
- Serverseitige Prüfung von Einheitenbesitz, Kosten, Limits und Befehlen
- Automatischer Sieg bei zerstörter Basis oder vollständig getrenntem Gegnerteam

## Produktion

Die lokale Profil-ID dient in diesem Prototyp als Spielerkennung. Für einen öffentlichen Wettbewerbsserver sollten vor dem großen Einsatz serverseitige Konten, TLS, Datenbank-Backups, Moderation und zusätzliche Anti-Cheat-Prüfungen ergänzt werden.
