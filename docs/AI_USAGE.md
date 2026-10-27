# AI Usage and Prompt History

## 1. Purpose

This document explains how AI assistance was used while developing the Lot Traceability and Product Recall System.

AI was used as a development assistant. The project was run and checked locally using Python, SQLite, PowerShell, and pytest.

## 2. Prompt History

The entries below summarize the main development requests from the working conversation. They are representative summaries, not a verbatim export of every prompt.

### Prompt 1: Build the project

Request: Help build a synthetic lot traceability and product recall project with Python, SQLite, generated data, and recall simulation.

AI assistance:
- Suggested implementation steps and project structure.
- Helped develop and troubleshoot scripts.
- Explained the purpose of traceability and recall metrics.

### Prompt 2: Debug recall exports

Request: Fix the recall export workflow so it accepts database and output paths and exports RecallScope and RecallAction data to CSV and JSON.

AI assistance:
- Helped update the export script.
- Suggested commands to run the script and inspect the exported files.

### Prompt 3: Validate the database

Request: Check database integrity and identify business-rule violations.

AI assistance:
- Helped inspect validation output.
- Explained foreign-key checks, primary-key uniqueness, genealogy gaps, excessive deliveries, and recalled inventory.
- Helped distinguish deliberately planted test cases from unexpected failures.

### Prompt 4: Verify recall metrics

Request: Check whether the recall simulation metrics and notification actions were consistent.

AI assistance:
- Helped verify affected customers, deliveries, delivered units, simulated recovery, quarantine, and missing notifications.
- Explained the recovery-rate calculation and the intentionally missing notification for CUST-00200.

### Prompt 5: Prepare and publish the project

Request: Help prepare the README, exclude generated output from Git, and publish the project to GitHub.

AI assistance:
- Suggested documentation and Git commands.
- Helped create a .gitignore file.
- Guided the commit and push workflow.

## 3. Where AI Helped

AI accelerated development by:
- Suggesting implementation and debugging steps.
- Explaining unfamiliar Python, SQL, Git, and validation concepts.
- Helping interpret command output.
- Drafting project documentation and run instructions.

## 4. What I Personally Ran and Reviewed

The following actions were performed locally during development:

- Ran the synthetic data-generation workflow.
- Ran the recall simulation.
- Executed the automated test suite.
- Inspected recall exports and database records.
- Ran database validation.
- Compared JSON and CSV recall metrics.
- Initialized Git and pushed the project to GitHub.

Recorded verification results:
- pytest: 6 tests passed.
- Foreign-key violations: 0.
- Duplicate primary keys: none reported.
- Date-order violations: 0.
- Consumption exceeding received quantity: 0.
- Excessive delivery business-rule violation: 1 deliberately planted case.
- Missing input-lot genealogy: 1 deliberately planted case.
- Available recalled inventory: 0.
- Missing customer notification: 1, for CUST-00200.
- Simulated recovery rate: 64.15%.

These results describe the local synthetic dataset and test run, not a production deployment.

## 5. Human Review and Limitations

AI suggestions were not treated as proof that the project worked. Commands and outputs were checked locally.

The six passing tests demonstrate that the existing test suite passed; they do not prove that every business rule is correct or that the application is production-ready.

The dataset is synthetic. Recovery is simulated, and the project is not a certified regulatory-compliance system.

Before final submission, the implementation and important claims should be reviewed against the source code and repeatable test results.

## 6. Transparency Note

This file is a summary of the main AI-assisted development activities. It must not be interpreted as a complete verbatim transcript of every prompt or response.

For an evaluation requiring the complete prompt history, include the original relevant prompts and responses from the development conversation as supplementary evidence.
