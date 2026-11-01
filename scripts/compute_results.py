"""FHIRTrustBench results: scores, gate, sensitivity and adjudication summary.

Usage (from the artifact root):
    python scripts/compute_results.py

Reads   data/codes_final.xlsx         (locked final codes)
        data/codes_coder1.xlsx        (coder 1, pre-adjudication)
        data/codes_coder2.xlsx        (coder 2, pre-adjudication)
        adjudication/adjudication.xlsx (adjudication decisions)
Writes  reports/*.csv and reports/results_summary.txt

Scoring rules (codebook): M=2, P=1, X=0, NR=0, NA excluded from the denominator.
Dimension score = points / (2 x applicable items); NA if fewer than 3 items apply.
FHIR-specificity gate: FS1 >= P and FS3 >= P and FS score >= 50%.
"""
import csv, os, statistics, sys
from collections import Counter
from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from agreement import read_map  # same reader the kappa script uses

POINTS = {"M": 2, "P": 1, "X": 0, "NR": 0}
DIMS = ["FS", "AV", "WI", "TE", "GR"]
GATE_THRESHOLD = 0.50
MIN_APPLICABLE = 3


def load(name):
    cells, problems = read_map(os.path.join(ROOT, "data", name))
    if problems:
        sys.exit(f"{name}: invalid or blank cells: {problems[:10]}")
    grid, dim_of = {}, {}
    for (sid, item), (dim, code) in cells.items():
        grid.setdefault(sid, {})[item] = code
        dim_of[item] = dim
    return grid, dim_of


def dim_score(row, dim_of, dim, na_as_nr=False):
    codes = [c for i, c in row.items() if dim_of[i] == dim]
    if na_as_nr:
        codes = ["NR" if c == "NA" else c for c in codes]
    app = [c for c in codes if c != "NA"]
    if len(app) < MIN_APPLICABLE:
        return None
    return sum(POINTS[c] for c in app) / (2 * len(app))


def gate(row, dim_of, threshold=GATE_THRESHOLD, na_as_nr=False):
    fs = dim_score(row, dim_of, "FS", na_as_nr)
    return (row["FS1"] in ("M", "P") and row["FS3"] in ("M", "P")
            and fs is not None and fs >= threshold)


def pct(x):
    return "NA" if x is None else f"{x:.0%}"


def write_csv(name, header, rows):
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    final, dim_of = load("codes_final.xlsx")
    c1, _ = load("codes_coder1.xlsx")
    c2, _ = load("codes_coder2.xlsx")
    studies = sorted(final)
    items = sorted(dim_of, key=lambda i: (DIMS.index(dim_of[i]), int("".join(filter(str.isdigit, i)) or 0), i))
    out = []
    say = out.append

    # Long-format final codes
    write_csv("final_codes_long.csv", ["study", "item", "dimension", "code", "points"],
              [[s, i, dim_of[i], final[s][i], POINTS.get(final[s][i], "")] for s in studies for i in items])

    # Scores and gate per study
    rows = []
    for s in studies:
        sc = {d: dim_score(final[s], dim_of, d) for d in DIMS}
        rows.append([s] + [("" if sc[d] is None else round(sc[d], 4)) for d in DIMS]
                    + [final[s]["FS1"], final[s]["FS3"], "PASS" if gate(final[s], dim_of) else "fail"])
    write_csv("scores_by_study.csv", ["study"] + DIMS + ["FS1", "FS3", "gate"], rows)

    say("FHIRTrustBench results (locked final codes)")
    say(f"{len(studies)} studies x {len(items)} sub-criteria = {len(studies)*len(items)} cells\n")
    say("1. Dimension scores by study")
    say("   study " + "".join(f"{d:>6}" for d in DIMS) + "   FS1  FS3  gate")
    for r in rows:
        s = r[0]
        sc = [dim_score(final[s], dim_of, d) for d in DIMS]
        say(f"   {s:5} " + "".join(f"{pct(x):>6}" for x in sc) + f"   {r[6]:>3}  {r[7]:>3}  {r[8]}")

    # Dimension summary
    summ = []
    say("\n2. Dimension summary (studies with a defined score)")
    for d in DIMS:
        v = [dim_score(final[s], dim_of, d) for s in studies]
        v = [x for x in v if x is not None]
        summ.append([d, len(v), round(statistics.median(v), 4), round(min(v), 4), round(max(v), 4),
                     round(statistics.mean(v), 4)])
        say(f"   {d}: n={len(v):2}  median {pct(statistics.median(v))}  range {pct(min(v))}-{pct(max(v))}  mean {pct(statistics.mean(v))}")
    write_csv("dimension_summary.csv", ["dimension", "n_scored", "median", "min", "max", "mean"], summ)

    # Gate
    passing = [s for s in studies if gate(final[s], dim_of)]
    fs13 = [s for s in studies if final[s]["FS1"] in ("M", "P") and final[s]["FS3"] in ("M", "P")]
    say(f"\n3. FHIR-specificity gate (FS1>=P, FS3>=P, FS>={GATE_THRESHOLD:.0%})")
    say(f"   Pass: {len(passing)}/{len(studies)} {passing}")
    say(f"   Meet FS1 and FS3 conditions: {len(fs13)}/{len(studies)} {fs13}")
    say(f"   Studies with FS >= 50%: {[s for s in studies if dim_score(final[s], dim_of, 'FS') >= .5]}")

    # Sensitivity
    sens = []
    def add(label, grid, thr=GATE_THRESHOLD, na_as_nr=False):
        p = [s for s in sorted(grid) if gate(grid[s], dim_of, thr, na_as_nr)]
        fsm = statistics.median([dim_score(grid[s], dim_of, "FS", na_as_nr) for s in grid])
        sens.append([label, len(p), ";".join(p), round(fsm, 4)])
    for thr in (0.50, 0.45, 0.40, 0.35, 0.30):
        add(f"final codes, gate threshold {thr:.0%}", final, thr)
    add("final codes, NA scored as NR", final, na_as_nr=True)
    add("coder 1 codes only, 50%", c1)
    add("coder 2 codes only, 50%", c2)
    write_csv("sensitivity.csv", ["scenario", "n_pass", "passing_studies", "median_FS"], sens)
    say("\n4. Sensitivity of the gate result")
    for r in sens:
        say(f"   {r[0]:42} pass {r[1]:2}/{len(studies)}  {r[2] or '-':18} median FS {r[3]:.0%}")

    # Item distribution
    dist = []
    for i in items:
        c = Counter(final[s][i] for s in studies)
        dist.append([i, dim_of[i]] + [c[k] for k in ("M", "P", "X", "NR", "NA")])
    write_csv("item_distribution.csv", ["item", "dimension", "M", "P", "X", "NR", "NA"], dist)
    none = [r[0] for r in dist if r[2] == 0 and r[3] == 0]
    nom = [r[0] for r in dist if r[2] == 0]
    say("\n5. Item-level findings")
    say(f"   Items no study receives any credit on (no M or P): {none}")
    say(f"   Items no study fully meets (no M): {len(nom)} of {len(items)}")
    for it in ("FS2", "FS10", "GR2"):
        c = Counter(final[s][it] for s in studies)
        say(f"   {it}: " + ", ".join(f"{k} {c[k]}" for k in ("M", "P", "X", "NR", "NA") if c[k]))

    # Adjudication summary
    ws = load_workbook(os.path.join(ROOT, "adjudication", "adjudication.xlsx"), data_only=True)["Disagreements"]
    hdr = [c.value for c in ws[1]]
    ix = {h: hdr.index(h) for h in ("Item", "Study", "Coder 1", "Coder 2", "Final", "Reason")}
    adj = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    mismatch = [(r[ix["Study"]], r[ix["Item"]]) for r in adj
                if c1[r[ix["Study"]]][r[ix["Item"]]] != r[ix["Coder 1"]]
                or c2[r[ix["Study"]]][r[ix["Item"]]] != r[ix["Coder 2"]]
                or final[r[ix["Study"]]][r[ix["Item"]]] != r[ix["Final"]]]
    outcome = Counter("coder 1" if r[ix["Final"]] == r[ix["Coder 1"]] else
                      "coder 2" if r[ix["Final"]] == r[ix["Coder 2"]] else "third code" for r in adj)
    by_dim = Counter(dim_of[r[ix["Item"]]] for r in adj)
    n_disagree = sum(c1[s][i] != c2[s][i] for s in studies for i in items)
    say("\n6. Adjudication")
    say(f"   Disagreeing cells between coders: {n_disagree}; rows in adjudication workbook: {len(adj)}")
    say(f"   Final code matched coder 1: {outcome['coder 1']}, coder 2: {outcome['coder 2']}, neither: {outcome['third code']}")
    say("   Disputes by dimension: " + ", ".join(f"{d} {by_dim[d]}" for d in DIMS))
    say(f"   Consistency check (workbook vs coder files vs final grid): "
        f"{'OK' if not mismatch else 'MISMATCH ' + str(mismatch[:10])}")
    say(f"   Rows with blank reason: {sum(1 for r in adj if not r[ix['Reason']])}")
    write_csv("adjudication_outcomes.csv", ["study", "item", "dimension", "coder1", "coder2", "final", "outcome", "reason"],
              [[r[ix["Study"]], r[ix["Item"]], dim_of[r[ix["Item"]]], r[ix["Coder 1"]], r[ix["Coder 2"]], r[ix["Final"]],
                "coder 1" if r[ix["Final"]] == r[ix["Coder 1"]] else "coder 2" if r[ix["Final"]] == r[ix["Coder 2"]] else "third code",
                r[ix["Reason"]]] for r in adj])

    with open(os.path.join(ROOT, "reports", "results_summary.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
