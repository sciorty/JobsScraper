import yaml
import importlib
import os
import sys
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from storage import init_db, upsert_jobs, list_jobs, set_reviewed, set_interested, set_comment

app = Flask(__name__)

cfg = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))

# Debug level: 0=silent, 1=normal, 2=verbose, 3=debug
DEBUG_LEVEL = cfg.get('debug_level', 1)

def debug_print(level, msg):
    """Print debug message based on debug level"""
    if DEBUG_LEVEL >= level:
        print(f"[DEBUG-{level}] {msg}", file=sys.stderr)

scraper_instances = []

def load_scrapers():
    instances = []
    for s in cfg.get('scrapers', []):
        if not s.get('enabled', True):
            continue
        mod = importlib.import_module(s['module'])
        cls = getattr(mod, s['class'])
        instances.append(cls())
    if DEBUG_LEVEL >= 2:
        print(f"✓ Loaded {len(instances)} scraper(s)")
    return instances

@app.route('/')
def index():
    jobs = list_jobs()
    if DEBUG_LEVEL >= 3:
        debug_print(3, f"Rendering {len(jobs)} jobs")
    return render_template('index.html', jobs=jobs)

@app.route('/api/jobs')
def api_jobs():
    jobs = list_jobs()
    return jsonify(jobs)

@app.route('/api/set_reviewed', methods=['POST'])
def api_set_reviewed():
    data = request.json
    set_reviewed(data['id'], 1 if data.get('reviewed') else 0)
    if DEBUG_LEVEL >= 3:
        debug_print(3, f"Job {data['id']} reviewed: {data.get('reviewed')}")
    return jsonify({'ok': True})

@app.route('/api/set_interested', methods=['POST'])
def api_set_interested():
    data = request.json
    set_interested(data['id'], 1 if data.get('interested') else 0)
    if DEBUG_LEVEL >= 3:
        debug_print(3, f"Job {data['id']} interested: {data.get('interested')}")
    return jsonify({'ok': True})

@app.route('/api/set_comment', methods=['POST'])
def api_set_comment():
    data = request.json
    set_comment(data['id'], data.get('comment', ''))
    return jsonify({'ok': True})

def run_scrapers():
    print(f'\n🔍 Running scrapers...')
    all_found = []
    keywords = cfg.get('keywords', [])
    locations = cfg.get('locations', [])
    
    if DEBUG_LEVEL >= 2:
        print(f"   Keywords: {', '.join(keywords)}")
        print(f"   Locations: {', '.join(locations)}")
        print()
    
    search_count = 0
    for kw in keywords:
        for loc in locations:
            for i, s in enumerate(scraper_instances):
                try:
                    scraper_cfg = cfg.get('scrapers', [])[i]
                    scraper_name = scraper_cfg.get('name', 'unknown')
                    max_results = scraper_cfg.get('max_results_per_search', 1000)
                    
                    search_count += 1
                    if DEBUG_LEVEL >= 1:
                        print(f"   [{search_count}] {scraper_name.upper()}: '{kw}' in '{loc}' (max {max_results})")
                    
                    jobs = s.search(kw, loc, max_results=max_results)
                    if DEBUG_LEVEL >= 2:
                        print(f"       → Found {len(jobs)} jobs")
                    all_found.extend(jobs)
                except Exception as e:
                    print(f'❌ Scraper error: {e}')
    
    if all_found:
        inserted = upsert_jobs(all_found)
        print(f'\n✓ Inserted/updated {inserted} new jobs (scraped {len(all_found)} total)')
    else:
        print('\nℹ️  No new jobs found')

if __name__ == '__main__':
    init_db()
    scraper_instances = load_scrapers()
    
    if DEBUG_LEVEL >= 1:
        print(f"📊 Debug level: {DEBUG_LEVEL}")
        poll_minutes = cfg.get('poll_interval_minutes', 5)
        print(f"🔄 Poll interval: {poll_minutes} minute(s)")
        print(f"📌 Keywords: {', '.join(cfg.get('keywords', []))}")
        print(f"📍 Locations: {', '.join(cfg.get('locations', []))}")

    # Check if DB has existing jobs
    existing_jobs = list_jobs()
    has_data = len(existing_jobs) > 0

    scheduler = BackgroundScheduler()
    poll_interval_seconds = cfg.get('poll_interval_minutes', 5) * 60
    scheduler.add_job(run_scrapers, 'interval', seconds=poll_interval_seconds)
    scheduler.start()

    # Run scrapers only if DB is empty, otherwise start server first
    if not has_data:
        run_scrapers()

    print("\n" + "="*60)
    print("✅ JobsScraper is RUNNING")
    print("="*60)
    print("📱 Web UI: http://127.0.0.1:5000")
    print("   or from other machines: http://<YOUR_IP>:5000")
    print("   (Find your IP: ifconfig | grep 'inet ')")
    print("="*60)
    if has_data:
        print(f"📊 Loaded {len(existing_jobs)} existing jobs from DB")
        print("🔄 Background scraping will start automatically")
    print()

    # Suppress Flask's default logging in production
    if DEBUG_LEVEL <= 1:
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    app.run(host='0.0.0.0', port=5000, debug=False)
