# Webfix

Chat-Anwendung mit Web- und Desktop-Client.

| Teil | Pfad | Technik |
|---|---|---|
| Server / API | [app/](app/) | Python, FastAPI, PostgreSQL |
| Web-Frontend | [frontend/](frontend/) | Angular (wird ins Container-Image eingebaut) |
| Desktop-Client | [WebfixClient/](WebfixClient/) | Qt 6 (Widgets, Network, WebSockets) |

## Downloads

Es gibt immer nur die neueste Version:

- **Container:** `ghcr.io/<user>/webfix:latest`
- **Windows (x64):** [WebfixClient-windows-x64.zip](https://github.com/<user>/webfix/releases/latest/download/WebfixClient-windows-x64.zip)
- **macOS (Apple Silicon):** [WebfixClient-macos-arm64.dmg](https://github.com/<user>/webfix/releases/latest/download/WebfixClient-macos-arm64.dmg)

Die macOS-App ist nicht notarisiert. Nach dem ersten Startversuch unter **Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“** erlauben, oder einmalig im Terminal:

```
xattr -cr /Applications/WebfixClient.app
```

## Server betreiben

Die Konfiguration kommt über Umgebungsvariablen aus einer `.env`. Eine Beispieldatei liegt unter [env](env):

```
cp env .env        # Werte anpassen
docker compose up -d
```

Es gibt zwei Varianten:

| Datei | Container |
|---|---|
| [docker-compose.yml](docker-compose.yml) | wird lokal gebaut, `./app` ist eingebunden (Entwicklung) |
| [docker-compose.github.yml](docker-compose.github.yml) | fertiges Image `ghcr.io/<user>/webfix:latest`, bei jedem Start aktualisiert |

```
docker compose -f docker-compose.github.yml up -d
```

Die App läuft auf Port `8000`, die Datenbank (PostgreSQL 16) speichert ihre Daten in `./pgdata`.

### Reverse Proxy (nginx)

Für HTTPS gehört ein nginx vor die App. `/api/stream/` ist eine WebSocket-Verbindung und braucht deshalb die `Upgrade`-Header und lange Timeouts.

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name chat.example.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # WebSocket-Stream
    location ^~ /api/stream/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Web-Frontend und restliche API
    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Anpassen:

- `server_name` und die Zertifikatspfade auf deine Domain setzen.
- `127.0.0.1:8000` gilt, wenn nginx direkt auf dem Host läuft. Läuft nginx selbst in einem Docker-Container, trag stattdessen die Host-IP im Docker-Netz ein, meist `172.17.0.1`.
- Wenn du in der Compose-Datei einen anderen Host-Port einträgst (z. B. `"8632:8000"`), muss derselbe Port auch in beiden `proxy_pass` stehen.
- In der `.env` müssen `DOMAIN_NAME`, `PROTOCOL=https` und die `FIDO2_*`-Werte zur Domain passen.

## Builds (GitHub Actions)

Die Builds starten nicht bei einem Commit, nur manuell: **Actions → Workflow wählen → Run workflow**.

| Workflow | Ergebnis |
|---|---|
| [Build container](.github/workflows/container.yml) | Baut das Image und pusht es als `ghcr.io/<user>/webfix:latest`. Ältere Versionen ohne Tag werden gelöscht. |
| [Build Qt client](.github/workflows/qt-client.yml) | Baut den Client für Windows (x64, MSVC) und macOS (arm64) mit Qt 6.8. Ersetzt das Release `latest` durch die neuen Dateien. |

Ist das Repository privat, sind auch das Image und das Release privat. Das Image machst du unter **Packages → webfix → Package settings** öffentlich.
