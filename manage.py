#!/usr/bin/env python3
"""
JobsScraper Management CLI
Simple commands to start, stop, and manage the application
"""

import os
import sys
import sqlite3
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / 'jobs.db'
VENV_PATH = PROJECT_ROOT / 'venv'
APP_PID_FILE = PROJECT_ROOT / '.app.pid'

def require_venv():
    """Check if venv is activated or activate it"""
    if not os.environ.get('VIRTUAL_ENV'):
        # Try to activate venv
        activate_script = VENV_PATH / 'bin' / 'activate'
        if not activate_script.exists():
            print("❌ Virtual environment not found!")
            print("   Run: python3 -m venv venv")
            sys.exit(1)
        print(f"⚙️  Activating venv...")
        # For subprocess calls, we'll handle venv activation there
    return True

def run_with_venv(cmd):
    """Run a command with venv activated"""
    if os.environ.get('VIRTUAL_ENV'):
        # Already in venv
        return subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
    else:
        # Run with venv activation
        full_cmd = f"source {VENV_PATH}/bin/activate && {cmd}"
        return subprocess.run(full_cmd, shell=True, cwd=PROJECT_ROOT, executable='/bin/zsh')

def cmd_start(args):
    """Start the Flask app"""
    print("🚀 Starting JobsScraper...")
    if APP_PID_FILE.exists():
        pid = APP_PID_FILE.read_text().strip()
        try:
            os.kill(int(pid), 0)
            print(f"⚠️  App already running (PID: {pid})")
            return
        except ProcessLookupError:
            APP_PID_FILE.unlink()

    require_venv()
    
    if args.bg:
        # Run in background
        print("📱 Running in background... (http://127.0.0.1:5000)")
        result = run_with_venv(f"python3 app.py > app.log 2>&1 &")
        # Try to get the PID from subprocess (won't work perfectly with background)
        print("   Use 'manage.py stop' to stop the app")
    else:
        print("📱 App running at http://127.0.0.1:5000")
        print("   Press Ctrl+C to stop")
        result = run_with_venv("python3 app.py")

def cmd_stop(args):
    """Stop the Flask app"""
    if not APP_PID_FILE.exists():
        # Try to find and kill by name
        print("🛑 Stopping JobsScraper...")
        run_with_venv("pkill -f 'python3 app.py' || true")
        print("✅ App stopped")
        return

    pid = APP_PID_FILE.read_text().strip()
    try:
        os.kill(int(pid), 15)
        APP_PID_FILE.unlink()
        print(f"✅ App stopped (PID: {pid})")
    except ProcessLookupError:
        APP_PID_FILE.unlink()
        print("✅ App was not running")

def cmd_status(args):
    """Check if app is running"""
    result = subprocess.run("pgrep -f 'python3 app.py'", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        pids = result.stdout.strip().split('\n')
        print(f"✅ App is running (PIDs: {', '.join(pids)})")
        print(f"   Access at: http://127.0.0.1:5000")
    else:
        print("❌ App is not running")

def cmd_db_info(args):
    """Show database statistics"""
    if not DB_PATH.exists():
        print("❌ Database not found (app hasn't run yet)")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Total jobs
    c.execute("SELECT COUNT(*) FROM jobs")
    total = c.fetchone()[0]
    
    # Flagged jobs
    c.execute("SELECT COUNT(*) FROM jobs WHERE flag = 1")
    flagged = c.fetchone()[0]
    
    # Jobs by company (top 5)
    c.execute("SELECT company, COUNT(*) FROM jobs GROUP BY company ORDER BY COUNT(*) DESC LIMIT 5")
    top_companies = c.fetchall()
    
    # Oldest and newest
    c.execute("SELECT MIN(created_at), MAX(created_at) FROM jobs")
    dates = c.fetchone()
    
    conn.close()

    print(f"📊 Database Statistics")
    print(f"   Total jobs: {total}")
    print(f"   Flagged: {flagged}")
    print(f"   Not flagged: {total - flagged}")
    if dates[0]:
        print(f"   Date range: {dates[0][:10]} to {dates[1][:10]}")
    if top_companies:
        print(f"\n   Top companies:")
        for company, count in top_companies:
            print(f"      - {company}: {count}")

def cmd_db_clean(args):
    """Clean the database (with confirmation)"""
    if not DB_PATH.exists():
        print("ℹ️  Database not found")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs")
    count = c.fetchone()[0]
    conn.close()

    print(f"⚠️  This will delete {count} jobs from the database.")
    response = input("   Type 'yes' to confirm: ").strip().lower()
    
    if response == 'yes':
        DB_PATH.unlink()
        print("✅ Database cleaned. It will be recreated on next app start.")
    else:
        print("❌ Cancelled")

def cmd_db_flagged(args):
    """Show only flagged jobs"""
    if not DB_PATH.exists():
        print("❌ Database not found")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, title, company, posted_date, comment FROM jobs WHERE flag = 1 ORDER BY company")
    jobs = c.fetchall()
    conn.close()

    if not jobs:
        print("No flagged jobs yet")
        return

    print(f"📌 Flagged Jobs ({len(jobs)})")
    print()
    for job in jobs:
        print(f"   {job['title']} @ {job['company']}")
        if job['comment']:
            print(f"      💬 {job['comment']}")
        print()

def cmd_install(args):
    """Install dependencies in venv"""
    print("📦 Installing dependencies...")
    require_venv()
    
    req_file = PROJECT_ROOT / 'requirements.txt'
    if not req_file.exists():
        print("❌ requirements.txt not found")
        return

    result = run_with_venv(f"python3 -m pip install -r requirements.txt")
    if result.returncode == 0:
        print("✅ Dependencies installed")
    else:
        print("❌ Installation failed")

def cmd_help(args):
    """Show help"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║              JobsScraper Management CLI                        ║
╚════════════════════════════════════════════════════════════════╝

Usage: python3 manage.py <command> [options]

Commands:
  start              Start the web app (Ctrl+C to stop)
  start --bg         Start in background
  stop               Stop the running app
  status             Check if app is running
  
  install            Install Python dependencies (first time only)
  
  db:info            Show database statistics
  db:clean           Delete all jobs from database
  db:flagged         Show all flagged jobs
  
  help               Show this help message

Examples:
  python3 manage.py start           # Start and watch logs
  python3 manage.py start --bg      # Start in background
  python3 manage.py stop            # Stop the app
  python3 manage.py db:info         # View DB stats
  python3 manage.py db:flagged      # View flagged jobs
  python3 manage.py db:clean        # Clear database

Configuration:
  Edit config.yaml to add keywords, locations, and scrapers

Web Interface:
  http://127.0.0.1:5000  (local)
  http://<YOUR_IP>:5000  (from other machines on LAN)

Find your IP: ifconfig | grep "inet "
""")

def main():
    parser = argparse.ArgumentParser(description='JobsScraper Management CLI', add_help=False)
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # start
    start_parser = subparsers.add_parser('start', help='Start the app')
    start_parser.add_argument('--bg', action='store_true', help='Run in background')
    start_parser.set_defaults(func=cmd_start)
    
    # stop
    stop_parser = subparsers.add_parser('stop', help='Stop the app')
    stop_parser.set_defaults(func=cmd_stop)
    
    # status
    status_parser = subparsers.add_parser('status', help='Check app status')
    status_parser.set_defaults(func=cmd_status)
    
    # db:info
    db_info_parser = subparsers.add_parser('db:info', help='Show database info')
    db_info_parser.set_defaults(func=cmd_db_info)
    
    # db:clean
    db_clean_parser = subparsers.add_parser('db:clean', help='Clean database')
    db_clean_parser.set_defaults(func=cmd_db_clean)
    
    # db:flagged
    db_flagged_parser = subparsers.add_parser('db:flagged', help='Show flagged jobs')
    db_flagged_parser.set_defaults(func=cmd_db_flagged)
    
    # install
    install_parser = subparsers.add_parser('install', help='Install dependencies')
    install_parser.set_defaults(func=cmd_install)
    
    # help
    help_parser = subparsers.add_parser('help', help='Show help')
    help_parser.set_defaults(func=cmd_help)
    
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        cmd_help(args)
    elif hasattr(args, 'func'):
        args.func(args)
    else:
        cmd_help(args)

if __name__ == '__main__':
    main()
