# FHIRTrustBench: codebook, coded evidence and analysis

This package accompanies the paper *The Interface Is the Risk: FHIRTrustBench and the Trustworthiness of Clinical AI on FHIR* (under review). It contains the instrument, every code assigned to the 16 benchmark subjects with the evidence behind it, the adjudication record, the search records and the scripts that reproduce every number reported in the paper.

## Contents

```
codebook/
  codebook.xlsx            the instrument (v1.1): dimensions, 46 sub-criteria with item rules,
                           rating codes, scoring rule, FHIR-specificity gate, rule clarifications,
                           traceability to sources
  coding_template.xlsx     blank sheet for coding a new system
data/
  studies.csv              the 16 benchmark subjects (S01-S16) with DOIs
  codes_round1_coder1.xlsx first-round codes, coder 1
  codes_round1_coder2.xlsx first-round codes, coder 2
  codes_coder1.xlsx        final-round codes before adjudication, coder 1
  codes_coder2.xlsx        final-round codes before adjudication, coder 2
  codes_final.xlsx         adjudicated codes (46 sub-criteria x 16 studies)
  codes_final.csv          the same, one row per cell
  recode_s01_s08.csv       evidence for the full-text recode of S01 and S08
adjudication/
  adjudication.xlsx        the 162 disputed cells, final codes, reasons, rule changes, evidence log
search/
  queries.md               search strings, dates and counts
  initial_search.xlsx      the 29 candidates of the initial search, with eligibility decisions
  database_screening.xlsx  title/abstract screening of the PubMed and arXiv results
  records_pubmed.csv       retrieved records (without abstracts)
  records_arxiv.csv
scripts/
  agreement.py             inter-coder agreement (weighted kappa, applicability, disagreements)
  compute_results.py       dimension scores, gate, sensitivity analyses, item-level counts
  make_evidence_map.py     the heatmap figure (TikZ) from the computed scores
  requirements.txt
reports/                   outputs of the scripts, as reported in the paper
```

## Codes and scoring

Each sub-criterion is coded M (met), P (partial), X (explicitly not done), NR (not reported) or NA (not applicable). Points: M = 2, P = 1, X = NR = 0; NA is excluded. A dimension score is the share of attainable points over applicable sub-criteria, reported as NA when fewer than three apply. A system passes the FHIR-specificity gate if FS1 and FS3 are at least P and its FHIR-specificity score is at least 50%. Full rules are in `codebook/codebook.xlsx`.

Codes describe what a publication reports, not what a system does.

## Reproducing the results

Requires Python 3.10 or later and `openpyxl`. From this folder:

```
pip install -r scripts/requirements.txt
python scripts/agreement.py data/codes_coder1.xlsx data/codes_coder2.xlsx --a-name "Coder 1" --b-name "Coder 2"
python scripts/compute_results.py
python scripts/make_evidence_map.py > reports/evidence_map.tex
```

`agreement.py` writes `reports/agreement_report.txt` and `reports/disagreements.csv`. Run it on the two `codes_round1_*` files for the first-round figures (`reports/agreement_round1.txt`).

| Reported in the paper | File |
|---|---|
| Inter-coder agreement (final round and first round) | `reports/agreement_report.txt`, `reports/agreement_round1.txt` |
| Dimension scores and gate, per study | `reports/scores_by_study.csv` |
| Dimension summary (Table 1) | `reports/dimension_summary.csv`, `reports/item_distribution.csv` |
| Sensitivity of the gate result | `reports/sensitivity.csv` |
| Adjudication outcomes | `reports/adjudication_outcomes.csv` |
| Search counts | `search/queries.md`, `search/database_screening.xlsx` |

## Notes

- Publication PDFs are not included; studies are identified by DOI in `data/studies.csv`, and every rating is supported by a short verbatim quotation in the adjudication evidence log or the coding sheets.
- Coder identities are anonymised for review.
- AI assistance in coding, adjudication and screening is described in the paper's Generative AI Usage Disclosure; screening decisions in `database_screening.xlsx` record an AI pre-screen and a separate human decision column.

## Licence

Code: MIT. Codebook, data and documentation: CC BY 4.0. See `LICENSE`.
