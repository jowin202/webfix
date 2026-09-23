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

Die macOS-App ist nicht signiert. Beim ersten Start deshalb per Rechtsklick → „Öffnen“ bestätigen.

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

## Builds (GitHub Actions)

Die Builds starten nicht bei einem Commit, nur manuell: **Actions → Workflow wählen → Run workflow**.

| Workflow | Ergebnis |
|---|---|
| [Build container](.github/workflows/container.yml) | Baut das Image und pusht es als `ghcr.io/<user>/webfix:latest`. Ältere Versionen ohne Tag werden gelöscht. |
| [Build Qt client](.github/workflows/qt-client.yml) | Baut den Client für Windows (x64, MSVC) und macOS (arm64) mit Qt 6.8. Ersetzt das Release `latest` durch die neuen Dateien. |

Ist das Repository privat, sind auch das Image und das Release privat. Das Image machst du unter **Packages → webfix → Package settings** öffentlich.
