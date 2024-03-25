# SOEN 6491 - Team ALPHA Data Collection

This repository contains python scripts that scrape and collect refactoring data from GitHub Java projects (through their url) into an output SQLite database.

## Runnable Files

- `extract_data.py` Clones a requested repository and extracts the required data using RefactoringMiner, Organic and the git cli.
- `get_duplicates.py` Adds code clone data to an existing database (ie should be run after extract_data)
- `fix_smell.spy` Some smells and metrics were extracted based on incorrect files in the initial script. This script makes sure all commits were analyzed by Organic and are correctly imported into the database.

## References

- RefactoringMiner.jar was built from the code in [this](https://github.com/thanhpd/refactoringminertest) repository.
- organic-v0.1.1-OPT.jar was built from the code in [this](https://github.com/plsakr/organic-standalone) repository.
- PMD was downloaded from [their official website](https://pmd.github.io/)