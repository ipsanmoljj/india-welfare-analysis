#!/usr/bin/env bash
# Final pipeline: nothing is analysed until the data audit passes.
set -euo pipefail
cd "$(dirname "$0")"
python3 code/06a_border_pairs.py        # border pairs + map (needs geopandas)
python3 code/07_nfhs6_rajasthan.py      # extract NFHS-6 Rajasthan PDF -> data/interim
python3 code/00_clean_and_checks.py     # clean + audit; writes audit_status.txt
python3 code/06_insurance_border.py     # refuses to run unless audit PASS
