#!/usr/bin/env python3
import argparse, json, re, sys, time
from typing import Dict, Any, List, Tuple
import requests

SEARCH_URL = "https://openlibrary.org/search/authors.json"
AUTHOR_URL = "https://openlibrary.org/authors/{key}.json"
WORKS_URL = "https://openlibrary.org/authors/{key}/works.json"

HEADERS = {"User-Agent": "AuthorSubjectAnalysis/1.0 (academic use)"}

def is_author_key(s: str) -> bool:
    return bool(re.fullmatch(r"OL\d+A", s.strip()))

def pick_best_author(hitlist: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Heuristic: choose the hit with the most work_count, falling back to the first.
    Returns (author_key, author_name).
    """
    if not hitlist:
        raise SystemExit("No author found by that name.")
    best = max(hitlist, key=lambda d: d.get("work_count", 0))
    key = best.get("key") or best.get("id") or ""
    # 'key' often looks like '/authors/OLxxxxA' — normalize to 'OLxxxxA'
    if key.startswith("/authors/"):
        key = key.split("/")[-1]
    return key, best.get("name") or ""

def resolve_author(query: str) -> Tuple[str, str]:
    if is_author_key(query):
        # fetch name
        r = requests.get(AUTHOR_URL.format(key=query), headers=HEADERS, timeout=30)
        r.raise_for_status()
        name = r.json().get("name", query)
        return query, name
    # search by name
    r = requests.get(SEARCH_URL, params={"q": query}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    key, name = pick_best_author(data.get("docs", []))
    if not name:
        name = query
    return key, name

def fetch_works(author_key: str, max_pages: int = 200, page_size: int = 100, sleep_s: float = 0.2):
    all_entries = []
    offset = 0
    for _ in range(max_pages):
        r = requests.get(WORKS_URL.format(key=author_key), params={"limit": page_size, "offset": offset}, headers=HEADERS, timeout=60)
        r.raise_for_status()
        data = r.json()
        entries = data.get("entries", [])
        if not entries:
            break
        for e in entries:
            # Normalize subjects across different fields
            subjects = set()
            for field in ("subjects", "subject_places", "subject_times", "subject_people"):
                vals = e.get(field) or []
                for v in vals:
                    if isinstance(v, str):
                        subjects.add(v.strip())
            all_entries.append({
                "key": e.get("key"),
                "title": e.get("title"),
                "subjects": sorted(subjects),
                "first_publish_year": e.get("first_publish_year"),
            })
        offset += page_size
        time.sleep(sleep_s)
    return all_entries

def main():
    ap = argparse.ArgumentParser(description="Collect an author's works and subjects from Open Library.")
    ap.add_argument("author", help="Author name (e.g., 'Agatha Christie') or Open Library author key (e.g., 'OL34184A').")
    ap.add_argument("--page-size", type=int, default=100, help="API page size (default: 100).")
    ap.add_argument("--max-pages", type=int, default=200, help="Maximum number of pages to fetch (default: 200).")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between requests (default: 0.2).")
    args = ap.parse_args()

    key, name = resolve_author(args.author)
    works = fetch_works(key, max_pages=args.max_pages, page_size=args.page_size, sleep_s=args.sleep)

    out = {
        "author_key": key,
        "author_name": name,
        "total_works": len(works),
        "works": works,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
