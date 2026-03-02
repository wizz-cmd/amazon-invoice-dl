#!/usr/bin/env python3
"""
Amazon.de Invoice Downloader
Downloads all invoices from an Amazon.de account as PDF files.

Usage:
    python3 amazon-invoice-dl.py --year=2025
    python3 amazon-invoice-dl.py --date-range=20240101-20241231
    python3 amazon-invoice-dl.py  # defaults to current year

Credentials via env vars or .env file:
    AMAZON_EMAIL=...
    AMAZON_PASSWORD=...

Or pass --email= --password= on command line.

Output: ./downloads/ (or --output-dir=<path>)
"""

import argparse
import os
import re
import sys
import time
import random
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


def human_delay(min_s=1.5, max_s=4.0):
    """Random delay to mimic human behavior."""
    time.sleep(random.uniform(min_s, max_s))


def load_env_file():
    """Load .env file if present."""
    for d in [Path.cwd()] + list(Path.cwd().parents)[:3]:
        env_file = d / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break


def parse_args():
    p = argparse.ArgumentParser(description="Amazon.de Invoice Downloader")
    p.add_argument("--email", default=os.environ.get("AMAZON_EMAIL", ""))
    p.add_argument("--password", default=os.environ.get("AMAZON_PASSWORD", ""))
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--date-range", dest="date_range", default=None,
                   help="YYYYMMDD-YYYYMMDD")
    p.add_argument("--output-dir", dest="output_dir", default="./downloads")
    p.add_argument("--headless", action="store_true", default=False,
                   help="Run headless (default: visible browser for 2FA)")
    p.add_argument("--start-year", dest="start_year", type=int, default=None,
                   help="Download from this year to current year (batch mode)")
    return p.parse_args()


def get_date_range(args):
    """Return (start_date, end_date) as strings YYYYMMDD."""
    if args.date_range:
        parts = args.date_range.split("-")
        return parts[0], parts[1]
    year = args.year or datetime.now().year
    return f"{year}0101", f"{year}1231"


def login(page, email, password):
    """Log into Amazon.de. Handles 2FA by waiting for user."""
    print("→ Navigating to Amazon.de login...")
    page.goto("https://www.amazon.de/gp/css/order-history?ref_=nav_orders_first")
    human_delay(2, 4)

    # Check if already logged in
    if "order-history" in page.url and "ap/signin" not in page.url:
        print("✅ Already logged in")
        return True

    # Email
    email_field = page.locator('input[name="email"], input#ap_email')
    if email_field.is_visible():
        print("→ Entering email...")
        email_field.fill(email)
        human_delay(0.5, 1.5)
        cont_btn = page.locator('input#continue, input[type="submit"]').first
        cont_btn.click()
        human_delay(1.5, 3)

    # Password
    pw_field = page.locator('input[name="password"], input#ap_password')
    if pw_field.is_visible():
        print("→ Entering password...")
        pw_field.fill(password)
        human_delay(0.5, 1)
        sign_in = page.locator('input#signInSubmit, input[type="submit"]').first
        sign_in.click()
        human_delay(2, 4)

    # 2FA / CAPTCHA check — wait for user
    for _ in range(60):  # 5 min max
        try:
            url = page.url
            print(f"  [debug] URL: {url[:80]}")

            # Primary check: look for Amazon nav bar elements that only appear when logged in
            nav = page.locator('#nav-link-accountList, #nav-orders, #nav-item-signout')
            if nav.first.is_visible(timeout=2000):
                print("✅ Login successful")
                return True
        except Exception:
            pass

        print("⏳ Waiting for 2FA / CAPTCHA — complete it in the browser...")
        time.sleep(5)

    print("❌ Login timed out after 5 minutes")
    return False


def get_order_years_filter(page, start_date, end_date):
    """Navigate to order history and set the date filter."""
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    return list(range(start_year, end_year + 1))


def scrape_orders_for_year(page, year):
    """Scrape all order IDs and dates for a given year using pagination URL params."""
    orders = []
    start_index = 0
    page_num = 0

    print(f"\n📅 Fetching orders for {year}...")

    while True:
        page_num += 1
        url = f"https://www.amazon.de/your-orders/orders?timeFilter=year-{year}&startIndex={start_index}"
        print(f"  Page {page_num} (startIndex={start_index})...")
        page.goto(url)
        human_delay(2, 4)

        # Get the full page text and extract all order IDs via regex
        try:
            page_text = page.content()
        except Exception as e:
            print(f"  ⚠️  Error getting page content: {e}")
            break

        # Find order IDs in the page HTML (most reliable method)
        order_ids_on_page = list(set(re.findall(r'(\d{3}-\d{7}-\d{7})', page_text)))

        # Filter out any IDs we already have
        existing_ids = {o["id"] for o in orders}
        new_ids = [oid for oid in order_ids_on_page if oid not in existing_ids]

        if not new_ids:
            print(f"  No new orders found on page {page_num}, done.")
            break

        print(f"  Found {len(new_ids)} order IDs on page {page_num}")

        # For each order ID, try to extract date and total from nearby text
        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=10000)
        except:
            pass

        months_de = {
            "Januar": "01", "Februar": "02", "März": "03", "April": "04",
            "Mai": "05", "Juni": "06", "Juli": "07", "August": "08",
            "September": "09", "Oktober": "10", "November": "11", "Dezember": "12"
        }

        for oid in new_ids:
            # Try to find the date near this order ID in the text
            # Look for date pattern before the order ID
            order_date = f"{year}0101"
            total = "0_00"

            # Find the chunk of text around this order ID
            idx = body_text.find(oid)
            if idx > 0:
                # Look backwards ~500 chars for date and price
                chunk = body_text[max(0, idx - 500):idx + 100]

                # Date: "22. Februar 2026" or "3. Mai 2024"
                date_matches = re.findall(
                    r'(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})',
                    chunk
                )
                if date_matches:
                    last = date_matches[-1]  # closest to order ID
                    day = last[0].zfill(2)
                    month = months_de.get(last[1], "00")
                    yr = last[2]
                    order_date = f"{yr}{month}{day}"

                # Total: "18,74 €" or "EUR 18,74"
                total_matches = re.findall(r'(\d+[.,]\d{2})\s*€', chunk)
                if total_matches:
                    total = total_matches[-1].replace(",", "_").replace(".", "_")

            orders.append({
                "id": oid,
                "date": order_date,
                "total": total,
            })

        # Amazon.de shows 10 orders per page
        start_index += 10
        human_delay(1, 2)

    print(f"  → {len(orders)} orders found for {year}")
    return orders


def download_invoice(page, order, output_dir):
    """Download the invoice PDF for a single order."""
    order_id = order["id"]
    date = order["date"]
    total = order["total"]
    filename = f"{date}_{total}_amazon_{order_id}.pdf"
    filepath = output_dir / filename

    if filepath.exists():
        print(f"  ⏭️  Skip (exists): {filename}")
        return True

    # Navigate to order detail / invoice page
    invoice_url = f"https://www.amazon.de/gp/css/summary/print.html/ref=ppx_yo_dt_b_invoice_o00?ie=UTF8&orderID={order_id}"
    try:
        page.goto(invoice_url, timeout=15000)
        human_delay(1.5, 3)

        # Check if we got an actual invoice page
        body_text = page.locator("body").inner_text(timeout=5000)
        if "Rechnung" in body_text or "Invoice" in body_text or order_id in body_text:
            # Print to PDF
            page.pdf(path=str(filepath), format="A4", print_background=True)
            print(f"  ✅ {filename}")
            return True
        else:
            # Try the invoice link from order details
            order_url = f"https://www.amazon.de/gp/your-account/order-details/ref=ppx_yo_dt_b_order_details_o00?ie=UTF8&orderID={order_id}"
            page.goto(order_url, timeout=15000)
            human_delay(1, 2)

            # Look for "Rechnung" link
            invoice_link = page.locator('a:has-text("Rechnung"), a[href*="invoice"], a:has-text("Invoice")')
            if invoice_link.count() > 0:
                invoice_link.first.click()
                human_delay(1, 2)
                page.pdf(path=str(filepath), format="A4", print_background=True)
                print(f"  ✅ {filename} (via order details)")
                return True
            else:
                print(f"  ⚠️  No invoice link found for {order_id}")
                return False

    except PWTimeout:
        print(f"  ❌ Timeout for {order_id}")
        return False
    except Exception as e:
        print(f"  ❌ Error for {order_id}: {e}")
        return False


def main():
    load_env_file()
    args = parse_args()

    email = args.email or os.environ.get("AMAZON_EMAIL", "")
    password = args.password or os.environ.get("AMAZON_PASSWORD", "")

    if not email or not password:
        print("❌ Credentials required. Set AMAZON_EMAIL + AMAZON_PASSWORD or use --email/--password")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date, end_date = get_date_range(args)
    if args.start_year:
        start_date = f"{args.start_year}0101"
        end_date = f"{datetime.now().year}1231"

    years = list(range(int(start_date[:4]), int(end_date[:4]) + 1))

    print(f"🛒 Amazon.de Invoice Downloader")
    print(f"   Years: {years}")
    print(f"   Output: {output_dir.resolve()}")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = browser.new_context(
            locale="de-DE",
            timezone_id="Europe/Berlin",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        # Stealth: remove webdriver flag
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.new_page()

        if not login(page, email, password):
            browser.close()
            sys.exit(1)

        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        for year in years:
            orders = scrape_orders_for_year(page, year)
            for order in orders:
                human_delay(0.8, 2.0)
                result = download_invoice(page, order, output_dir)
                if result:
                    if (output_dir / f"{order['date']}_{order['total']}_amazon_{order['id']}.pdf").stat().st_size > 0:
                        total_downloaded += 1
                    else:
                        total_skipped += 1
                else:
                    total_failed += 1

        print(f"\n{'='*50}")
        print(f"📊 Ergebnis:")
        print(f"   ✅ Heruntergeladen: {total_downloaded}")
        print(f"   ⏭️  Übersprungen:   {total_skipped}")
        print(f"   ❌ Fehlgeschlagen:  {total_failed}")
        print(f"   📁 Ausgabeverzeichnis: {output_dir.resolve()}")

        browser.close()


if __name__ == "__main__":
    main()
