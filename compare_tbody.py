# compare_tables.py
from bs4 import BeautifulSoup
import sys, re, json
from pathlib import Path

WS = re.compile(r"\s+", re.UNICODE)

def norm_text(s: str) -> str:
    if s is None: return ""
    s = s.replace("\u00a0", " ").replace("\u3000", " ")
    s = WS.sub(" ", s).strip()
    return s

def ensure_tbody(html: str) -> str:
    h = html.strip()
    if "<tbody" in h or h.startswith("<table"):
        return h
    
    return f"<table><tbody>{h}</tbody></table>"

def extract_rows(html: str):
    doc = BeautifulSoup(ensure_tbody(html), "lxml")
    tb = doc.tbody or doc.find("table") or doc
    rows = []
    for tr in tb.find_all("tr", recursive=True):
        cells = []
        for cell in tr.find_all(["th", "td"], recursive=False):
            cells.append({
                "text": norm_text(cell.get_text(separator=" ", strip=True)),
                "colspan": int(cell.get("colspan", 1)),
                "rowspan": int(cell.get("rowspan", 1)),
            })
        
        if cells: rows.append(cells)
    return rows

def compare_rows(A, B):
    diffs = []
    max_r = max(len(A), len(B))
    for r in range(max_r):
        if r >= len(A):
            diffs.append({"type":"missing_row_in_A", "row": r, "cells_in_B": len(B[r])})
            continue
        if r >= len(B):
            diffs.append({"type":"missing_row_in_B", "row": r, "cells_in_A": len(A[r])})
            continue
        ra, rb = A[r], B[r]
        if len(ra) != len(rb):
            diffs.append({"type":"cell_count_diff", "row": r, "A": len(ra), "B": len(rb)})
        mc = max(len(ra), len(rb))
        for c in range(mc):
            if c >= len(ra):
                diffs.append({"type":"missing_cell_in_A", "row": r, "col": c, "B": rb[c]})
                continue
            if c >= len(rb):
                diffs.append({"type":"missing_cell_in_B", "row": r, "col": c, "A": ra[c]})
                continue
            a, b = ra[c], rb[c]
            reasons = []
            if a["text"] != b["text"]: reasons.append("text")
            if a["colspan"] != b["colspan"]: reasons.append("colspan")
            if a["rowspan"] != b["rowspan"]: reasons.append("rowspan")
            if reasons:
                diffs.append({"type":"mismatch", "row": r, "col": c, "reasons": reasons, "A": a, "B": b})
    return diffs

def main(path_a, path_b):
    html_a = Path(path_a).read_text(encoding="utf-8")
    html_b = Path(path_b).read_text(encoding="utf-8")
    A = extract_rows(html_a)
    B = extract_rows(html_b)
    diffs = compare_rows(A, B)
    ok = len(diffs) == 0
    print(json.dumps({
        "equal": ok,
        "rows_A": len(A),
        "rows_B": len(B),
        "diff_count": len(diffs),
        "diffs": diffs[:200]  
    }, ensure_ascii=False, indent=2))
    if not ok:
        Path("diffs_full.json").write_text(json.dumps(diffs, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Full detail exported in: diffs_full.json")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_tbody.py test.html test1.html")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])