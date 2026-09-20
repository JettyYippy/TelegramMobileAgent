import os
import sys
import glob
import re
import argparse
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"

# Ensure Windows terminal doesn't crash on emojis
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def get_task_logs():
    """Finds all task logs from the app task log storage."""
    home_dir = Path.home()
    app_tasks_dir = home_dir / ".gemini" / "antigravity" / "brain"
    task_files = []
    if app_tasks_dir.exists():
        for log_path in app_tasks_dir.glob("**/.system_generated/tasks/*.log"):
            task_files.append(log_path)
    return sorted(task_files, key=os.path.getmtime, reverse=True)

def view_logs(date_str: str = None, keyword: str = None, max_lines: int = 40):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().strftime("%Y-%m-%d")
    target_date = date_str or today

    # Check for dedicated daily log file first
    daily_error_file = LOGS_DIR / f"errors_{target_date}.log"
    agent_log_file = LOGS_DIR / f"agent_{target_date}.log"

    print(f"==================================================")
    print(f"📋 TelegramMobileAgent Log Viewer ({target_date})")
    print(f"==================================================")

    pattern = re.compile(keyword or r"error|exception|traceback|failed|timed out|404|429|503", re.IGNORECASE)
    
    matches_found = 0
    
    # 1. Search in local logs directory
    for log_f in [agent_log_file, daily_error_file]:
        if log_f.exists():
            print(f"\n📂 Checking local log: {log_f.name}")
            with open(log_f, "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, 1):
                    if pattern.search(line):
                        print(f"  [{log_f.stem}:{line_no}] {line.strip()}")
                        matches_found += 1
                        if matches_found >= max_lines:
                            break
            if matches_found >= max_lines:
                break

    # 2. Search recent task logs if few local matches
    if matches_found < 10:
        task_logs = get_task_logs()
        for task_log in task_logs[:5]:
            mdate = datetime.datetime.fromtimestamp(os.path.getmtime(task_log)).strftime("%Y-%m-%d")
            if date_str and mdate != date_str:
                continue
            with open(task_log, "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, 1):
                    if pattern.search(line):
                        print(f"  [{task_log.name}:{line_no}] {line.strip()[:140]}")
                        matches_found += 1
                        if matches_found >= max_lines:
                            break
            if matches_found >= max_lines:
                break

    if matches_found == 0:
        print(f"\n✅ No matching log entries found for filter: '{keyword or 'error/exception'}'.")
    else:
        print(f"\n📊 Total matching entries shown: {matches_found}")
        print(f"📁 Full detailed error log saved at: {daily_error_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View and filter TelegramMobileAgent logs.")
    parser.add_argument("--date", "-d", type=str, default=None, help="Date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--keyword", "-k", type=str, default=None, help="Keyword filter (e.g., 429, 404, error, timeout)")
    parser.add_argument("--lines", "-n", type=int, default=50, help="Maximum lines to display (default: 50)")
    args = parser.parse_args()

    view_logs(date_str=args.date, keyword=args.keyword, max_lines=args.lines)
