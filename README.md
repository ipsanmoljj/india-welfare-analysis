# Welfare analysis of Indian policy using NFHS-4 vs NFHS-5

Class project. Two candidate designs, both built on public NFHS factsheet data
(no microdata registration needed).

| | PMUY (Ujjwala, May 2016) | Bihar prohibition (April 2016) |
|---|---|---|
| Unit | District (262 matched districts, 20 states) | State (33 after dropping prohibition states) |
| Design | Intensity DiD: exposure = % not using clean fuel in NFHS-4 | Single-treated-unit DiD, permutation inference |
| Outcomes | Clean cooking fuel, child ARI, stunting, anaemia | Spousal violence (same definition both rounds) |
| Script | `code/02_pmuy_did.py` | `code/03_bihar_prohibition.py` |

## Run

```bash
pip install pandas statsmodels
python code/01_build_panel.py
python code/02_pmuy_did.py
python code/03_bihar_prohibition.py
```

## First results (unreviewed)

**PMUY:** First stage is strong. Each extra 1 pp of baseline non-clean-fuel use
goes with a 0.18 pp larger increase in clean-fuel use (SE 0.06, clustered by state).
Health reduced forms are mostly null. The stunting result is significant, but its
implied size (−0.37 pp stunting per +1 pp clean fuel) is too big to believe, which
points to mean reversion or catch-up rather than a PMUY effect. Treat it as a
threat to validity, not a finding.

**Bihar:** Spousal violence fell 3.7 pp in Bihar and 3.6 pp in the control states.
DiD ≈ −0.1 pp, permutation p = 1.0, so no detectable effect at state level.

## Data (`data/raw/`)

- `nfhs5_districts_with_nfhs4.csv`, `nfhs5_states_with_nfhs4.csv`: from
  [pratapvardhan/NFHS-5](https://github.com/pratapvardhan/NFHS-5) (IIPS factsheets)
- `nfhs4_states_ht.csv`: from [HindustanTimesLabs/nfhs-data](https://github.com/HindustanTimesLabs/nfhs-data)

## Known limitations

- The district file covers only 341 districts, and only 262 of them have NFHS-4
  values. For full coverage use the data.gov.in NFHS-5 district factsheets.
- The welfare/CBA side (PMUY subsidy cost, Bihar excise revenue loss) is not built
  yet. It needs PPAC / RBI State Finances data.
- Alcohol use is not comparable across rounds (NFHS-4: men 15-49; NFHS-5: men 15+).
