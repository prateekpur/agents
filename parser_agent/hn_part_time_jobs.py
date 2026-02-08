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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import requests

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


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "\n", text)
    
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_latest_thread(month: Optional[str] = None) -> dict:
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
    resp = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    for hit in hits:
        title = hit.get("title", "").lower()
        if "who is hiring" in title and "who wants" not in title and "freelancer" not in title:
            return hit

    raise SystemExit("❌ Could not find a 'Who is hiring?' thread. Try specifying --month.")


def fetch_item(item_id: int) -> Optional[dict]:
    """Fetch a single HN item (story or comment) by ID."""
    try:
        resp = requests.get(HN_ITEM_URL.format(item_id), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def fetch_comments(comment_ids: list[int], max_workers: int = 20) -> list[dict]:
    """Fetch all comments in parallel."""
    comments = []
    total = len(comment_ids)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_item, cid): cid for cid in comment_ids}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == total:
                print(f"  Fetched {done}/{total} comments...", file=sys.stderr)
            result = future.result()
            if result and result.get("text") and not result.get("deleted") and not result.get("dead"):
                comments.append(result)

    return comments


def matches_part_time(text: str) -> list[str]:
    """Return list of matched keyword patterns in the text."""
    matched = []
    for pattern in COMPILED_KEYWORDS:
        m = pattern.search(text)
        if m:
            matched.append(m.group())
    return matched


def extract_first_line(text: str) -> str:
    """Extract the first non-empty line as a rough title/company name."""
    for line in text.split("\n"):
        line = line.strip()
        if line:
            return line[:120]
    return "(no title)"


def format_comment(comment: dict, matched_keywords: list[str]) -> str:
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
        default=20,
        help="Number of parallel HTTP workers (default: 20).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write results to file instead of stdout.",
    )
    args = parser.parse_args()

    # 1. Find the thread
    search_target = args.month or "latest"
    print(f"🔍 Searching for '{search_target}' Who is hiring thread...", file=sys.stderr)
    thread = find_latest_thread(args.month)
    title = thread.get("title", "Unknown")
    story_id = thread.get("objectID") or thread.get("story_id")
    thread_url = f"https://news.ycombinator.com/item?id={story_id}"
    print(f"📋 Found: {title}", file=sys.stderr)
    print(f"   🔗 {thread_url}", file=sys.stderr)

    # 2. Fetch the story to get top-level comment IDs
    print("\n📥 Fetching thread data...", file=sys.stderr)
    story = fetch_item(int(story_id))
    if not story:
        raise SystemExit("❌ Failed to fetch the thread. Try again later.")

    comment_ids = story.get("kids", [])
    print(f"   Found {len(comment_ids)} top-level job postings", file=sys.stderr)

    # 3. Fetch all comments in parallel
    print("\n⬇️  Downloading all comments...", file=sys.stderr)
    comments = fetch_comments(comment_ids, max_workers=args.workers)
    print(f"   Got {len(comments)} valid comments", file=sys.stderr)

    # 4. Filter for part-time keywords
    print("\n🔎 Filtering for part-time / contract / freelance...", file=sys.stderr)
    results = []
    for comment in comments:
        text = strip_html(comment.get("text", ""))

        matched = matches_part_time(text)
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

    print(f"   ✅ Found {len(results)} part-time opportunities!\n", file=sys.stderr)

    # 5. Output results
    if args.json_output:
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
        print(f"📝 Results written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
