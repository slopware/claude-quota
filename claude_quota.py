#!/usr/bin/env python3
"""Claude Code status line: drop-in replacement that adds 5h plan usage.

Reads the full session JSON from stdin (provided by Claude Code) and displays
model, directory, context window bar, cost, and 5h rate limit quota bar.

Zero dependencies beyond the Python standard library.

Install:
  1. Copy this file to ~/.claude/usage_statusline.py
  2. Set in ~/.claude/settings.json:
     {
       "statusLine": {
         "command": "python3 ~/.claude/usage_statusline.py"
       }
     }

Flags (default: show everything):
  --model     Show model name
  --dir       Show current directory
  --context   Show context window usage bar
  --cost      Show session cost
  --quota     Show 5h rate limit usage bar
  --reset     Show time until quota resets (requires --quota)

Examples:
  python3 ~/.claude/usage_statusline.py                  # show all
  python3 ~/.claude/usage_statusline.py --quota --reset  # quota only
  python3 ~/.claude/usage_statusline.py --context --quota --reset  # context + quota
"""

import io
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CREDENTIALS_FILE = os.path.expanduser("~/.claude/.credentials.json")
CACHE_FILE = os.path.expanduser("~/.claude/usage_cache.json")
CACHE_TTL_SECONDS = 60

FILL = "\u2588"
EMPTY = "\u2591"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"


# --- OAuth usage API ---

def get_access_token():
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            creds = json.load(f)
        return creds.get("claudeAiOauth", {}).get("accessToken")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def fetch_usage(access_token):
    try:
        req = urllib.request.Request(USAGE_URL, headers={
            "Authorization": f"Bearer {access_token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
            "User-Agent": "claude-code/1.0",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return json.loads(resp.read())
    except Exception:
        pass
    return None


def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_cache(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "data": data}, f)
    except Exception:
        pass


def get_usage():
    cache = load_cache()
    if cache and (time.time() - cache["timestamp"]) < CACHE_TTL_SECONDS:
        return cache["data"]

    access_token = get_access_token()
    if not access_token:
        return cache["data"] if cache else None

    data = fetch_usage(access_token)
    if data and "five_hour" in data:
        save_cache(data)
        return data

    # Fetch failed (rate limit, network error, etc.) — update cache timestamp
    # so we back off instead of retrying every statusline refresh
    if cache:
        save_cache(cache["data"])
        return cache["data"]
    return None


def time_until_reset(resets_at_str):
    try:
        resets_at = datetime.fromisoformat(resets_at_str)
        now = datetime.now(timezone.utc)
        total_seconds = int((resets_at - now).total_seconds())
        if total_seconds <= 0:
            return "now"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h{minutes:02d}m"
        return f"{minutes}m"
    except Exception:
        return "?"


# --- Rendering ---

def render_bar(pct, width=10):
    pct = max(0, min(100, pct))
    filled = round(pct / 100 * width)
    empty = width - filled

    if pct >= 80:
        color = RED
    elif pct >= 50:
        color = YELLOW
    else:
        color = GREEN

    return f"{color}{FILL * filled}{DIM}{EMPTY * empty}{RESET}"


def parse_flags():
    args = set(sys.argv[1:])
    all_flags = {"--model", "--dir", "--context", "--cost", "--quota", "--reset"}
    specified = args & all_flags
    if not specified:
        defaults = {f: True for f in all_flags}
        defaults["--cost"] = False
        return defaults
    return {f: f in specified for f in all_flags}


def main():
    flags = parse_flags()

    try:
        session = json.load(sys.stdin)
    except Exception:
        session = {}

    segments = []

    if flags["--model"]:
        model = session.get("model", {}).get("display_name")
        if model:
            segments.append(f"{CYAN}{model}{RESET}")

    if flags["--dir"]:
        cwd = session.get("workspace", {}).get("current_dir") or session.get("cwd")
        if cwd:
            segments.append(f"{DIM}{os.path.basename(cwd)}{RESET}")

    if flags["--context"]:
        ctx = session.get("context_window", {})
        pct = ctx.get("used_percentage")
        if pct is not None:
            pct = int(pct)
            bar = render_bar(pct)
            segments.append(f"{bar} {DIM}{pct}%{RESET}")
        elif session:
            segments.append(f"{DIM}{EMPTY * 10} no data yet{RESET}")

    if flags["--cost"]:
        cost = session.get("cost", {}).get("total_cost_usd")
        if cost is not None:
            segments.append(f"{DIM}${cost:.2f}{RESET}")

    if flags["--quota"]:
        usage = get_usage()
        if usage and usage.get("five_hour"):
            util = usage["five_hour"]["utilization"]
            bar = render_bar(util)
            parts = [f"{CYAN}5h{RESET} {bar} {util:.0f}%"]
            if flags["--reset"]:
                resets_at = usage["five_hour"].get("resets_at", "")
                if resets_at:
                    parts.append(f"{DIM}resets {time_until_reset(resets_at)}{RESET}")
            segments.append(f" {DIM}\u00b7{RESET} ".join(parts))

    if segments:
        print("  ".join(segments))


if __name__ == "__main__":
    main()
