#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus


QUERIES = [
    {
        "name": "byovd-killers",
        "q": '"BYOVD" AND (kill OR antiav OR antiedr) in:name,description,readme',
    },
    {
        "name": "edr-evasion",
        "q": '"EDR" AND (evasion OR bypass OR kill) in:name,description,readme',
    },
    {
        "name": "kernel-exploit",
        "q": '"kernel exploit" AND (windows OR driver) in:name,description,readme',
    },

]


DAYS_LOOKBACK = 30


PER_PAGE = 50


RESULTS_FILE = Path("previous_results.json")
LOG_FILE = Path("monitor.log")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
# ─────────────────────────────────────────────


def log(message: str, level: str = "INFO"):
    """Scrive un messaggio nel log e su stdout."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] [{level}] {message}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def github_request(url: str) -> dict:
    
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-keyword-watcher/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 403:
            raise RuntimeError("Rate limit raggiunto. Imposta GITHUB_TOKEN per aumentare i limiti.") from e
        if e.code == 422:
            raise RuntimeError(f"Query non valida: {url}") from e
        raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Errore di rete: {e.reason}") from e


def search_repositories(query_name: str, query_str: str, days: int) -> list[dict]:
    """Cerca repository GitHub creati negli ultimi `days` giorni con una query booleana avanzata."""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    # Appende il filtro data alla query e codifica per l'URL
    full_query = quote_plus(f"{query_str} created:>={since}")
    url = (
        f"https://api.github.com/search/repositories"
        f"?q={full_query}&sort=updated&order=desc&per_page={PER_PAGE}"
    )

    data = github_request(url)
    items = data.get("items", [])

    results = []
    for item in items:
        results.append({
            "id": item["id"],
            "full_name": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description") or "",
            "stars": item["stargazers_count"],
            "updated_at": item.get("updated_at", ""),
            "pushed_at": item.get("pushed_at", ""),
            "language": item.get("language") or "N/A",
            "created_at": item["created_at"],
            "topics": item.get("topics", []),
            "query": query_name,
        })
    return results


def load_previous_results() -> dict:
   
    if not RESULTS_FILE.exists():
        return {}
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            log("File previous_results.json corrotto, ripartendo da zero.", "WARN")
            return {}


def save_results(results: dict):
    
    # Backup
    if RESULTS_FILE.exists():
        RESULTS_FILE.rename(RESULTS_FILE.with_suffix(".json.bk"))
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def format_repo(repo: dict) -> str:
    
    desc = repo["description"][:80] + "…" if len(repo["description"]) > 80 else repo["description"]
    topics = ", ".join(repo["topics"]) if repo["topics"] else "—"
    return (
        f"  📦 {repo['full_name']}\n"
        f"     ⭐ {repo['stars']}  🗣 {repo['language']}  📅 {repo['created_at'][:10]}\n"
        f"     🔗 {repo['url']}\n"
        f"     📝 {desc or '(nessuna descrizione)'}\n"
        f"     🏷  {topics}"
    )


def main():
    query_names = [q["name"] for q in QUERIES]

    log("=" * 60)
    log("GitHub Keyword Watcher avviato")
    log(f"Query monitorate: {', '.join(query_names)}")
    log(f"Finestra temporale: ultimi {DAYS_LOOKBACK} giorni")
    log(f"Token GitHub: {'✓ presente' if GITHUB_TOKEN else '✗ assente (rate limit 10 req/min)'}")
    log("=" * 60)

    previous = load_previous_results()
    current_run: dict[str, dict] = {}
    new_found = 0
    errors = 0

    for entry in QUERIES:
        name = entry["name"]
        q_str = entry["q"]
        log(f"Ricerca query: '{name}'")
        log(f"  ↳ {q_str}")
        try:
            repos = search_repositories(name, q_str, DAYS_LOOKBACK)
            log(f"  → {len(repos)} repository trovati in totale")

            prev_ids = set(previous.get(name, {}).get("seen_ids", []))
            new_repos = [r for r in repos if str(r["id"]) not in prev_ids]

            if new_repos:
                log(f"  🆕 {len(new_repos)} NUOVI repository:", "NEW")
                for repo in new_repos:
                    log(format_repo(repo), "NEW")
                    new_found += 1
            else:
                log("  ✓ Nessuna novità rispetto all'ultima esecuzione")

            all_ids = list(prev_ids | {str(r["id"]) for r in repos})
            current_run[name] = {
                "last_check": datetime.now(timezone.utc).isoformat(),
                "query": q_str,
                "seen_ids": all_ids,
                "last_new": [r["full_name"] for r in new_repos],
                "last_results": repos,
            }

        except RuntimeError as e:
            log(f"  ✗ Errore per '{name}': {e}", "ERROR")
            current_run[name] = previous.get(name, {})
            errors += 1

    save_results(current_run)

    log("=" * 60)
    log(f"Esecuzione completata — {new_found} nuovi repo trovati, {errors} errori")
    log("=" * 60)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
