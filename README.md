# JobsScraper — Job Offer Tracker

![JobsScraper Dashboard](./docs/screenshot.png)

A simple LAN-accessible webapp to search and track job offers from various portals, with a responsive web dashboard.

⚠️ **Vibe-Coded Project**

This app was created one evening out of sheer frustration with LinkedIn's job search. You know the feeling: you spend hours scrolling through job listings, but LinkedIn keeps pushing only the sponsored/highlighted ones in your face. The filters are terrible, you can't really keep track of what you've already analyzed, and there's no way to organize your search properly.

So I built this as a personal tool to:
- Automatically scrape jobs with keywords YOU care about
- Actually track what you've reviewed vs. what interests you
- Keep notes on each offer
- Sort and filter your way

It's rough around the edges, not production-ready, and likely full of bugs. But it works for what I needed. Use at your own risk! 😅

**P.S.** This README is also vibe-coded. No fancy documentation, just honest explanations of what works and what doesn't.

⚠️ **Legal Notice**

This is a **personal tool** for my own job search, not a commercial service. The default polling interval is intentionally set high (`poll_interval_minutes: 60`) to be respectful to the target portals. If you modify the defaults to use lower intervals, you do so at your own risk and are responsible for any consequences (rate limiting, IP bans, account suspension, etc.). Respect the Terms of Service of any website you scrape from. The author assumes no liability for misuse of this tool.

## 📋 Features

- **Automatic scraping** from LinkedIn (extensible to other portals)
- **Web dashboard** with filtering, sorting, and grouping
- **Review tracking** (mark as reviewed/interested)
- **Personal notes** on each offer
- **LAN accessible** from any device on your network
- **Simple CLI** for management

## 🗂️ Project Structure

```
JobsScraper/
├── app.py                  # Flask app + scheduler
├── config.yaml            # Configuration (keywords, locations, scrapers, interval)
├── storage.py             # SQLite database management
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── manage.py              # CLI management tool
├── scrapers/              # Scraper package
│   ├── __init__.py
│   └── linkedin.py        # LinkedIn scraper (plugin)
└── templates/
    └── index.html         # Web UI (table, flag, comments)
```

## 🚀 Quick Start

### 1️⃣ Clone / Download the project

If you haven't already, download the project and navigate to the folder:

```bash
cd /path/to/JobsScraper
```

### 2️⃣ Create virtual environment (first time only)

```bash
python3 -m venv venv
```

### 3️⃣ Install dependencies

```bash
python3 manage.py install
```

This automatically installs:
- `Flask` — web framework
- `requests` — HTTP client
- `beautifulsoup4` — HTML parsing
- `apscheduler` — task scheduler
- `PyYAML` — YAML config parsing

### 4️⃣ Configure the project (optional)

Edit `config.yaml` to add keywords/locations:

```yaml
keywords:
  - Junior Developer

locations:
  - Turin
  - Milan

scrapers:
  - name: linkedin
    module: scrapers.linkedin
    class: LinkedInScraper
    enabled: true

poll_interval_minutes: 60  # scrape every 60 minutes
```

### 5️⃣ Start the app

**Option A: Foreground (see logs)**
```bash
python3 manage.py start
```

Output:
```
🔍 Running scrapers...
✓ Inserted/updated 186 new jobs (scraped 251 total)

============================================================
✅ JobsScraper is RUNNING
============================================================
📱 Web UI: http://127.0.0.1:5000
   or from other machines: http://<YOUR_IP>:5000
   (Find your IP: ifconfig | grep 'inet ')
============================================================
```

👆 **The app is ready when you see this banner!**

**Option B: Background**
```bash
python3 manage.py start --bg
```

### 6️⃣ Access the UI

- **Same machine**: http://127.0.0.1:5000
- **Other PC on LAN**: http://<YOUR_IP>:5000
  - On macOS, find your IP with: `ifconfig | grep "inet "`
- **Smartphone**: same URL as your IP on the LAN

## 📱 Using the UI

### Table

The table shows:
| Column | Description |
|--------|-------------|
| **Position** | Job title |
| **Company** | Company name |
| **Location** | Job location |
| **Link** | Click to open offer on LinkedIn |
| **Date** | Publication date |
| **Flag** | ☑️ Checkbox: check if interested |
| **Comment** | Text field: personal notes |

### Sorting

Click any column header (Position, Company, Location, Date) to sort alphabetically. Click again to reverse.

### Flag (Y/N)

- Check the checkbox to mark offer as interesting
- Automatically saved to DB on click

### Comments

- Write personal notes in the "Comment" field
- Changes save when you click outside the field (blur)
- Examples: "Low salary", "Remote hours", "Deadline 30/04", etc.

## 🎛️ Management CLI Commands

Use `python3 manage.py` to control the app from terminal:

### Start / Stop

```bash
python3 manage.py start          # Start the app (see logs)
python3 manage.py start --bg     # Start in background
python3 manage.py stop           # Stop the app
python3 manage.py status         # Check if app is running
```

### Database

```bash
python3 manage.py db:info        # Show database statistics
python3 manage.py db:flagged     # Show only flagged offers
python3 manage.py db:clean       # Clear database (with confirmation)
```

### Setup

```bash
python3 manage.py install        # Install dependencies
python3 manage.py help           # Show all commands
```

## ⚙️ Configuration

You can change this parameters during the execution of the program, they will be fetched in the next scraping cycle
```yaml
keywords:
  - Programmer

locations:
  - Turin
  - Milan

poll_interval_minutes: 60        # Default: 1 hour
debug_level: 1                   # 0=silent, 1=normal, 2=verbose, 3=debug

scrapers:
  - name: linkedin
    module: scrapers.linkedin
    class: LinkedInScraper
    enabled: true
    max_results_per_search: 1000
```

## 🔌 Adding a New Scraper

### Example: Indeed Scraper

1. Create `scrapers/indeed.py`:

```python
import requests
from bs4 import BeautifulSoup
import time

class IndeedScraper:
    def search(self, keywords: str, location: str, max_results: int = 100) -> list:
        all_jobs = []
        url = f"https://www.indeed.com/jobs?q={keywords}&l={location}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (..)'
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Parse Indeed-specific HTML...
            # Return list of dicts with keys: title, company, location, url, posted_date
        except Exception as e:
            print(f"Error: {e}")
        return all_jobs
```

2. Add to `config.yaml`:

```yaml
scrapers:
  - name: linkedin
    module: scrapers.linkedin
    class: LinkedInScraper
    enabled: true
  - name: indeed
    module: scrapers.indeed
    class: IndeedScraper
    enabled: true
```

3. Restart `app.py`.

## 📊 Database File

- `jobs.db` — SQLite database (created automatically on first run)
  - Table: `jobs` (id, title, company, location, url, posted_date, flag, comment, created_at)

To inspect the DB directly:
```bash
sqlite3 jobs.db "SELECT COUNT(*) as total FROM jobs;"
```

To reset the database:
```bash
rm jobs.db
```

##  Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"

Make sure you've installed dependencies:
```bash
python3 manage.py install
```

### "Connection refused" when accessing from smartphone

- Verify the app is running: `http://127.0.0.1:5000` should work on the PC.
- Verify firewall doesn't block port 5000.
- Verify smartphone is on the same WiFi network.
- Use `ifconfig | grep "inet "` to find the correct IP (usually `192.168.x.x`).

### "LinkedIn blocked (403)"

LinkedIn blocks massive requests after a few cycles. Solutions:
- Increase `poll_interval_minutes` to `60` (1 hour).
- Use proxy or VPN.
- Add scrapers for other portals (Indeed, Glassdoor, etc.).
- Consider using LinkedIn official API (requires authentication).

### No offers found

- Check that keywords and locations in `config.yaml` are correct.
- Check app logs for scraping errors.
- Try changing LinkedIn site language (EN vs IT).

##  License

**MIT License** — You're free to use, modify, and distribute this software. Just keep my name in the credits. That's it!

For the full legal text, see [LICENSE](./LICENSE).

---

**Good luck with your job search! 🚀**
