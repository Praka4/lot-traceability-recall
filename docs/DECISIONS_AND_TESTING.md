# Technical Decisions and Testing

## Problem
This project simulates product traceability and recalls using synthetic data, Python, and SQLite.

## Architecture
- Data generation: src/generate.py
- Recall simulation: src/simulate_recall.py
- Database validation: src/validate.py
- CSV and JSON exports: src/export_recall.py
- Automated tests: tests/test_project.py

## Design Decisions
SQLite makes the project easy to run without a separate database server.
Synthetic data allows repeatable testing without real customer information.
Deliberately planted anomalies test whether validation detects known problems.
CSV and JSON exports support further analysis.

## Verification
The recorded local test run passed all 6 tests.
The synthetic dataset contains one missing input-lot genealogy issue and one excessive-delivery issue.
The recall simulation recorded a 64.15% recovery rate and one missing customer notification.

## Limitations
This is an educational project using synthetic data. Recovery is simulated, and the system is not certified for regulatory compliance.
