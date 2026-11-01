"""FHIRTrustBench inter-coder agreement.

Usage:
    python agreement.py coderA.xlsx coderB.xlsx [--a-name "Coder 1" --b-name "Coder 2"]

Both files must use the blank evidence-map layout (sheet "Evidence map":
sub-criterion IDs in column A from row 5, study IDs in the header row 4
from column D, one code per cell: M, P, X, NR or NA).

Outputs (printed and written to reports/ in the artifact root):
  agreement_report.txt   summary statistics
  disagreements.csv      every cell where the two coders differ, for adjudication
"""
import argparse, csv, os, sys
from collections import Counter
from openpyxl import load_workbook

CODES = {"M", "P", "X", "NR", "NA"}
POINTS = {"M": 2, "P": 1, "X": 0, "NR": 0}
DIMS = ["FS", "AV", "WI", "TE", "GR"]


def read_map(path):
    ws = load_workbook(path, data_only=True)["Evidence map"]
    studies = {}
    col = 4
    while ws.cell(4, col).value:
        studies[col] = str(ws.cell(4, col).value).split("\n")[0].strip()
        col += 1
    cells, problems = {}, []
    row = 5
    while ws.cell(row, 1).value:
        item, dim = str(ws.cell(row, 1).value).strip(), str(ws.cell(row, 2).value).strip()
        for c, sid in studies.items():
            v = ws.cell(row, c).value
            v = "" if v is None else str(v).strip().upper()
            if v not in CODES:
                problems.append(f"{sid}/{item}: '{v}'")
            else:
                cells[(sid, item)] = (dim, v)
        row += 1
    return cells, problems


def cohen_kappa(pairs, cats, weight=None):
    """weight: None (unweighted), 'linear' or 'quadratic'. pairs: list of (a, b)."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    k = len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    obs = [[0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    ra = [sum(r) for r in obs]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i, j):
        if weight is None:
            return 0.0 if i == j else 1.0
        d = abs(i - j) / (k - 1)
        return d if weight == "linear" else d * d

    po = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w(i, j) * ra[i] * cb[j] for i in range(k) for j in range(k)) / n ** 2
    return 1.0 if pe == 0 else 1 - po / pe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--a-name", default="A"); ap.add_argument("--b-name", default="B")
    args = ap.parse_args()
    A, pa = read_map(args.a)
    B, pb = read_map(args.b)
    if pa or pb:
        print("Fix these cells before computing agreement:")
        for p in pa: print(f"  {args.a_name}: {p}")
        for p in pb: print(f"  {args.b_name}: {p}")
        sys.exit(1)
    keys = sorted(set(A) & set(B))
    only = set(A) ^ set(B)
    out = []
    say = out.append
    say(f"FHIRTrustBench agreement: {args.a_name} vs {args.b_name}")
    say(f"Cells compared: {len(keys)} ({len({k[0] for k in keys})} studies x {len({k[1] for k in keys})} items)")
    if only:
        say(f"WARNING: {len(only)} cells present in only one file (different studies/items); ignored.")

    # 1. Exact agreement on the five codes
    exact = sum(A[k][1] == B[k][1] for k in keys) / len(keys)
    say(f"\n1. Exact agreement on all five codes: {exact:.1%}")
    say(f"   Unweighted kappa (5 codes): {cohen_kappa([(A[k][1], B[k][1]) for k in keys], ['M','P','X','NR','NA']):.2f}")

    # 2. Applicability (NA vs applicable)
    app = [("NA" if A[k][1] == "NA" else "AP", "NA" if B[k][1] == "NA" else "AP") for k in keys]
    say(f"\n2. Applicability agreement (NA vs applicable): {sum(x == y for x, y in app)/len(app):.1%}, "
        f"kappa {cohen_kappa(app, ['AP','NA']):.2f}")

    # 3. Points scale on cells both found applicable
    both = [k for k in keys if A[k][1] != "NA" and B[k][1] != "NA"]
    say(f"\n3. Points scale (M=2, P=1, X/NR=0) on {len(both)} cells both coders rated applicable")
    say(f"   {'':6}{'n':>5}{'raw agree':>11}{'quad. kappa':>13}{'linear kappa':>14}")

    def row(label, ks):
        pr = [(POINTS[A[k][1]], POINTS[B[k][1]]) for k in ks]
        if not pr:
            return
        raw = sum(x == y for x, y in pr) / len(pr)
        say(f"   {label:6}{len(pr):>5}{raw:>11.1%}{cohen_kappa(pr,[0,1,2],'quadratic'):>13.2f}"
            f"{cohen_kappa(pr,[0,1,2],'linear'):>14.2f}")
    row("ALL", both)
    for d in DIMS:
        row(d, [k for k in both if A[k][0] == d])

    # 4. X vs NR splits
    zero = [k for k in both if A[k][1] in ("X", "NR") and B[k][1] in ("X", "NR")]
    split = [k for k in zero if A[k][1] != B[k][1]]
    say(f"\n4. Cells both scored 0: {len(zero)}; split X vs NR: {len(split)} "
        f"({(len(split)/len(zero) if zero else 0):.1%}). Same score, reported separately.")

    # 5. Size of disagreements
    dist = Counter(abs(POINTS[A[k][1]] - POINTS[B[k][1]]) for k in both)
    say(f"\n5. Disagreement size on points scale: exact {dist[0]}, one step {dist[1]}, two steps (M vs 0) {dist[2]}")

    # 6. Code cross-tab
    cats = ["M", "P", "X", "NR", "NA"]
    tab = Counter((A[k][1], B[k][1]) for k in keys)
    say(f"\n6. Cross-tab (rows {args.a_name}, columns {args.b_name})")
    say("        " + "".join(f"{c:>6}" for c in cats))
    for a in cats:
        say(f"   {a:>4} " + "".join(f"{tab[(a,b)]:>6}" for b in cats))

    # 7. Items with most disagreement
    per_item = Counter(k[1] for k in keys if A[k][1] != B[k][1])
    say("\n7. Items with most disagreements (candidates for rule clarification):")
    for item, n in per_item.most_common(8):
        say(f"   {item}: {n} of {len({k[0] for k in keys})} studies")

    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(here, exist_ok=True)
    with open(os.path.join(here, "agreement_report.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(here, "disagreements.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["study", "item", "dimension", args.a_name, args.b_name, "points_gap", "final_code", "reason"])
        for k in keys:
            if A[k][1] != B[k][1]:
                gap = "" if "NA" in (A[k][1], B[k][1]) else abs(POINTS[A[k][1]] - POINTS[B[k][1]])
                w.writerow([k[0], k[1], A[k][0], A[k][1], B[k][1], gap, "", ""])
    print("\n".join(out))
    print("\nWrote reports/agreement_report.txt and reports/disagreements.csv")


if __name__ == "__main__":
    main()
