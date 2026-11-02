# Presentation guide: methods, results and figures

Every number here comes from the final pipeline (`./run_all.sh`), which runs on
cleaned data only and stops unless the data audit passes. File references point
to where each number is produced.

---

## 0. The study on one slide

| | |
|---|---|
| **Title** | Rajasthan's state health insurance scheme and household welfare: a border-district difference-in-differences |
| **Question** | Did Rajasthan's Bhamashah Swasthya Bima Yojana (BSBY, Dec 2015) raise health insurance coverage and reduce out-of-pocket (OOP) spending, relative to districts just across the state border that had only the national schemes? |
| **Data** | NFHS-3 (2005-06), NFHS-4 (2015-16), NFHS-5 (2019-21) factsheets; NFHS-6 (2023-24, provisional) for Rajasthan; Census 2011 district map |
| **Design** | Contiguous border-pair DiD (Dube, Lester & Reich 2010): 23 Rajasthan × 26 neighbour districts, 40 usable pairs; plus a three-round state event study for pre-trends |
| **Main result** | Coverage rose **52.8 percentage points** more in Rajasthan border districts (SE 5.1, p < 0.001); robust in every check (+45 to +55) |
| **Welfare result** | **No detectable change in OOP per delivery.** The design is underpowered for it: the 95% CI (−₹2,003 to +₹1,291) is wider than the baseline (₹2,235) |
| **One-line takeaway** | The scheme reached people at scale, but this data can't show it reduced what they paid. |

---

## 1. Motivation

- **The policy problem:** OOP spending is a major source of financial
  hardship in India, and governments respond with tax-funded hospital insurance
  for poor households.
- **The national track record:** the scheme before PM-JAY, RSBY (2008), showed
  no reduction in OOP (Karan, Yip & Mahal 2017).
- **Rajasthan's response:** it launched its own, larger scheme (BSBY) in
  December 2015, covering about 1 crore families with cashless treatment in
  public and empanelled private hospitals.
- **The gap:** no published study evaluates BSBY's effect on coverage or OOP
  against a credible comparison group. Dupas & Jain (NBER WP 2021) study
  *who uses* BSBY from claims data, not its effect.

## 2. Policy timeline (memorise this)

| Date | Event | Why it matters |
|---|---|---|
| 2005-06 | NFHS-3 | Pre-period for the state pre-trend check |
| 2008 | RSBY (national) starts | Control states' insurance |
| 2012 | Gujarat's MA Yojana | Gujarat has its own scheme → robustness drops Gujarat |
| **13 Dec 2015** | **BSBY launched in Rajasthan** | **Treatment** |
| 23 Jan – 21 Jul 2016 | NFHS-4 fieldwork in Rajasthan | Baseline starts 6 weeks *after* launch → estimates are lower bounds |
| Sep 2018 | PM-JAY (national) | Control states get PM-JAY too |
| 2019 | BSBY merged with Ayushman Bharat (AB-MGRSBY) | Treatment continues under a new name |
| 2019-21 | NFHS-5 | Post-period |
| May 2021 | Chiranjeevi (Rajasthan, near-universal) | After NFHS-5 Rajasthan fieldwork |
| May 2023 – Jan 2024 | NFHS-6 fieldwork, Rajasthan | Persistence check |

**What the estimate means:** Rajasthan's scheme compared with the neighbours'
RSBY/PM-JAY, *not* insurance compared with no insurance.

---

## 3. Data

| Source | Content | Role |
|---|---|---|
| NFHS-4 & NFHS-5 district factsheets (IIPS), 641 districts | One value per district per indicator | Main analysis |
| Second copy of the same factsheets (phase-1 states) | Same values, with small-sample flags | Cross-check, flags |
| NFHS-3/4/5 state factsheets | State values | Event study |
| NFHS-6 Rajasthan compendium (Aug 2026, provisional) | 33 districts, NFHS-6 and NFHS-5 side by side | Cross-check, persistence |
| Census 2011 district map (datameet) | District boundaries | Finding border pairs |

**Outcomes**

| Variable | Definition | Role |
|---|---|---|
| Insurance coverage | % households with any member covered by a health insurance/financing scheme | First outcome (did the scheme reach people?) |
| OOP per delivery | Average OOP per delivery in a public health facility, real 2019-21 ₹ | Welfare outcome (financial protection) |
| log OOP | Natural log of the above | Same, robust to skew |
| Institutional births | % births in a health facility | Use of care |
| Public-facility births | % births in a public facility | Use of care / public–private shift |
| Electricity | % population in households with electricity | **Placebo** (insurance shouldn't affect it) |
| Women 10+ years school | % women with ≥10 years schooling | **Placebo** |

**Why districts on 2011 boundaries:** NFHS-4 and NFHS-5 report the 2011
districts. Rajasthan's 2023 districts (Kotputli-Behror, Balotra, Deeg, Salumbar,
etc.) sit inside their 2011 parents.

---

## 4. Data cleaning and checks (`code/00_clean_and_checks.py`)

The protocol was fixed **before** re-running any regression. Every check passes
(`output/checks/data_audit.md`), and the analysis refuses to run otherwise.

| Step | What was done | Result |
|---|---|---|
| Missing values | No imputation. 0 is the factsheet code for suppressed (<25 cases) or non-comparable values → missing | 70 OOP and 68 other zeros in NFHS-4 recoded |
| Structural missingness | Districts split after NFHS-4 have no comparable baseline | 5 neighbour districts dropped: Firozpur, Bhiwani, Shajapur, Sabarkantha, Panchmahal (51 → 40 pairs) |
| Differential missingness | Is OOP missing more often on one side? | 0/23 Rajasthan vs 0/21 neighbours (Fisher p = 1.00) |
| Cross-source agreement | Every outcome, both rounds, against a second copy and the NFHS-6 PDF | 100% exact; 33/33 Rajasthan districts exact |
| Ranges & logic | % in [0, 100], ₹ > 0, public births ≤ institutional births | 0 violations |
| Small-sample flags | NFHS marks 25–49-case estimates; the main file strips the marks | Recoverable only for Gujarat; no flagged border values |
| Inflation | OOP converted to real 2019-21 ₹ with CPI-Combined | NFHS-4 × 1.209 |
| Outliers (OOP) | Capped at Q3 + 1.5·IQR, fences per round over all 637 comparable districts | Caps ₹9,109 / ₹7,943; **no border district reaches them**; percentages not capped (bounded) |
| Standardisation | z = (x − μ)/σ, μ and σ from **NFHS-4 neighbour border districts**, applied to both rounds and sides | Lets outcomes be compared in SD units |
| State panel | Names harmonised across files; boundary-changed states dropped (J&K/Ladakh, DNH & Daman-Diu) | 27 states; NFHS-4 agrees across files within 0.7 pp |

**Why standardise this way:** z-scoring each round separately would force both
rounds to mean 0 and erase the change the DiD measures. Using one reference (the
pre-period comparison group) keeps β interpretable as "effect in SDs of the
pre-scheme comparison distribution" (Kling, Liebman & Katz 2007 convention).

**Baseline balance (NFHS-4, within pairs, Rajasthan − neighbour)**

| | Rajasthan | Neighbours | Difference | p |
|---|---|---|---|---|
| Insurance | 17.2 | 13.0 | +2.3 | 0.14 |
| OOP (real ₹) | 1,962 | 1,652 | +594 | 0.09 |
| Institutional births | 86.1 | 83.9 | +3.4 | 0.10 |
| Public-facility births | 65.9 | 59.0 | +6.8 | 0.03 |
| Electricity | 89.5 | 93.8 | −3.8 | 0.02 |
| Women 10+ yrs school | 23.2 | 25.8 | −1.8 | 0.27 |

DiD allows level differences. The higher baseline OOP raised a mean-reversion
concern, so a specification controlling for each district's NFHS-4 level was
added.

---

## 5. Sample: contiguous border pairs (`code/06a_border_pairs.py`)

1. Load the Census 2011 district map.
2. For each Rajasthan district, find every district in another state within
   500 m of its boundary. The tolerance absorbs digitisation gaps.
3. Measure the shared border length. The minimum is about 7 km, so there are no
   corner-only touches.
4. Result: **51 pairs: 23 Rajasthan × 26 neighbour districts** (MP 22 pairs,
   Haryana 13, Gujarat 10, Punjab 3, UP 3).
5. Join to NFHS on census codes, not names.
6. 11 pairs drop with the 5 split neighbour districts, leaving **40 pairs**.

**Whole districts only:** NFHS gives one value per district, so a partial
district is impossible. Three things make the map look otherwise: 2011 vs
current boundaries, Chittaurgarh's detached piece, and MP's Neemuch and Mandsaur
wedge.

---

## 6. Empirical strategy

### 6.1 Main equation

For district *i* in pair *p*:

  **ΔY_ip = β · Rajasthan_i + γ_p + ε_ip**,  where ΔY = Y(NFHS-5) − Y(NFHS-4)

- **ΔY:** with two rounds, differencing equals including district fixed
  effects. Everything time-invariant about a district (geography, culture,
  baseline wealth) drops out.
- **γ_p (pair fixed effect):** each Rajasthan district is compared only with
  the district touching it. Regional shocks shared by both sides of a border
  segment drop out.
- **β:** the average within-pair difference in change, i.e. the DiD.
- **Stacking:** a district bordering three neighbours appears in three pairs,
  as in Dube et al.

**Sanity check you can quote:** from the raw means (Figure 3), Rajasthan border
districts went 17.2 → 87.8 (+70.6) and neighbours 13.0 → 31.0 (+18.0). The
difference is +52.6, almost exactly the regression's +52.8.

### 6.2 Identifying assumption

**Parallel trends across the border:** without BSBY, Rajasthan's border
districts would have changed like the districts across the line. Contiguity
makes this plausible (shared climate, economy, culture). The state event study
(section 7) tests it with pre-period data.

### 6.3 Inference

- **The problem:** districts repeat across pairs, so their errors are correlated.
- **What Dube et al. do:** cluster by state and border segment. We have only 6
  states and 5 segments, too few to cluster on.
- **What we do:** **two-way clustering by Rajasthan district and neighbour
  district.**

### 6.4 Robustness (decided before looking at results)

| Check | Reason |
|---|---|
| Drop Gujarat | Own scheme since 2012 (Karan et al. drop states with own schemes) |
| MP border only | MP had almost no RSBY enrolment by 2016: the cleanest "no-insurance" comparison |
| Pairs sharing ≥ 10 km | Drops short borders |
| Control for NFHS-4 level | Responds to baseline imbalance / mean reversion |
| Leave-one-out | Drop each pair, and each Rajasthan district with all its pairs |
| OOP capped at 1.5·IQR | Outliers |
| Drop small-sample values | Where flags are recoverable |
| Placebo outcomes | Electricity, women's schooling (Sood et al. 2014 logic) |

---

## 7. Pre-trend: three-round state event study

NFHS-3 exists only at state level, so parallel trends are tested on states.

| Insurance coverage (%) | 2005-06 | 2015-16 | 2019-21 | Pre change | Post change |
|---|---|---|---|---|---|
| **Rajasthan** | 4.5 | 18.7 | **87.8** | +14.2 | **+69.1** |
| Gujarat | 10.2 | 23.1 | 39.0 | +12.9 | +15.9 |
| Madhya Pradesh | 4.8 | 17.7 | 38.1 | +12.9 | +20.4 |
| Haryana | 6.7 | 12.2 | 25.7 | +5.5 | +13.5 |
| Punjab | 6.8 | 21.2 | 25.2 | +14.4 | +4.0 |
| Uttar Pradesh | 1.2 | 6.1 | 15.9 | +4.9 | +9.8 |

Notation from Karan, Yip & Mahal (2017):

- **φ2 (pre-period DiD, 2005→2016) = +4.1 pp:** roughly parallel before
  the scheme.
- **φ3 (post-period DiD, 2016→2020) = +56.4 pp.**
- **Trend-adjusted φ3 − φ2 = +52.3 pp:** almost identical to the border-pair β.
- **Permutation inference** (Abadie et al. 2010; Conley & Taber 2011): each of
  27 states is "treated" in turn. Rajasthan's post-period gap ranks **1st of
  27**, so **p = 1/27 ≈ 0.037**. This is the smallest p-value achievable with
  27 states.

---

## 8. Results (`output/insurance/border_pair_did_main.csv`)

### 8.1 Main table (40 pairs, two-way clustered SEs)

| Outcome | β (SE) | p | β in SD | Control NFHS-4 level | Leave-one-Rajasthan-district-out |
|---|---|---|---|---|---|
| **Insurance coverage (pp)** | **+52.8 (5.1)** | **<0.001** | 7.3 | +55.1 (4.2) | +51.3 to +53.9 |
| OOP per delivery (real ₹) | −356 (840) | 0.67 | −0.44 | +227 (212), p = 0.29 | −478 to +30 |
| log OOP | −0.08 (0.31) | 0.80 | −0.17 | +0.09 (0.12) | −0.14 to +0.05 |
| Institutional births (pp) | −1.2 (2.3) | 0.62 | −0.09 | +0.8 (1.3) | −1.6 to −0.6 |
| Public-facility births (pp) | +2.4 (5.4) | 0.66 | 0.12 | +5.5 (3.9) | +1.3 to +4.2 |
| *Placebo:* electricity (pp) | +3.2 (3.5) | 0.35 | 0.56 | −0.1 (0.6) | +2.0 to +3.9 |
| *Placebo:* women 10+ yrs school (pp) | +3.1 (1.7) | 0.08 | 0.24 | +2.8 (1.5), p = 0.07 | +2.5 to +3.7 |

Capped OOP and the drop-small-sample column are identical to the main estimates
(nothing binds in the border sample).

### 8.2 Sample robustness (insurance coverage)

| Sample | β | SE | Pairs |
|---|---|---|---|
| All borders | 52.8 | 5.1 | 40 |
| Drop Gujarat | 51.2 | 5.5 | 35 |
| MP border only | 45.4 | 6.2 | 21 |
| Pairs ≥ 10 km | 52.0 | 5.0 | 38 |

All p < 0.001. No other outcome is significant in any sample.

### 8.3 How to explain each result

1. **Coverage, +52.8 pp.** Large, precise and stable. The smallest estimate
   (MP only, +45.4) is the cleanest comparison and is still huge. In SD units
   it's 7.3, because baseline coverage barely varied (SD 7.2 pp). It's a true
   number, but it shows why SD units can mislead for a near-zero-baseline
   outcome.
2. **OOP per delivery: no detectable effect, and that is not evidence of no effect.**
   - 95% CI −₹2,003 to +₹1,291; baseline ₹2,235.
   - Minimum detectable effect (80% power, 5% level) = 2.8 × SE = **₹2,352**, more than
     the whole baseline. The design can't detect even a complete elimination.
   - The negative point estimate is **mean reversion**. Rajasthan started higher
     (+₹594), and controlling for the NFHS-4 level flips it to +₹227. Dropping one
     district (Baran) moves it to +₹30.
   - **Why deliveries are a weak test:** public-facility deliveries have been
     free under JSSK since 2011 on *both* sides of the border. BSBY's value is in
     hospitalisations (surgery, cardiac, cancer), which NFHS doesn't measure at
     district level.
   - **Consistent with the literature:** Karan et al. (2017) find RSBY didn't
     reduce OOP.
3. **Births: no change.** Institutional births were already about 87% at
   baseline (ceiling).
4. **Placebos.** Electricity passes. Women's schooling is borderline (p ≈ 0.07–0.08).
   Report it honestly: a mild signal that Rajasthan's border districts were
   improving slightly faster on general development. It's small next to the
   coverage effect (0.24 SD vs 7.3 SD).

### 8.4 Persistence (NFHS-6, descriptive)

| Rajasthan district means | NFHS-5 | NFHS-6 |
|---|---|---|
| Insured, border (23) | 87.8 | 87.7 |
| Insured, interior (10) | 90.0 | 92.0 |
| Public-facility births, border | 78.3 | 70.6 |
| Private-facility births, border | 17.2 | 24.4 |

- **Coverage held:** the effect didn't fade. Chiranjeevi (2021) added nothing
  measurable because coverage was already at about 88% (ceiling).
- **Births moved toward private facilities.** That fits insurance paying private
  hospitals, but there's **no comparison group**, so it's descriptive only.

---

## 9. Figures (`output/insurance/`)

### Figure 1: Border sample map (`fig_border_map.png`)
- **Shows:** red = 23 Rajasthan border districts (treated); blue = 26
  neighbouring districts touching them (control); pale = interior Rajasthan
  (excluded). Census 2011 boundaries.
- **Say:** "We compare only districts that touch across the state line, so
  geography, climate and local economy are shared."
- **If asked about odd shapes:** 2011 boundaries (Jaipur included Kotputli),
  Chittaurgarh's detached piece (arrowed), and MP's Neemuch–Mandsaur wedge.

### Figure 2: State event study (`fig_state_event_study.png`)
- **Shows:** insurance coverage in Rajasthan (red) and its five neighbours (grey)
  across NFHS-3, 4 and 5. The dashed line is BSBY's launch.
- **Say:** "Before 2016 Rajasthan tracks its neighbours. Then it jumps to 88%,
  while they reach 16–39%."
- **This is the parallel-trends evidence.** Its weakness: only one pre-period
  point, at state level.

### Figure 3: Coverage in border districts over three rounds (`fig_coverage_three_rounds.png`)
- **Shows:** district means. Rajasthan border districts go 17.2 → 87.8 → 87.7;
  neighbour border districts go 13.0 → 31.0 (their NFHS-6 isn't available).
- **Say:** "The raw DiD is visible by eye: 70.6 vs 18.0 points, a gap of 52.6,
  which the regression reproduces. The effect then plateaus."
- **Note:** the regression's baseline mean (15.1) differs slightly from 17.2,
  because in the regression districts appear once per pair they belong to.

### Figure 4: Coefficient plot (`fig_coefficients.png`)
- **Panel A:** the coverage effect (pp, 95% CI) across all specifications
  (+45 to +55, far from zero).
- **Panel B:** the other outcomes in SD units. All CIs cross zero. OOP's CI is
  the widest, which is the underpowering. Placebos are in grey.
- **Say:** "The scheme moved coverage. Nothing else moved detectably, and the
  placebos are flat."

---

## 10. Limitations (say these before you're asked)

1. **Contaminated baseline:** NFHS-4 Rajasthan fieldwork started 6 weeks after
   launch, so β is a **lower bound**.
2. **The comparison is scheme vs scheme**, not insurance vs none.
3. **District averages:** eligible and ineligible households can't be
   separated, so there's no triple difference.
4. **Districts are large** (Barmer ≈ 28,000 km²). This compares border districts,
   not border villages.
5. **OOP covers deliveries only,** and the design is underpowered for it.
6. **One pre-period point, at state level.**
7. **Cost is a floor:** the BSBY premium isn't public, so cost uses official claims paid
   (section 12b). Benefits are not monetised (OOP null), so this is cost-effectiveness plus
   break-even, not a full CBA.
8. **NFHS-6 is provisional** and Rajasthan-only.

**Future work:** NSS 71st vs 75th rounds for OOP per hospitalisation; NFHS
GPS-cluster data for a spatial RDD (Dell 2010; Sood et al. 2014); neighbours'
NFHS-6 for a three-round border event study.

---

## 11. Literature positioning

| Paper | Method / topic | How we use it |
|---|---|---|
| Dube, Lester & Reich (2010), *REStat* | Contiguous county-pair DiD | Our design |
| Card & Krueger (1994), *AER* | Cross-border DiD | Classic precedent |
| Abadie, Diamond & Hainmueller (2010), *JASA* | One treated unit, permutation inference | State-level inference |
| Conley & Taber (2011), *REStat* | Inference with few treated groups | Why not conventional SEs |
| Karan, Yip & Mahal (2017), *Soc Sci Med* | RSBY, DiD, OOP | Control group's scheme; null OOP benchmark; φ notation |
| Sood et al. (2014), *BMJ* | Karnataka insurance, geographic RD, villages | Closest topic + method; placebo logic; future work |
| Dupas & Jain (2021), NBER WP | BSBY claims, gender gaps | Same scheme, different question |
| Kling, Liebman & Katz (2007), *Econometrica* | Standardised effects | SD-unit convention |
| Dell (2010), *Econometrica* | Spatial RDD | Future work |

---

## 12. Likely questions and answers

**Q: Why not a regression discontinuity?**
A: An RDD needs a running variable, e.g. each household's distance to the
border. We only have district averages. The border-pair DiD is the
district-level equivalent. A GPS-based RDD is future work.

**Q: NFHS-4 was collected after BSBY started. Doesn't that break the DiD?**
A: It biases β *toward zero*, because early enrolment raises the baseline. So
+52.8 is a lower bound. The state data also shows Rajasthan's 2016 level was in
line with its neighbours (18.7% vs 6–23%), so contamination was small.

**Q: How do you know trends were parallel?**
A: State level, NFHS-3 → NFHS-4: Rajasthan +14.2 pp vs neighbours' mean +10.1
pp (φ2 = +4.1). The post-period gap is 56.4. One pre-period, so it supports the
assumption rather than proving it.

**Q: Isn't the control group also insured?**
A: Yes: RSBY, then PM-JAY. So the estimate is Rajasthan's scheme *relative to*
the national schemes. The MP-only sample (no RSBY enrolment by 2016) gives +45.4.

**Q: Why is OOP not significant? Does insurance not work?**
A: The design can't tell. The MDE (₹2,352) exceeds the baseline (₹2,235).
Deliveries in public facilities were already free under JSSK, so it's the wrong
margin for a hospitalisation scheme. Karan et al. found the same for RSBY with
better data.

**Q: The women's-schooling placebo is borderline. Does that worry you?**
A: Somewhat. It suggests slightly faster general development in Rajasthan's
border districts. But it's 0.24 SD against 7.3 SD for coverage, and adding
the baseline control doesn't change coverage.

**Q: Did outliers drive anything?**
A: No. OOP was capped at Q3 + 1.5·IQR, but no border district reaches the cap.
Leave-one-out keeps coverage between +51.3 and +53.9.

**Q: Why min-max/z-scores at all?**
A: Only to compare outcomes on one scale (Figure 4B). Headline results stay in
natural units. z-scores use the pre-period comparison group's mean and SD,
applied to both rounds, because standardising each round separately would erase
the change being measured.

**Q: Why two-way clustering?**
A: Each district appears in several pairs, so its errors repeat. Clustering on
both the Rajasthan and the neighbour district handles that. Dube et al. cluster
by state and border segment, but 6 states / 5 segments are too few clusters.

**Q: What would you do with more time?**
A: (1) NSS health rounds for OOP per hospitalisation. (2) NFHS GPS clusters for a
spatial RDD. (3) The premium cost for a full cost-benefit analysis.
(4) Neighbours' NFHS-6.

---

## 12b. Cost-effectiveness and break-even (`code/08_cost_effectiveness.py`)

**Status:** complete with sourced inputs. All inputs pass the cleaning checks
(`output/checks/data_audit.md`, cost-effectiveness section).

**Headline:** BSBY cost about **₹492 per additionally insured household per year**
(2019-21 ₹), with a range of ₹414–608 over the 95% CI of β and ₹572 with the
conservative MP-only β. About **40%** of spending goes to households that would
have had some insurance anyway.

### Why not a full cost-benefit analysis
A CBA needs a rupee value for benefits. Our only welfare outcome (OOP) is null
and underpowered, so any benefit figure would be borrowed from other studies.
We report what the coverage cost (tier 1), and how large a benefit would be
needed to justify it (tier 2).

### Method source
The **incremental cost-effectiveness ratio** = incremental cost ÷ incremental effect
(Drummond et al., *Methods for the Economic Evaluation of Health Care Programmes*;
Boardman et al., *Cost-Benefit Analysis: Concepts and Practice*). It is applied to
an evaluation's causal effect as in J-PAL's **Dhaliwal, Duflo, Glennerster &
Tulloch (2013)**, "Comparative Cost-Effectiveness Analysis to Inform Policy in
Developing Countries".

### Formula

  **Cost per additionally insured household per year = (p_BSBY · c_Raj − p_RSBY · c_cf) / β**

| Symbol | Value | Source |
|---|---|---|
| β | 0.528 (CI 0.428–0.628; MP-only 0.454) | Our cleaned border-pair DiD |
| c_Raj | 0.875 | NFHS-5 coverage in Rajasthan border districts, weighted as in β |
| c_cf = c_Raj − β | 0.347 | Coverage the districts would have had without BSBY |
| p_BSBY (cost) | **₹297 per family per year** (floor, 2019-21 ₹) | SIHFW BSBY presentation: claims paid ₹295.63 cr, 13 Dec 2015 – 10 Feb 2017 (p. 19), ~1 crore eligible families (p. 2) |
| p_RSBY (counterfactual) | **0 in the main spec**; ₹560 as a sensitivity | Rajasthan "still in the early stages of rolling-out RSBY as of September 2016" (Karan et al. 2017, p. 84); ₹560 from their Table 1, p. 85 |

**Why households cancel:** spending = premium × covered families, and covered
families = coverage rate × households. So the ratio needs no population counts.

### Why each choice (for questions)
| Choice | Reason |
|---|---|
| Divide by β, not by all enrolees | Coverage would have risen anyway (neighbours +18 pp); only households insured *because of* BSBY count as the effect |
| Count spending on already-insured families | Paying for them is part of the cost of reaching new ones (crowd-out logic) |
| Subtract RSBY counterfactual spending | Cost and effect share the same counterfactual: Rajasthan's scheme vs the national scheme |
| p_RSBY = 0 as a sensitivity | Rajasthan was early in RSBY rollout in 2016 (Karan et al.), so the counterfactual spending may be near zero; this gives an upper bound |
| CI and MP-only β | Effect uncertainty carries through; the smallest β gives the most conservative (highest) cost |
| NFHS coverage ≈ enrolment | NFHS counts any insurance, so c_Raj slightly overstates BSBY enrolment → the ratio is an upper bound |

### Where the cost figure comes from
The premium itself is not public in citable form. The official SIHFW deck reports
**claims paid**: ₹295.63 crore over 1.16 years for about 1 crore families. That is
₹254 per family per year in nominal terms, or **₹297 in 2019-21 rupees** (CPI-C,
time-weighted over the claims window). The state paid the insurer *at least*
this much, and the deck's profit-refund clause (p. 18) pushes the premium toward
claims. So it is a floor on cost.

Cleaning checks on the transcribed claims table: Pvt + Govt = Total for every row;
the funnel is monotone (enlisted ₹414.67 cr ≥ submitted ≥ approved ≥ paid ₹295.63 cr);
the average paid claim (₹4,927) is plausible.

### Results (`output/cba/cost_effectiveness.csv`)
| β case | Cost per additionally insured household per year (2019-21 ₹) |
|---|---|
| Main (0.528) | **₹492** |
| 95% CI of β | ₹414 – ₹608 |
| MP border only (0.454, conservative) | ₹572 |
| Sensitivity: offset by full RSBY premium ₹560 | ₹125 (mixes a claims floor with a premium, so not the main estimate) |

General form: cost = 1.66 × (BSBY cost per family) with the main β.

**Bias directions (say these):**
- *Understated:* claims are below the premium (insurer margin), and the window
  includes the early ramp-up months.
- *Overstated:* NFHS coverage counts any insurance, so c_Raj overstates BSBY
  enrolment, and some RSBY spending would have happened without BSBY.

### Tier 2: break-even
The annual benefit an additionally insured household must receive for the scheme
to pay for itself equals the ratio above: **about ₹492 a year**. For scale, BSBY
paid an average of ₹4,927 per claim, and about 5% of eligible families had a
paid claim per year (6,00,033 claims over 1.16 years among ~1 crore families). Plausibility, as scenarios rather than
estimates: Karan et al. (2017) find ~₹0 OOP savings under RSBY; Sood et al. (2014)
find 64% lower OOP for covered tertiary care. Our OOP CI per delivery (−₹2,003 to
+₹1,291) cannot confirm or rule out the break-even.

### Tier 3 (future work)
Value of risk protection (Finkelstein & McKnight 2008) and MVPF (Hendren &
Sprung-Keyser 2020) need household-level spending data (NSS health rounds).

---

## 13. Glossary

| Term | Meaning here |
|---|---|
| DiD | Difference-in-differences: change in treated minus change in control |
| Border-pair / contiguous pair | A Rajasthan district and a district touching it across the state line |
| Pair fixed effect | Separate intercept per pair, so comparisons stay within pairs |
| Two-way clustering | SEs allowing correlation within each Rajasthan district and within each neighbour district |
| φ2, φ3 | Pre- and post-period DiD in the state event study |
| Permutation p | Share of states whose placebo "effect" is at least as large as Rajasthan's |
| MDE | Minimum detectable effect = 2.8 × SE (80% power, 5% two-sided) |
| Mean reversion | Units that start unusually high tend to fall back on their own |
| 1.5·IQR rule | Cap values above Q3 + 1.5 × (Q3 − Q1) |
| z-score | (x − mean) / SD, here using the NFHS-4 neighbour-border reference |
| OOP | Out-of-pocket spending |
| JSSK | Janani Shishu Suraksha Karyakram (free public-facility deliveries since 2011) |

---

## 14. Reproducibility

```bash
./run_all.sh
```

| Step | Script | Output |
|---|---|---|
| 1 | `code/06a_border_pairs.py` | `data/clean/border_pairs.csv`, Figure 1 |
| 2 | `code/07_nfhs6_rajasthan.py` | `data/interim/nfhs6_rajasthan_extracted.csv` |
| 3 | `code/00_clean_and_checks.py` | cleaned data, `output/checks/data_audit.md`, `audit_status.txt` |
| 4 | `code/06_insurance_border.py` | results CSVs, Figures 2–4 (runs only if the audit passes) |
