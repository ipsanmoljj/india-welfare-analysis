# Welfare analysis of PM Ujjwala Yojana (PMUY) in Rajasthan: evidence from NFHS-4 and NFHS-5

Class project. PMUY (May 2016) gave free LPG connections to poor households:
63.59 lakh in Rajasthan by March 2021, 8 crore nationally by Sept 2019. NFHS-4
(2015-16) was collected just before launch and NFHS-5 (2019-21) after.

**Question:** How much did PMUY move Rajasthan households onto clean cooking fuel,
did Rajasthan lag the rest of India, and is the scheme welfare-improving in
Rajasthan once costs (including the state's Rs 450 refill top-up) are counted?

## Why Rajasthan needs the national data

Within Rajasthan alone (33 districts), the intensity DiD has **no first stage**
(slope 0.06, p = 0.64, F ≈ 0.2). Every district gained about the same, whatever
its baseline. So the design is:

1. **Identification from all-India** (575 districts, state FE): the causal
   slope of LPG uptake on PMUY exposure (`code/02_pmuy_did.py`).
2. **Rajasthan vs comparable districts** (`code/05_rajasthan_gap.py`): did
   Rajasthan districts gain less than districts elsewhere with the same baseline
   exposure, electricity, sanitation, water and schooling?
3. **Rajasthan welfare calibration** (`code/04_cba.py Rajasthan`): conversion
   rate and CBA/MVPF using Rajasthan connections, households and the state top-up.

## Results

| | Estimate | Inference |
|---|---|---|
| All-India first stage (Δ clean fuel per 1 pp exposure) | 0.16 | p = 0.003 |
| All-India quadratic: peak effect at ~67% baseline non-use | 0.67 / −0.50 | p < 0.001 |
| Within-Rajasthan first stage | 0.06 | p = 0.64 (not identified) |
| Rajasthan mean Δ clean fuel vs rest of India | +9.5 vs +16.4 pp | |
| **Rajasthan gap vs comparable districts** | **−8.2 pp** | cluster p < 0.001; permutation: 2nd worst of 24 states, p = 0.25 |
| Health 2SLS (child ARI, stunting, underweight, anaemia; women anaemia) | null | all p > 0.3 |
| Placebo (institutional births) | null | p = 0.21 |

**Rajasthan welfare:**
- **Conversion:** 7–26% of Rajasthan's PMUY connections became households using
  clean fuel as main fuel. That's Rs 6,100–21,800 of connection subsidy per
  effective switcher (the national figure is ~37%).
- **Per beneficiary household (10 yrs, 8%):** social NPV ≈ Rs 21,700 and MVPF ≈ 2.8
  with the state top-up, under the base assumptions (time valued at 50% of the
  wage, 3.95 refills/yr, health = 0). At 25% of the wage, NPV is negative.
- The Rs 450 refill scheme (Jan 2024) comes **after** NFHS-5, so this study cannot
  evaluate it. It enters only the government-cost side of the CBA.

## Run

```bash
pip install pandas statsmodels linearmodels matplotlib
python code/01_build_panel.py
python code/02_pmuy_did.py              # all-India -> output/all_india/
python code/02_pmuy_did.py Rajasthan    # within-state check -> output/rajasthan/
python code/05_rajasthan_gap.py         # Rajasthan vs comparable districts
python code/04_cba.py                   # all-India CBA
python code/04_cba.py Rajasthan         # Rajasthan CBA
```

`code/03_bihar_prohibition.py` is the abandoned alternative topic (state-level
null result), kept for reference.

## Data (`data/raw/`)

- `nfhs_districts_641_kalla.csv`: NFHS-4 and NFHS-5 district factsheets, 641
  districts ([SaiSiddhardhaKalla/NFHS](https://github.com/SaiSiddhardhaKalla/NFHS)).
  Values cross-checked against the pratapvardhan file.
- `nfhs5_districts_with_nfhs4.csv`, `nfhs5_states_with_nfhs4.csv`: [pratapvardhan/NFHS-5](https://github.com/pratapvardhan/NFHS-5)
- `nfhs4_states_ht.csv`: [HindustanTimesLabs/nfhs-data](https://github.com/HindustanTimesLabs/nfhs-data)

## CBA parameters to verify before submission (`code/04_cba.py`)

| Parameter | Value | Source | Status |
|---|---|---|---|
| Connection assistance | Rs 1,600 | pmuy.gov.in | verified |
| Refills / beneficiary / yr | 3.95 (FY24) | Rajya Sabha reply, Feb 2025 | verified |
| Refill subsidy | Rs 300 | MoPNG, Oct 2023 | check |
| Rajasthan PMUY connections | 63.59 lakh (31.03.2021) | Lok Sabha AU1844 | verified |
| Rajasthan households | 1.45 crore | **assumption** (Census 2011 ≈ 1.26 cr, grown) | replace |
| Rajasthan refill price to PMUY | Rs 450 from Jan 2024 | CM announcement, Dec 2023 | check |
| LPG unsubsidised price | Rs 850 | IOCL Delhi price | check |
| Firewood collection hours | 660 / household / yr | Practical Action (2015) | check original |
| Rural female wage | Rs 300/day | **assumption**; replace with PLFS / Labour Bureau | replace |
| Stove cost | Rs 1,000 | **assumption** | replace |
| Full-LPG refills / yr | 7 | **assumption** | replace |

## Limitations

- Exposure correlates with poverty. State FE, baseline controls and the placebo
  help but don't fully rule out differential trends. With only two rounds there
  is no pre-trend test.
- The first stage is borderline weak for 2SLS (clustered F ≈ 9), and is
  not identified within Rajasthan alone.
- The Rajasthan gap is conditional on observables. Part of it may come from
  non-PMUY factors (e.g. firewood availability in desert districts), so the
  conversion lower bound attributes all of it to PMUY, which is an extreme case.
- The level effect behind the conversion rate needs the "zero exposure → zero
  effect" assumption.
- Factsheet data is district averages. Household-level NFHS microdata (DHS
  registration) would allow a stronger design.
