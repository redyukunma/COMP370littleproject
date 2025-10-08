#!/usr/bin/env python3
import argparse, json, sys, csv, math
from typing import Dict, List, Tuple

def load_theme(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def to_map(theme_json: Dict) -> Dict[str, int]:
    return {t["subject"]: int(t["count"]) for t in theme_json.get("themes", [])}

def jaccard(set1, set2) -> float:
    if not set1 and not set2:
        return 1.0
    return len(set1 & set2) / max(1, len(set1 | set2))

def cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    keys = set(v1) | set(v2)
    dot = sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in keys)
    n1 = math.sqrt(sum(v1.get(k, 0.0)**2 for k in keys))
    n2 = math.sqrt(sum(v2.get(k, 0.0)**2 for k in keys))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)

def normalize(counts: Dict[str, int]) -> Dict[str, float]:
    s = sum(counts.values()) or 1
    return {k: v/s for k, v in counts.items()}

def write_csv(path: str, rows: List[List]):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser(description="Compare two authors' themes")
    ap.add_argument("author1_theme")
    ap.add_argument("author2_theme")
    ap.add_argument("--top", type=int, default=20, help="Top rows to print (default: 20)")
    args = ap.parse_args()

    a1 = load_theme(args.author1_theme)
    a2 = load_theme(args.author2_theme)

    c1 = to_map(a1)
    c2 = to_map(a2)
    n1 = normalize(c1)
    n2 = normalize(c2)
    keys1 = set(c1)
    keys2 = set(c2)

    # Similarities
    jac = jaccard(keys1, keys2)
    cos = cosine_similarity(n1, n2)

    print(f"Author 1: {a1.get('author_name')} ({a1.get('author_key')}) subjects={len(keys1)}")
    print(f"Author 2: {a2.get('author_name')} ({a2.get('author_key')}) subjects={len(keys2)}")
    print(f"Jaccard (set overlap): {jac:.3f}")
    print(f"Cosine similarity (normalized counts): {cos:.3f}")
    print()

    # Shared themes table
    shared = sorted(keys1 & keys2, key=lambda k: (n1.get(k,0)+n2.get(k,0)), reverse=True)
    rows_shared = [["subject","a1_count","a2_count","a1_freq","a2_freq","min_freq","avg_freq"]]
    for k in shared:
        rows_shared.append([k, c1.get(k,0), c2.get(k,0), f"{n1.get(k,0):.4f}", f"{n2.get(k,0):.4f}", f"{min(n1.get(k,0),n2.get(k,0)):.4f}", f"{(n1.get(k,0)+n2.get(k,0))/2:.4f}"])
    write_csv("shared.csv", rows_shared)

    # Distinctive themes: large freq difference
    diff1 = sorted(keys1 - keys2, key=lambda k: n1.get(k,0), reverse=True) + sorted(shared, key=lambda k: (n1.get(k,0)-n2.get(k,0)), reverse=True)
    diff2 = sorted(keys2 - keys1, key=lambda k: n2.get(k,0), reverse=True) + sorted(shared, key=lambda k: (n2.get(k,0)-n1.get(k,0)), reverse=True)

    rows_d1 = [["subject","a1_count","a1_freq","a2_count","a2_freq","freq_gap"]]
    for k in diff1[:max(args.top, 100)]:
        rows_d1.append([k, c1.get(k,0), f"{n1.get(k,0):.4f}", c2.get(k,0), f"{n2.get(k,0):.4f}", f"{(n1.get(k,0)-n2.get(k,0)):.4f}"])
    write_csv("distinctive_author1.csv", rows_d1)

    rows_d2 = [["subject","a2_count","a2_freq","a1_count","a1_freq","freq_gap"]]
    for k in diff2[:max(args.top, 100)]:
        rows_d2.append([k, c2.get(k,0), f"{n2.get(k,0):.4f}", c1.get(k,0), f"{n1.get(k,0):.4f}", f"{(n2.get(k,0)-n1.get(k,0)):.4f}"])
    write_csv("distinctive_author2.csv", rows_d2)

    # Console preview
    print("Top shared themes:")
    for k in shared[:args.top]:
        print(f"  - {k} | a1={c1.get(k,0)} ({n1.get(k,0):.3f}), a2={c2.get(k,0)} ({n2.get(k,0):.3f})")

    print("\nDistinctive for Author 1:")
    for k in diff1[:args.top]:
        print(f"  - {k} | gap={n1.get(k,0)-n2.get(k,0):.3f}")

    print("\nDistinctive for Author 2:")
    for k in diff2[:args.top]:
        print(f"  - {k} | gap={n2.get(k,0)-n1.get(k,0):.3f}")

    # Save a machine-readable summary
    summary = {
        "author1": {"name": a1.get("author_name"), "key": a1.get("author_key")},
        "author2": {"name": a2.get("author_name"), "key": a2.get("author_key")},
        "jaccard": jac, "cosine": cos,
        "counts": {"a1_subjects": len(keys1), "a2_subjects": len(keys2), "shared": len(shared)},
        "artifacts": ["shared.csv", "distinctive_author1.csv", "distinctive_author2.csv"]
    }
    with open("compare_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
