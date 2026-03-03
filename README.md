# Kamppi Lounas Dashboard

Auto-updating weekly lunch menu dashboard for restaurants near Kamppi / Autotalo, Helsinki.

🌐 **Live:** `https://<your-username>.github.io/kamppi-lunch`

## How it works

1. Every **Monday at 07:00 Helsinki time**, a GitHub Action runs `scrape.py`
2. The script fetches each restaurant's lunch page, uses the **Claude API** to parse free-text into structured JSON
3. The result is saved to `docs/menus.json` and committed to the repo
4. GitHub Pages serves the dashboard from `docs/`

You can also trigger a manual scrape anytime from **Actions → Scrape Weekly Menus → Run workflow**.

## Adding a restaurant

Open `scrape.py` and add an entry to the `RESTAURANTS` list:

```python
{
    "id": "my_restaurant",
    "name": "My Restaurant",
    "address": "Street 1, 00100 Helsinki",
    "url": "https://example.com/lounas/",
    "hours": "11:00–14:00",
    "parse_method": "claude",
},
```

That's it — Claude handles the parsing for any site structure.

## Setup

### 1. Fork / clone this repo

### 2. Add your Anthropic API key
Go to **Settings → Secrets and variables → Actions → New repository secret**
- Name: `ANTHROPIC_API_KEY`
- Value: your key from [console.anthropic.com](https://console.anthropic.com)

### 3. Enable GitHub Pages
Go to **Settings → Pages**
- Source: `Deploy from a branch`
- Branch: `main`, folder: `/docs`

### 4. Enable Actions
Go to **Actions** tab and enable workflows if prompted.

Done! The first scrape will run next Monday, or trigger it manually right away.

## Files

```
├── scrape.py                        # Scraper + Claude parser
├── requirements.txt
├── .github/workflows/scrape.yml     # Monday 07:00 schedule
└── docs/
    ├── index.html                   # Dashboard UI
    └── menus.json                   # Auto-updated weekly
```
