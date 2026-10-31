# Project rules

1. **No analysis without data cleaning.** Every analysis reads only from `data/clean/`
   after `code/00_clean_and_checks.py` has run and `output/checks/audit_status.txt`
   says `PASS`. New data (new survey round, new state, new indicator) goes through
   00 first, with its own checks added to the audit, before any regression, table or figure.
2. **The cleaned results are final.** The numbers in `output/insurance/` produced by
   `./run_all.sh` are the study's results. Don't report numbers from raw data or
   from the appendix scripts as findings.
3. **Cleaning protocol (fixed):** no imputation; 0 = missing code; drop districts and
   states whose boundaries changed between rounds; OOP in real 2019-21 rupees (CPI-C),
   capped at Q3 + 1.5·IQR per round over all comparable districts; z-scores use the
   NFHS-4 neighbour-border mean and SD, applied to both rounds and sides.
4. Run everything with `./run_all.sh`.
