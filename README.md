# Lot Traceability & Product Recall Simulator

A reproducible synthetic supply-chain dataset and product recall simulator built with Python and SQLite.

## Features

- Deterministic synthetic data generated from a fixed seed.
- Supplier, material lot, product, BOM, production, inventory, shipment and customer records.
- Forward traceability from a recalled raw material lot to affected finished lots, deliveries and customers.
- Recall actions for customer notification, inventory quarantine, recovery and disposition.
- Four labelled exception scenarios, including missing genealogy and delivery over production.
- Separate ground-truth labels for evaluating anomaly detection.
- SQLite database, CSV/JSON exports, validation reports and reproducibility checks.
- Automated tests using pytest.

## Requirements

- Python 3.10 or newer
- pip
- pytest for running tests

## Installation

Clone the repository and enter its directory:

```powershell
git clone https://github.com/Praka4/lot-traceability-recall.git
cd lot-traceability-recall
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual environment activation, you can run the Python commands using `.venv\Scripts\python.exe` instead.

## Run the project

Run these commands from the repository root, in order:

```powershell
python src\generate.py --out output --seed 20261022 --scale starter
python src\simulate_recall.py --db output\traceability.db --out output
python src\validate.py --db output\traceability.db --out output
python src\export_recall.py --db output\traceability.db --out output
python -m pytest -q
```

To generate the larger dataset, replace `starter` with `full` and use a separate output directory such as `output_full` for every command.

## Verification

The test suite should report six passing tests:

```text
6 passed
```

The full dataset's validation previously reported:

- Foreign-key violations: 0
- Duplicate primary keys: none
- Date-order violations: 0
- Consumption exceeding received quantity: 0
- Planted missing-input-lot issue: 1
- Planted delivery-over-production issue: 1
- Available recalled inventory after simulation: 0

The two business-rule issues are deliberate test cases, not unexpected database-integrity failures. The recall simulation quarantines affected inventory; therefore, an inventory issue planted in the input data may no longer be present in the final simulated state.

Results can vary by dataset scale. Inspect the generated validation report and ground-truth files to confirm the actual results for your run.

## Output files

The output directory contains the SQLite database and generated reports/exports, including CSV and JSON data. Exact files depend on the scripts and selected output directory.

Ground-truth labels are separate from operational records. Do not use them as input features when evaluating an anomaly-detection model.

## Domain assumptions

- Quantities are measured in units unless a field says otherwise.
- A production order can consume multiple material lots.
- Material consumption connects production orders and material lots.
- Finished lots can be split across shipments.
- Recall scope is derived by traversing traceability relationships, rather than being assigned randomly.
- Synthetic anomalies are deliberately planted and documented in ground truth.
- Recovery quantities are simulated; they do not represent real-world physical recovery.

## Documentation

- `docs/architecture.md` — system design and data flow.
- `docs/data_dictionary.md` — fields and data definitions.
- `docs/AI_USAGE.md` — AI assistance and review summary.
- `docs/DECISIONS_AND_TESTING.md` — technical decisions, testing and limitations.

The AI usage document is a summary, not a complete verbatim prompt transcript. Any submission requiring prompt history should include the actual relevant prompts and responses as supplementary evidence.

## Limitations and future improvements

- All records are synthetic; this is a simulator, not a production recall platform.
- Recall and recovery results depend on the generated data and implemented rules.
- Further improvements could include richer anomaly scenarios, more extensive tests, and automated CI.

## Data provenance

All generated records are synthetic. No real customer or confidential supply-chain data is included.
