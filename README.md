# 👁️ TheWatcher

> Automated GitHub surveillance for BYOVD, EDR evasion, and kernel exploit research — running silently, every 2 hours.

---

## What it does

TheWatcher continuously scans GitHub for newly published repositories matching advanced boolean queries focused on offensive security research. Every 2 hours, GitHub Actions wakes it up, runs the search, compares against the previous state, and logs anything new.

No noise. No duplicates. Just new signal.

---

## Monitored queries

| Name | Query |
|------|-------|
| `byovd-killers` | `"BYOVD" AND (kill OR antiav OR antiedr) in:name,description,readme` |
| `edr-evasion` | `"EDR" AND (evasion OR bypass OR kill) in:name,description,readme` |
| `kernel-exploit` | `"kernel exploit" AND (windows OR driver) in:name,description,readme` |

Queries are fully customizable in `watcher.py`.

---

## How it works

```
GitHub Actions  (every 2h / manual trigger)
      │
      ▼
  watcher.py
      ├── calls GitHub Search API for each query
      ├── compares results with previous_results.json
      ├── logs NEW repos to monitor.log  [NEW]
      └── saves updated state to previous_results.json
```

---

## Files

| File | Description |
|------|-------------|
| `watcher.py` | Main script — queries, logic, logging |
| `.github/workflows/watcher.yml` | GitHub Actions automation |
| `previous_results.json` | Seen repo state (auto-updated) |
| `monitor.log` | Full run history with all findings |

---

## Reading the results

Open `monitor.log` — new repositories are marked with `[NEW]`:

```
[2026-05-05 08:46:44 UTC] [INFO] ============================================================
[2026-05-05 08:46:44 UTC] [INFO] GitHub Keyword Watcher avviato
[2026-05-05 08:46:44 UTC] [INFO] Ricerca query: 'byovd-killers'
[2026-05-05 08:46:44 UTC] [NEW]    🆕 3 NUOVI repository:
[2026-05-05 08:46:44 UTC] [NEW]    📦 user/byovd-tool
                                      ⭐ 12  🗣 C  📅 2026-05-05
                                      🔗 https://github.com/user/byovd-tool
```

---

## Customization

Edit the `QUERIES` list in `watcher.py`:

```python
QUERIES = [
    {
        "name": "my-query",
        "q": '"rootkit" AND (windows OR linux) in:name,description,readme',
    },
]
```

Change the lookback window (default: last 24h):

```python
DAYS_LOOKBACK = 1
```

Change the schedule in `watcher.yml` (default: every 2h):

```yaml
- cron: "0 */2 * * *"   # every 6 hours
- cron: "0 8 * * *"     # daily at 08:00 UTC
```

---

## Run manually

```bash
python watcher.py

# with a GitHub token (higher rate limits)
GITHUB_TOKEN=ghp_xxx python watcher.py
```

Requires Python 3.10+. No external dependencies.

---

## GitHub Search syntax reference

| Operator | Example |
|----------|---------|
| `AND` | `"BYOVD" AND kill` |
| `OR` | `(kill OR bypass OR evade)` |
| `NOT` | `NOT archived` |
| `in:name` | search in repo name only |
| `in:description` | search in description only |
| `in:readme` | search in README |
| `stars:>N` | repos with more than N stars |
| `language:C` | filter by language |

---

*Runs on GitHub Actions. Zero cost on public repositories.*
