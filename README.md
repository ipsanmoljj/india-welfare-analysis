# Welfare analysis of PM Ujjwala Yojana (PMUY): district-level evidence from NFHS-4 and NFHS-5

Class project. PMUY (May 2016) gave free LPG connections to poor households, which
reached 8 crore connections by Sept 2019. NFHS-4 (2015-16) was collected just
before launch and NFHS-5 (2019-21) after, which gives a clean before/after at
district level.

**Question:** Did PMUY move households onto clean cooking fuel, did that improve
health, and is the scheme welfare-improving once costs are counted?

## Design

Intensity difference-in-differences over **575 districts** in both rounds
(districts created after NFHS-4 are dropped).

- **Exposure:** % of households NOT using clean fuel in NFHS-4. Higher exposure
  means more PMUY-eligible households.
- **Specification:** first differences (district FE) on exposure, with state FE,
  baseline electricity, sanitation, water and women's schooling, plus the
  baseline level of each outcome (absorbs mean reversion).
- **2SLS:** exposure instruments the change in clean-fuel use, for health outcomes.
- **Placebo:** institutional births, which cooking fuel should not affect.
- **Inference:** SEs clustered by state.

## Results so far

| | Estimate | p |
|---|---|---|
| First stage, linear (Δ clean fuel per 1 pp exposure) | 0.16 | 0.003 |
| First stage, quadratic: exposure / exposure²/100 | 0.67 / −0.50 | <0.001 |
| 2SLS child ARI, stunting, underweight, anaemia; women anaemia | all small, none significant | >0.3 |
| Placebo: institutional births | null | 0.21 |

1. **Adoption moved, but not most where need was greatest.** The effect peaks
   around 67% baseline non-use and declines after that. Districts that were
   90%+ on solid fuel gained less than middling districts. This fits a refill
   affordability story: getting a connection is not the same as using it.
2. **No detectable health effect at district level.** An earlier "stunting effect"
   disappears once the baseline level is controlled for (mean reversion). This
   is a null at district-average resolution, not evidence of zero individual
   effect. NFHS measures *main* fuel, and fuel stacking is common.
3. **Conversion:** Under the assumption that zero-exposure districts got no PMUY
   effect, the linear first stage implies about 10 pp more households on clean
   fuel, i.e. about 2.9 crore switchers from 8 crore connections (**~37%
   conversion**). That works out to about Rs 4,350 of connection subsidy per
   effective switcher.
4. **CBA (per beneficiary household, 10 yrs, 8%):** Social NPV is about
   **Rs 21,700** in the base case, with time valued at 50% of the rural wage, 3.95
   refills/yr and health = 0. MVPF ≈ 3.3. **The sign depends on how time is
   valued:** at 25% of the wage, NPV is negative at any refill level. See
   `output/fig_cba_sensitivity.png`.

## Run

```bash
pip install pandas statsmodels linearmodels matplotlib
python code/01_build_panel.py
python code/02_pmuy_did.py
python code/04_cba.py
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
| LPG unsubsidised price | Rs 850 | IOCL Delhi price | check |
| Firewood collection hours | 660 / household / yr | Practical Action (2015) | check original |
| Rural female wage | Rs 300/day | **assumption**; replace with PLFS / Labour Bureau | replace |
| Stove cost | Rs 1,000 | **assumption** | replace |
| Full-LPG refills / yr | 7 | **assumption** | replace |

## Limitations

- Exposure correlates with poverty. State FE, baseline controls and the placebo
  help but don't fully rule out differential trends. With only two rounds there
  is no pre-trend test.
- The first stage is borderline weak for 2SLS (clustered F ≈ 9).
- The level effect behind the conversion rate needs the "zero exposure → zero
  effect" assumption.
- Factsheet data is district averages. Household-level NFHS microdata (DHS
  registration) would allow a stronger design.
