
"""
This module contains the logic for header detection and normalization.
"""
import pandas as pd

import re
from typing import List, Dict, Any, Optional, Tuple
from .headers_helper import (
    CANONICAL_HEADERS,
    VARIATIONS_NORM,
    CANON_NORM,
    norm,
    normalize_tokens,
    similarity,
)

def try_immediate_map(raw: Any) -> Dict[str, Any]:
    n = normalize_tokens(norm(raw))
    if not n:
        return {}
    for c, cn in CANON_NORM:
        if n == cn:
            return {"canonical": c, "via": "exact"}
    for c in CANONICAL_HEADERS:
        for v in VARIATIONS_NORM[c]:
            if isinstance(v, re.Pattern):
                if re.fullmatch(v, n):
                    return {"canonical": c, "via": "variation"}
            elif v == n:
                return {"canonical": c, "via": "variation"}
    return {}

def fuzzy_map_one(raw: Any, threshold: float = 0.78) -> Dict[str, Any]:
    n = normalize_tokens(norm(raw))
    if not n:
        return {}
    best = {"score": 0.0}
    for c, cn in CANON_NORM:
        s = similarity(n, cn)
        if s > best["score"]:
            best = {"canonical": c, "score": s}
    return best if best.get("score", 0.0) >= threshold else {}

def looks_like_trading_header(cells: List[Any]) -> Dict[str, float]:
    hits = 0
    for cell in cells:
        if try_immediate_map(cell).get("canonical"):
            hits += 1
    denom = max(len(cells), 1)
    return {"hits": hits, "coverage": hits / denom}

def detect_and_normalize_headers(
    df: pd.DataFrame,
    limit: int = 50,
    min_hits: int = 6,
    min_coverage: float = 0.5,
    fuzzy_threshold: float = 0.78,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    limit = max(1, min(limit, df.shape[0]))
    warnings: List[str] = []
    grid = df.values.tolist()
    header_row: Optional[int] = None
    best_coverage = 0.0

    for r in range(limit):
        row = grid[r]
        stats = looks_like_trading_header(row)
        if stats["coverage"] > best_coverage:
            best_coverage = stats["coverage"]
        if stats["hits"] >= min_hits and stats["coverage"] >= min_coverage:
            header_row = r
            break

    stopped_at = header_row + 1 if header_row is not None else limit
    if header_row is None:
        warnings.append(f"No obvious header found in top {limit} rows; assuming row {limit - 1} as header.")
        header_row = limit - 1

    raw_header = [str(x) if x is not None else '' for x in grid[header_row]]
    data_rows = grid[header_row + 1:]

    recognized: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []
    out_cols: List[str] = [''] * len(raw_header)

    for i, h in enumerate(raw_header):
        m = try_immediate_map(h)
        if m.get("canonical"):
            recognized.append({"index": i, "raw": h, "canonical": m["canonical"], "via": m["via"]})
            out_cols[i] = m["canonical"]
        else:
            unknown.append({"index": i, "raw": h})
            out_cols[i] = h  # provisional

    used_fuzzy = False
    if unknown:
        for u in unknown:
            f = fuzzy_map_one(u["raw"], fuzzy_threshold)
            if f.get("canonical"):
                out_cols[u["index"]] = f["canonical"]
                recognized.append({
                    "index": u["index"],
                    "raw": u["raw"],
                    "canonical": f["canonical"],
                    "via": "fuzzy",
                })
                used_fuzzy = True

    # Ensure header name uniqueness
    seen: Dict[str, int] = {}
    for i, col in enumerate(out_cols):
        count = seen.get(col, 0) + 1
        seen[col] = count
        if count > 1:
            out_cols[i] = f"{col} ({count})"

    out_df = pd.DataFrame(data_rows, columns=out_cols)

    report = {
        "headerRow": header_row,
        "coverage": best_coverage,
        "recognized": sorted(recognized, key=lambda x: x["index"]),
        "unknown": [
            {"index": idx, "raw": raw}
            for idx, raw in enumerate(raw_header)
            if out_cols[idx] not in CANONICAL_HEADERS
        ],
        "usedFuzzy": used_fuzzy,
        "stoppedAt": stopped_at,
        "warnings": warnings,
        "finalHeaders": out_cols,
    }

    return out_df, report
