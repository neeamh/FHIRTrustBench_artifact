# Search queries

## Initial targeted search (11 October 2026)
Seeded with the 39 studies included in Balch et al. (2023), JMIR Medical Informatics 11:e48297, and extended with the web searches listed in `initial_search.xlsx` (sheet "Search log"). 29 candidates were assessed against IC1-IC6; 16 were included.

## Database search (2026-10-31)

PubMed (E-utilities), 179 records:

    (FHIR[tiab] OR "Fast Healthcare Interoperability Resources"[tiab] OR "SMART on FHIR"[tiab] OR "CDS Hooks"[tiab]) AND ("machine learning"[tiab] OR "deep learning"[tiab] OR "artificial intelligence"[tiab] OR "language model"[tiab] OR "neural network"[tiab] OR prediction[tiab]) AND 2016:2026[dp]

arXiv (API), 47 records:

    abs:FHIR AND (abs:"language model" OR abs:"machine learning" OR abs:agent OR abs:"deep learning" OR abs:"artificial intelligence" OR abs:LLM)

After removing duplicates by title: 222 records. Title and abstract screening against IC1-IC6 is recorded in `database_screening.xlsx`. Record lists (without abstracts) are in `records_pubmed.csv` and `records_arxiv.csv`.
