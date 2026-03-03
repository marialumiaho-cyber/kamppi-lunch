#!/usr/bin/env python3
"""
Weekly lunch menu scraper – Kamppi / Autotalo area, Helsinki.
Fetches menus, uses Claude API to parse into structured JSON,
writes result to docs/menus.json for the GitHub Pages dashboard.
"""

import json
import re
import os
import sys
from datetime import date, timedelta
import anthropic
import httpx
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────

RESTAURANTS = [
    {
        "id": "factory_kamppi",
        "name": "Factory Kamppi",
        "address": "Runeberginkatu 3, 00100 Helsinki",
        "url": "https://factorykamppi.com/lounas/",
        "hours": "10:30–15:00",
        "parse_method": "claude",
    },
    # Add more restaurants here — just copy the block above and change the values.
    # Each restaurant needs: id, name, address, url, hours, parse_method ("claude" for all new ones)
]

DAYS_FI = {1: "Maanantai", 2: "Tiistai", 3: "Keskiviikko", 4: "Torstai", 5: "Perjantai"}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "docs", "menus.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LunchBot/1.0)"}
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=20)
    resp.raise_for_status()
    return resp.text


def get_week_label() -> str:
    """Return a label like '2.3.–6.3.2026' for the current Mon–Fri week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    if monday.month == friday.month:
        return f"{monday.day}.{monday.month}.–{friday.day}.{friday.month}.{friday.year}"
    return f"{monday.day}.{monday.month}.–{friday.day}.{friday.month}.{friday.year}"


# ── Claude-assisted parsing (universal — works for any restaurant) ─────────────

def parse_with_claude(restaurant: dict, html: str) -> dict:
    """Strip the page to readable text and ask Claude to structure the menu."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("nav, header, footer, script, style, iframe, noscript"):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Trim whitespace-heavy lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    menu_text = "\n".join(lines[:300])  # cap at ~300 lines to stay within context

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are a lunch menu extraction assistant. Below is the raw text from the lunch page of {restaurant['name']} ({restaurant['url']}).

Extract the weekly lunch menu and return ONLY a valid JSON object — no markdown, no backticks, no explanation.

Use this exact structure:
{{
  "week_label": "e.g. 2.3.–6.3.2026",
  "prices": ["e.g. Lounasbuffet 13,70 €"],
  "common_items": ["items available every day, e.g. salad bar, bread, dessert, coffee"],
  "daily_menus": {{
    "1": {{ "soups": ["..."], "mains": ["...", "..."], "dessert": ["..."], "vegan": ["..."] }},
    "2": {{ "soups": ["..."], "mains": ["...", "..."], "dessert": ["..."], "vegan": null }},
    "3": {{ "soups": ["..."], "mains": ["...", "..."], "dessert": ["..."], "vegan": ["..."] }},
    "4": {{ "soups": ["..."], "mains": ["...", "..."], "dessert": ["..."], "vegan": null }},
    "5": {{ "soups": ["..."], "mains": ["...", "..."], "dessert": ["..."], "vegan": ["..."] }}
  }}
}}

Rules:
- Keys 1–5 = Monday–Friday
- Keep dietary tags like (L+G), (VE), (VGN), (M+G+VS) inline within each item string
- If a category (soups / dessert / vegan) has no items for a day, set it to null
- common_items = things available every day (salad bar, bread, coffee, etc.) — extract from the description text
- Use Finnish dish names (the page is bilingual — prefer Finnish)
- week_label should reflect the actual dates shown on the page

PAGE TEXT:
{menu_text}
"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ── Main scrape loop ──────────────────────────────────────────────────────────

def scrape_all() -> list:
    results = []
    for restaurant in RESTAURANTS:
        print(f"Fetching: {restaurant['name']} …")
        try:
            html = fetch_html(restaurant["url"])
            menu_data = parse_with_claude(restaurant, html)

            results.append({
                "id": restaurant["id"],
                "name": restaurant["name"],
                "address": restaurant["address"],
                "url": restaurant["url"],
                "hours": restaurant["hours"],
                "week_label": menu_data.get("week_label", get_week_label()),
                "prices": menu_data.get("prices", []),
                "common_items": menu_data.get("common_items", []),
                "daily_menus": menu_data.get("daily_menus", {}),
            })
            print(f"  ✓ OK")

        except Exception as e:
            print(f"  ✗ Error: {e}", file=sys.stderr)
            results.append({
                "id": restaurant["id"],
                "name": restaurant["name"],
                "address": restaurant["address"],
                "url": restaurant["url"],
                "hours": restaurant["hours"],
                "week_label": get_week_label(),
                "prices": [],
                "common_items": [],
                "daily_menus": {},
                "error": str(e),
            })
    return results


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    week = get_week_label()
    print(f"Scraping menus for week {week} …")

    data = {
        "scraped_at": date.today().isoformat(),
        "week_label": week,
        "restaurants": scrape_all(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
