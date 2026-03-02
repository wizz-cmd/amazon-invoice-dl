# CLAUDE.md — Amazon Invoice Downloader

## Project Overview

CLI tool to download all invoices from Amazon.de as PDF files. Uses Playwright (Chromium) with stealth mode and human-like delays. Supports 2FA via visible browser window.

**Repo:** https://github.com/wizz-cmd/amazon-invoice-dl
**License:** MIT | **Language:** Python 3.9+ | **Build:** hatchling
**Entry point:** `src/amazon_invoice_dl/cli.py` → `main()`

## Architecture

Single-module CLI tool:
- `src/amazon_invoice_dl/cli.py` — all logic (login, scraping, PDF download)
- `pyproject.toml` — package config, CLI entry point `amazon-invoice-dl`
- No tests yet, no CI yet

## How It Works

1. Launch Chromium via Playwright (visible by default for 2FA)
2. Login to Amazon.de (email → password → wait for 2FA if needed)
3. Iterate order history pages per year, extract order IDs via regex
4. For each order: navigate to print invoice URL, `page.pdf()` to save
5. Filenames: `YYYYMMDD_AMOUNT_amazon_ORDER-ID.pdf`
6. Idempotent: skips existing files

## Development Commands

```bash
# Install in dev mode
pip install -e .
playwright install chromium

# Run
amazon-invoice-dl --help
amazon-invoice-dl --year 2024 --email test@example.com --password xyz

# Lint (not yet configured, but please use)
ruff check src/
ruff format src/
```

## Git Conventions

- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- Git identity: `Claude Code <claude-code@schoemfeld.de>`
- Branch: `main` (direct push ok for now)

## Key Design Goals

1. **Usable by non-technical people** — clear error messages, good `--help` output, sensible defaults
2. **hledger-style period expressions** for time filtering (see below)
3. **Cross-platform** — Linux and macOS, no Windows requirement but don't break it either
4. **Minimal dependencies** — only `playwright`, no heavy frameworks
5. **Idempotent** — safe to re-run, skips already-downloaded invoices

## Priority: Period Expressions (hledger-style)

Replace the current `--year` / `--date-range` / `--start-year` flags with a single unified `--period` flag inspired by hledger:

```bash
amazon-invoice-dl --period 2024           # full year
amazon-invoice-dl --period 2024-11        # single month (November 2024)
amazon-invoice-dl --period 2024Q3         # quarter
amazon-invoice-dl --period 2024H1         # half year
amazon-invoice-dl --period 2023..2025     # range of years
amazon-invoice-dl --period 2024-06..2024-12  # month range
amazon-invoice-dl                          # default: current year
```

Keep `--year` as deprecated alias for backwards compatibility.

### Period parsing spec:
- `YYYY` → Jan 1 to Dec 31
- `YYYY-MM` → first to last day of month
- `YYYYQN` (N=1-4) → quarter
- `YYYYHN` (N=1-2) → half year
- `FROM..TO` → range (both inclusive, each can be YYYY or YYYY-MM)
- No period / no args → current year

## Future Ideas (don't implement yet, just be aware)

- **Credential management:** Apple Keychain integration (macOS), libsecret (Linux), or generic keyring via `keyring` package
- **Config file:** `~/.config/amazon-invoice-dl/config.yaml` for defaults (email, output-dir, locale)
- **Multiple Amazon locales:** amazon.com, amazon.co.uk, etc. (currently hardcoded to .de)
- **Progress bar** with `rich` or `tqdm`
- **Retry logic** for transient failures
- **Test suite** with mocked pages
- **CI** via GitHub Actions (lint + type check at minimum)
- **Changelog / releases** with git tags

## Code Style

- Type hints where practical (not mandatory for existing code)
- Docstrings for public functions
- German comments are fine for Amazon.de-specific logic
- Keep it simple — this is a CLI tool, not a framework
