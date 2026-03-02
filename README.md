# amazon-invoice-dl

Download all invoices from your Amazon.de account as PDF files.

Uses Playwright (Chromium) with human-like delays and stealth mode. Supports 2FA — a browser window opens for you to complete the challenge.

## Installation

```bash
# Clone and install
git clone https://github.com/wizz-cmd/amazon-invoice-dl.git
cd amazon-invoice-dl
pip install .

# Install the browser (one-time)
playwright install chromium
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/wizz-cmd/amazon-invoice-dl.git
playwright install chromium
```

## Usage

```bash
# Download current year's invoices (opens browser for login + 2FA)
amazon-invoice-dl --email you@example.com --password 'hunter2'

# Download a specific year
amazon-invoice-dl --year 2024

# Download a range of years
amazon-invoice-dl --start-year 2020

# Custom date range
amazon-invoice-dl --date-range 20240101-20241231

# Custom output directory
amazon-invoice-dl --output-dir ~/Documents/amazon-invoices

# Headless mode (only works without 2FA)
amazon-invoice-dl --headless
```

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

## License

MIT
