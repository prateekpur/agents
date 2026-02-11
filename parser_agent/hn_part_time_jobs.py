#!/usr/bin/env python3
"""
Parse YCombinator Hacker News "Who is Hiring?" threads to find part-time opportunities.

Uses the official HN Firebase API:
  - Algolia Search API to find the latest "Who is hiring?" thread
  - Firebase Item API to fetch each comment (job posting)

Filters comments for part-time/contract/freelance keywords and outputs
clean, readable results.
"""

import argparse
import html
import json
import re
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    _HAS_BS4 = False

# ── API endpoints ──────────────────────────────────────────────────────────────
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"

# ── Keywords that signal part-time / flexible work ─────────────────────────────
PART_TIME_KEYWORDS = [
    r"\bpart[\s-]?time\b",
    r"\bcontract\b",
    r"\bfreelance\b",
    r"\bconsulting\b",
    r"\bfractional\b",
    r"\bflexible hours\b",
    r"\bflexible schedule\b",
    r"\b\d{1,2}[\s-]?hours?\s*/\s*week\b",   # e.g. "20 hours/week", "10-20 hours / week"
    r"\bproject[\s-]?based\b",
    r"\bhourly\b",
]

COMPILED_KEYWORDS = [re.compile(kw, re.IGNORECASE) for kw in PART_TIME_KEYWORDS]

# Simple in-memory cache for fetched items to avoid refetching
_ITEM_CACHE: Dict[int, Dict[str, Any]] = {}


def get_session(retries: int = 3, backoff: float = 0.5, status_forcelist=(429, 500, 502, 503, 504)) -> requests.Session:
    """Return a requests.Session configured with retries and connection pooling."""
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist, allowed_methods=frozenset(["GET"]))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def strip_html(text: str) -> str:
    """Remove HTML and decode entities. Uses BeautifulSoup when available.

    Falls back to a conservative regex-based approach if BeautifulSoup is not installed.
    """
    if not text:
        return ""
    text = html.unescape(text)
    if _HAS_BS4:
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text("\n")
    else:
        cleaned = re.sub(r"<[^>]+>", "\n", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def find_latest_thread(month: Optional[str] = None, session: Optional[requests.Session] = None) -> dict:
    """
    Find the latest "Ask HN: Who is hiring?" thread via Algolia.
    If `month` is given (e.g. "February 2026"), search for that specific month.
    """
    query = "Ask HN: Who is hiring?"
    if month:
        query += f" ({month})"

    params = {
        "query": query,
        "tags": "story,author_whoishiring",
        "hitsPerPage": 5,
    }
    session = session or get_session()
    resp = session.get(ALGOLIA_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    for hit in hits:
        title = hit.get("title", "").lower()
        if "who is hiring" in title and "who wants" not in title and "freelancer" not in title:
            return hit

    raise SystemExit("Could not find a 'Who is hiring?' thread. Try specifying --month.")


def fetch_item(item_id: int, session: Optional[requests.Session] = None) -> Optional[dict]:
    """Fetch a single HN item (story or comment) by ID. Uses a session and a small cache."""
    if item_id in _ITEM_CACHE:
        return _ITEM_CACHE[item_id]
    session = session or get_session()
    try:
        resp = session.get(HN_ITEM_URL.format(item_id), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            _ITEM_CACHE[item_id] = data
        return data
    except requests.RequestException as exc:
        logging.debug("Failed to fetch item %s: %s", item_id, exc)
        return None


def fetch_comments(comment_ids: List[int], max_workers: int = 10, include_replies: bool = False, session: Optional[requests.Session] = None) -> List[dict]:
    """Fetch comments in parallel. Optionally include nested replies (descendants).

    This will iteratively fetch children when `include_replies` is True.
    """
    session = session or get_session()
    comments: List[dict] = []
    todo_ids = list(dict.fromkeys(comment_ids))  # unique preserving order
    total_started = len(todo_ids)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        while todo_ids:
            futures = {pool.submit(fetch_item, cid, session): cid for cid in todo_ids}
            todo_ids = []
            for future in as_completed(futures):
                cid = futures[future]
                result = future.result()
                if not result:
                    continue
                if result.get("deleted") or result.get("dead"):
                    continue
                if result.get("text"):
                    comments.append(result)
                # if including replies, add children to next round
                if include_replies and result.get("kids"):
                    for child in result.get("kids", []):
                        if child not in _ITEM_CACHE:
                            todo_ids.append(child)
            if total_started and (len(comments) % 50 == 0 or len(comments) >= total_started):
                logging.info("Fetched %d comments (so far)", len(comments))

    return comments


def matches_part_time(text: str, compiled_patterns: List[re.Pattern]) -> List[str]:
    """Return list of matched keyword strings (with short context)."""
    matched: List[str] = []
    for pattern in compiled_patterns:
        m = pattern.search(text)
        if m:
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            snippet = text[start:end].replace("\n", " ")
            matched.append(snippet.strip())
    return matched


def extract_first_line(text: str) -> str:
    """Extract the first non-empty line as a rough title/company name."""
    for line in text.split("\n"):
        line = line.strip()
        if line:
            return line[:120]
    return "(no title)"


def format_comment(comment: dict, matched_keywords: List[str]) -> str:
    """Format a single comment for display."""
    raw_text = comment.get("text", "")
    clean = strip_html(raw_text)
    title = extract_first_line(clean)
    author = comment.get("by", "unknown")
    item_id = comment.get("id", "")
    url = f"https://news.ycombinator.com/item?id={item_id}"
    ts = comment.get("time", 0)
    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"

    separator = "─" * 80
    return (
        f"{separator}\n"
        f"🏢 {title}\n"
        f"   👤 {author} | 📅 {date_str}\n"
        f"   🔗 {url}\n"
        f"   🏷️  Matched: {', '.join(matched_keywords)}\n"
        f"\n{clean}\n"
    )


def compile_keywords(extra: Optional[List[str]] = None) -> List[re.Pattern]:
    pats = PART_TIME_KEYWORDS.copy()
    if extra:
        for e in extra:
            # escape plain keywords, allow phrase matching
            pats.append(re.escape(e))
    return [re.compile(p, re.IGNORECASE) for p in pats]


def main():
    parser = argparse.ArgumentParser(
        description="Find part-time opportunities from HN 'Who is Hiring?' threads"
    )
    parser.add_argument(
        "--month",
        type=str,
        default=None,
        help="Target month, e.g. 'February 2026'. Defaults to latest thread.",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        default=None,
        help="Additional keywords to search for (e.g. 'python' 'remote').",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of formatted text.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel HTTP workers (default: 20).",
    )
    parser.add_argument(
        "--include-replies",
        action="store_true",
        dest="include_replies",
        help="Also fetch nested replies under each top-level posting.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. 'text' or 'json'.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="hn_part_time_jobs 1.1",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write results to file instead of stdout.",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    session = get_session()

    # 1. Find the thread
    search_target = args.month or "latest"
    logging.info("Searching for '%s' Who is hiring thread...", search_target)
    thread = find_latest_thread(args.month, session=session)
    title = thread.get("title", "Unknown")
    story_id = thread.get("objectID") or thread.get("story_id")
    thread_url = f"https://news.ycombinator.com/item?id={story_id}"
    logging.info("Found: %s", title)
    logging.info("Thread URL: %s", thread_url)

    # 2. Fetch the story to get top-level comment IDs
    logging.info("Fetching thread data...")
    story = fetch_item(int(story_id), session=session)
    if not story:
        logging.error("Failed to fetch the thread. Try again later.")
        raise SystemExit(2)

    comment_ids = story.get("kids", [])
    logging.info("Found %d top-level job postings", len(comment_ids))

    # 3. Fetch all comments in parallel
    logging.info("Downloading comments (workers=%d) ...", args.workers)
    comments = fetch_comments(comment_ids, max_workers=args.workers, include_replies=args.include_replies, session=session)
    logging.info("Got %d valid comments", len(comments))

    # 4. Filter for part-time keywords
    logging.info("Filtering for part-time / contract / freelance...")
    results = []
    patterns = compile_keywords(args.keywords)
    for comment in comments:
        text = strip_html(comment.get("text", ""))

        matched = matches_part_time(text, patterns)
        if not matched:
            continue

        if args.keywords:
            extra_pattern = "|".join(re.escape(kw) for kw in args.keywords)
            if not re.search(extra_pattern, text, re.IGNORECASE):
                continue

        results.append({
            "comment": comment,
            "matched_keywords": matched,
            "clean_text": text,
            "title": extract_first_line(text),
        })

    logging.info("Found %d part-time opportunities", len(results))

    # 5. Output results
    if args.json_output or args.format == "json":
        json_results = []
        for r in results:
            json_results.append({
                "id": r["comment"].get("id"),
                "by": r["comment"].get("by"),
                "time": r["comment"].get("time"),
                "url": f"https://news.ycombinator.com/item?id={r['comment'].get('id')}",
                "title": r["title"],
                "matched_keywords": r["matched_keywords"],
                "text": r["clean_text"],
            })
        output = json.dumps(json_results, indent=2, ensure_ascii=False)
    else:
        header = (
            f"{'═' * 80}\n"
            f"  HN 'Who is Hiring?' — Part-Time Opportunities\n"
            f"  Thread: {title}\n"
            f"  Results: {len(results)} matches\n"
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"{'═' * 80}\n"
        )
        body = "\n".join(format_comment(r["comment"], r["matched_keywords"]) for r in results)
        output = header + "\n" + body

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        logging.info("Results written to %s", args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()
