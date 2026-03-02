# amazon-invoice-dl

Download all invoices from your Amazon.de account as PDF files.

Uses Playwright (Chromium) with human-like delays and stealth mode. Supports 2FA — a browser window opens for you to complete the challenge.

## Installation

### macOS (recommended)

```bash
brew install pipx
pipx install git+https://github.com/wizz-cmd/amazon-invoice-dl.git
pipx ensurepath   # add ~/.local/bin to PATH, then restart your shell
playwright install chromium
```

### Linux

```bash
pip install --user git+https://github.com/wizz-cmd/amazon-invoice-dl.git
playwright install chromium
```

### From source

```bash
git clone https://github.com/wizz-cmd/amazon-invoice-dl.git
cd amazon-invoice-dl
pip install .    # or: pipx install .
playwright install chromium
```

## Usage

```bash
# Download current year's invoices (opens browser for login + 2FA)
amazon-invoice-dl --email you@example.com --password 'hunter2'

# Full year
amazon-invoice-dl --period 2024

# Single month
amazon-invoice-dl --period 2024-11

# Quarter
amazon-invoice-dl --period 2024Q3

# Half year
amazon-invoice-dl --period 2024H1

# Range of years
amazon-invoice-dl --period 2023..2025

# Month range
amazon-invoice-dl --period 2024-06..2024-12

# Custom output directory
amazon-invoice-dl --output-dir ~/Documents/amazon-invoices

# Headless mode (only works without 2FA)
amazon-invoice-dl --headless
```

> **Note:** The `--year`, `--start-year`, and `--date-range` flags still work but are deprecated.
> Use `--period` instead.

### Credentials via environment / .env

Instead of passing `--email` and `--password`, set environment variables or create a `.env` file:

```bash
AMAZON_EMAIL=you@example.com
AMAZON_PASSWORD=hunter2
```

The tool looks for `.env` in the current directory and up to 3 parent directories.

## Output

PDFs are saved as:

```
YYYYMMDD_AMOUNT_amazon_ORDER-ID.pdf
```

Example: `20240315_18_74_amazon_302-1234567-8901234.pdf`

Already-downloaded invoices are skipped automatically (idempotent).

## Requirements

- Python 3.9+
- Playwright + Chromium
- Works on Linux and macOS

## Implemented Features

- **Login** — automatischer Login auf Amazon.de mit E-Mail und Passwort
- **2FA / CAPTCHA** — Browser-Fenster öffnet sich, User löst die Challenge manuell
- **Perioden-Filter** — hledger-style `--period`-Flag für Jahr, Monat, Quartal, Halbjahr, Bereiche
- **Pagination** — iteriert alle Bestellseiten eines Jahres automatisch durch
- **Retry bei Timeout** — Seitennavigation wird bei Timeout einmalig wiederholt
- **PDF-Download** — Rechnungsseite wird als A4-PDF gespeichert, inkl. Fallback über Bestelldetails
- **Idempotent** — bereits heruntergeladene Rechnungen werden übersprungen (Dateiname als Schlüssel)
- **Fortschrittsbalken** — tqdm-Balken mit Gesamtanzahl und aktueller Order-ID während des Downloads
- **Dateinamensschema** — `YYYYMMDD_AMOUNT_amazon_ORDER-ID.pdf` (sortierbar, maschinenlesbar)
- **Credentials** — via `--email`/`--password`, Umgebungsvariablen oder `.env`-Datei
- **Stealth-Modus** — deaktiviert `navigator.webdriver`, menschliche Zufallsverzögerungen
- **Headless-Modus** — optionaler Betrieb ohne sichtbares Browser-Fenster

---

## Roadmap — User Stories

Die folgenden User Stories beschreiben geplante Weiterentwicklungen.
Beim Implementieren einfach auf die ID verweisen, z. B. *„US-R01 implementieren"*.

### Robustheit & Zuverlässigkeit *(hohe Priorität)*

**US-R01 — Exponentielles Retry mit Backoff**
Als Benutzer möchte ich, dass fehlgeschlagene Downloads automatisch mit exponentiellem Backoff wiederholt werden (z. B. 3 Versuche: 5 s, 30 s, 120 s), damit ein kurzer Netzwerkfehler oder eine Amazon-Drosselung keinen vollständigen Neustart erfordert.

**US-R02 — Strukturierte Exit-Codes**
Als Skript-Benutzer möchte ich, dass das Tool standardisierte Exit-Codes nach `sysexits.h` zurückgibt (z. B. `EX_USAGE=64` bei falschen Argumenten, `EX_UNAVAILABLE=69` bei Login-Fehler, `EX_IOERR=74` bei Schreibfehlern), damit Fehler in Shell-Skripten und CI-Pipelines zuverlässig erkannt und unterschieden werden können.

**US-R03 — Graceful Shutdown bei Signalen**
Als Benutzer möchte ich, dass das Tool bei `SIGINT` (Ctrl+C) und `SIGTERM` sauber beendet wird — laufender Download wird abgeschlossen, temporäre Dateien werden entfernt, eine Zusammenfassung des bisherigen Fortschritts wird ausgegeben — damit kein inkonsistenter Zustand hinterlassen wird.

**US-R04 — Fehler-Log in Datei**
Als Benutzer möchte ich, dass alle Warnungen und Fehler optional in eine Logdatei (z. B. `--log-file downloads/errors.log`) geschrieben werden, damit ich nach einem Lauf nachvollziehen kann, welche Rechnungen nicht heruntergeladen werden konnten und warum.

**US-R05 — Stderr für Diagnose, Stdout für Maschinen**
Als Benutzer möchte ich, dass Statusmeldungen und Fehlermeldungen auf `stderr` ausgegeben werden und maschinenlesbare Ausgaben (z. B. `--json`) auf `stdout` erscheinen, damit das Tool sich gemäß Unix-Konventionen verhält und in Pipelines verwendbar ist.

### Konfiguration & Credentials

**US-C01 — System-Keyring-Integration**
Als Benutzer möchte ich meine Amazon-Zugangsdaten einmalig im System-Schlüsselbund speichern (macOS Keychain, GNOME Keyring / libsecret) und das Tool danach ohne `--password`-Flag aufrufen, damit mein Passwort nicht in Shell-History, `.env`-Dateien oder Prozesslisten auftaucht.

**US-C02 — XDG-konforme Konfigurationsdatei**
Als Benutzer möchte ich Standardwerte (E-Mail, Ausgabeverzeichnis, Periode) in `~/.config/amazon-invoice-dl/config.toml` hinterlegen können (XDG Base Directory Specification), damit ich beim täglichen Aufruf keine Flags angeben muss und das Tool dem Linux-Desktop-Standard entspricht.

### Benutzeroberfläche & Komfort

**US-U01 — Dry-Run-Modus**
Als Benutzer möchte ich mit `--dry-run` sehen, welche Rechnungen heruntergeladen werden würden, ohne dass tatsächlich Dateien geschrieben werden, damit ich vor einem langen Lauf die Auswahl prüfen kann.

**US-U02 — Ausgabe als JSON**
Als Entwickler möchte ich mit `--json` eine strukturierte JSON-Ausgabe auf `stdout` erhalten (eine Zeile pro Rechnung mit Status, Dateiname, Order-ID, Datum, Betrag), damit ich das Tool in eigene Skripte und Workflows integrieren kann.

### Erweiterbarkeit

**US-E01 — Unterstützung weiterer Amazon-Länder**
Als internationaler Benutzer möchte ich mit `--locale amazon.com` oder `--locale amazon.co.uk` Rechnungen von anderen Amazon-Marktplätzen herunterladen, damit das Tool nicht auf Amazon.de beschränkt ist.

### Qualität & Wartbarkeit

**US-Q01 — Automatisierte Testsuite**
Als Entwickler möchte ich eine Testsuite mit gemockten Playwright-Seiten haben, die kritische Pfade abdeckt (Login, Pagination, PDF-Download, Perioden-Parsing), damit Regressionen frühzeitig erkannt werden.

**US-Q02 — CI via GitHub Actions**
Als Maintainer möchte ich, dass bei jedem Push und Pull Request automatisch Linting (`ruff`), Typprüfung (`mypy`) und Tests ausgeführt werden, damit Qualitätsprobleme nicht unbemerkt in den `main`-Branch gelangen.

---

## License

MIT
