# claude-quota

A drop-in Claude Code statusline script that shows your 5-hour rate limit usage bar — the one thing the built-in statusline doesn't give you.

```
Opus  my-project  ██████░░░░ 30%  5h ███░░░░░░░ 28% · resets 3h42m
```

## What it does

- Shows your **5-hour plan quota** as a color-coded progress bar (green → yellow → red)
- Shows **time until reset** so you know when your limit refills
- Also renders the standard statusline info (model, directory, context window) so you don't lose anything
- Uses Claude Code's own OAuth credentials — no separate auth setup needed
- Caches API responses for 60 seconds to avoid hammering the endpoint
- Zero dependencies beyond the Python standard library

## Requirements

- Claude Code with an active Pro or Max subscription (OAuth login, not API key)
- Python 3.7+

## Install

1. Copy `claude_quota.py` to `~/.claude/`:

```bash
curl -o ~/.claude/claude_quota.py https://raw.githubusercontent.com/slopware/claude-quota/main/claude_quota.py
```

2. Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "command": "python3 ~/.claude/claude_quota.py"
  }
}
```

Or just paste the script into Claude Code and say **"save this as my statusline script"** — it'll handle both steps.

> **Windows users:** You may need to use `python` instead of `python3` in the command.

## Flags

By default (no flags), model, directory, context, quota, and reset are shown. Pass flags to show only what you want:

| Flag | Description |
|------|-------------|
| `--model` | Model name (e.g. Opus) |
| `--dir` | Current directory |
| `--context` | Context window usage bar |
| `--cost` | Session cost in USD (off by default, useful for API key users) |
| `--quota` | 5-hour rate limit bar |
| `--reset` | Time until quota resets (use with `--quota`) |

### Examples

```bash
# Show everything (default)
python3 ~/.claude/claude_quota.py

# Quota bar + reset timer only
python3 ~/.claude/claude_quota.py --quota --reset

# Context window + quota
python3 ~/.claude/claude_quota.py --context --quota --reset

# Just tell Claude what you want:
# "only show the quota bar and time left in my statusline"
# → it will set: python3 ~/.claude/claude_quota.py --quota --reset
```

## How it works

Claude Code's statusline runs a shell command and pipes session JSON to stdin. This script:

1. Reads the session JSON for context window, model, etc.
2. Reads the OAuth token from `~/.claude/.credentials.json` (auto-managed by Claude Code)
3. Calls `https://api.anthropic.com/api/oauth/usage` to get your 5-hour utilization
4. Caches the response for 60 seconds
5. Prints everything in one line with color-coded bars

No extra auth, no API keys, no dependencies to install.

## Notes

- Only works with Pro/Max plans using OAuth login. API key users won't have quota data (the standard statusline fields still work)
- If you use the `/statusline` slash command in Claude Code, it will overwrite your settings. Just re-set the command afterward
- The OAuth token refresh is handled by Claude Code itself — no maintenance needed on your end

## License

MIT
