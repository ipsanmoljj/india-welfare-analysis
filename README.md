# Rajasthan's state health insurance (BSBY) and welfare: a border-district DiD

**Main study.** Rajasthan launched the Bhamashah Swasthya Bima Yojana (BSBY) on
13 Dec 2015 (merged into AB-MGRSBY with Ayushman Bharat in 2019). Neighbouring
states had RSBY and then PM-JAY. We compare Rajasthan's border districts with the
districts directly across the state line, NFHS-4 (2015-16) → NFHS-5 (2019-21),
following Dube, Lester & Reich (2010).

![Border sample](output/insurance/fig_border_map.png)

Full walkthrough (data, sample construction, why districts look partial on the
map, specification, inference, limitations): [`docs/methodology.md`](docs/methodology.md).
References: [`docs/literature.md`](docs/literature.md).

## Design

- **Sample:** 51 contiguous Rajasthan–neighbour district pairs from the Census
  2011 map (`code/06a_border_pairs.py`). 23 Rajasthan and 26 neighbour districts;
  every pair shares ≥ 7 km of border. 40 pairs are used: 5 neighbour districts
  split after NFHS-4 (Panchmahal, Sabarkantha, Bhiwani, Shajapur, Firozpur) have
  no comparable NFHS-4 value.
- **Specification:** ΔY_ip = β·Rajasthan_i + pair FE, i.e. a within-pair DiD.
  SEs are two-way clustered by Rajasthan district and neighbour district.
- **Pre-trend:** three-round state event study (NFHS-3 → 4 → 5) with Karan et
  al. (2017) notation: φ2 = pre-period DiD, φ3 = post-period DiD. Permutation
  inference across states (Abadie et al. 2010).
- **Baseline caveat:** Rajasthan's NFHS-4 fieldwork ran 23 Jan – 21 Jul 2016,
  after launch. Early enrolment inflates the baseline, so β is a lower bound.

## Data cleaning and checks (`code/00_clean_and_checks.py`)

All checks pass (full log: [`output/checks/data_audit.md`](output/checks/data_audit.md)):

- **Missing values:** no imputation. 0 = suppressed/not-comparable code → missing.
  The 5 neighbour districts split after NFHS-4 are excluded. Among comparable
  districts, OOP is missing for 0/23 Rajasthan and 0/21 neighbours.
- **Cross-source agreement:** 100% exact on every outcome and round against
  the pratapvardhan file, and 33/33 against the NFHS-5 column in the NFHS-6
  compendium.
- **Ranges and logic:** 0 violations.
- **Small-sample flags (25–49 cases):** stripped in the main file. They are
  recoverable only for Gujarat, where none of the border districts are flagged.
- **Outliers:** OOP converted to real 2019-21 rupees (CPI-C), then capped at
  Q3 + 1.5·IQR (fences per round over all comparable districts: Rs 9,109 / Rs 7,943).
  **No border district reaches the fence**, so capping doesn't change the estimates.
- **Standardisation:** z-scores using the NFHS-4 neighbour-border mean and SD,
  applied to both rounds and both sides.
- **Baseline balance:** Rajasthan border districts started with higher OOP
  (+Rs 594, p = 0.09), more public-facility births (+6.8 pp, p = 0.03) and lower
  electricity (−3.8 pp, p = 0.02). Hence the baseline-control column below.

## Results (`code/06_insurance_border.py`, cleaned data, 40 pairs)

| Outcome | β (SE) | p | β in SD | Controlling for NFHS-4 level | Leave-one-Rajasthan-district-out range |
|---|---|---|---|---|---|
| **Insurance coverage (pp)** | **+52.8 (5.1)** | <0.001 | 7.3 | +55.1 (4.2) | +51.3 to +53.9 |
| OOP per delivery (real Rs) | −356 (840) | 0.67 | −0.44 | **+227 (212)** | −478 to +30 |
| log OOP | −0.08 (0.31) | 0.80 | −0.17 | +0.09 (0.12) | −0.14 to +0.05 |
| Institutional births (pp) | −1.2 (2.3) | 0.62 | −0.09 | +0.8 (1.3) | −1.6 to −0.6 |
| Public-facility births (pp) | +2.4 (5.4) | 0.66 | 0.12 | +5.5 (3.9) | +1.3 to +4.2 |
| *Placebo:* electricity (pp) | +3.2 (3.5) | 0.35 | 0.56 | −0.1 (0.6) | +2.0 to +3.9 |
| *Placebo:* women 10+ yrs school (pp) | +3.1 (1.7) | 0.08 | 0.24 | +2.8 (1.5) | +2.5 to +3.7 |

Capped OOP and the drop-small-sample column are identical to the main estimates
(nothing binds). Sample robustness (drop Gujarat, MP only, pairs ≥10 km):
insurance +45 to +52, all p < 0.001; nothing else significant
([`output/insurance/border_pair_did.csv`](output/insurance/border_pair_did.csv)).

**OOP power:** 95% CI −Rs 2,003 to +Rs 1,291, against a Rajasthan baseline of
Rs 2,235. The minimum detectable effect (Rs 2,352) exceeds the baseline, so the
design cannot detect even a complete elimination of delivery OOP. Once the
NFHS-4 level is controlled for, the point estimate turns positive. The earlier
negative sign was mean reversion from Rajasthan's higher starting OOP.

**State event study** (insurance coverage): Rajasthan 4.5% → 18.7% → **87.8%**.
Against its five neighbours, the pre-trend DiD is φ2 = +4.1 pp and the post DiD
is φ3 = +56.4 pp. Rajasthan's post-period jump ranks 1st of 26 states
(permutation p = 0.04).

## NFHS-6 (2023-24, provisional): Rajasthan only (`code/07_nfhs6_rajasthan.py`)

The uploaded compendium covers Rajasthan's 33 pre-2023 districts, so they line up
with NFHS-4/5. Our extraction reproduces the earlier NFHS-5 values exactly. It
has **no out-of-pocket indicator** and **no neighbouring states**, so it cannot
extend the border DiD. As a persistence check:

| District means | Insured NFHS-5 → 6 | Public-facility births | Private-facility births |
|---|---|---|---|
| Border (23) | 87.8 → 87.7 | 78.3 → 70.6 | 17.2 → 24.4 |
| Interior (10) | 90.0 → 92.0 | 80.6 → 75.4 | 14.1 → 18.8 |

Coverage stayed at its post-BSBY level: the effect persisted, and Chiranjeevi
(May 2021) added nothing measurable on this indicator because it was already
near the ceiling. Births shifted from public to private facilities. That is
consistent with insurance that pays private hospitals, but there is no control
group for it, so it is descriptive only.

## Run

```bash
pip install pandas statsmodels linearmodels matplotlib geopandas
python code/06a_border_pairs.py      # pairs + map (needs geopandas)
python code/07_nfhs6_rajasthan.py    # NFHS-6 extraction (used in checks)
python code/00_clean_and_checks.py   # cleaning + audit
python code/06_insurance_border.py   # border DiD, robustness, state event study
```

---

# Appendix: earlier PMUY analysis

## Welfare analysis of PM Ujjwala Yojana (PMUY) in Rajasthan: evidence from NFHS-4 and NFHS-5

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

### Run (PMUY)

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
