"""Clean the district data for the BSBY border analysis and run sanity checks.

Strategy (decided before re-running any regression):
  1. Missing values: no imputation. Districts split after NFHS-4 are dropped;
     0 is the factsheet code for suppressed (<25 cases) or not-comparable values,
     so 0 -> missing. Small-sample (25-49 case) flags are recovered where a source
     still carries them (pratapvardhan file = phase-1 states, incl. Gujarat).
  2. Sanity checks: cross-source agreement, keys, ranges, logic, large jumps,
     baseline balance, missingness by side.
  3. Outliers (OOP only; percentages are bounded 0-100 and left as is):
     real rupees -> cap at Q3 + 1.5*IQR, fences per round over all comparable
     districts; log outcome capped with fences computed on the log scale.
  4. Standardisation: z = (x - mean) / SD with mean and SD from NFHS-4
     neighbour border districts, applied to both rounds and both sides.

Outputs:
  data/clean/insurance_district_clean.csv   one row per comparable district
  data/clean/state_insurance_clean.csv      NFHS-3/4/5 state panel (event study)
  data/clean/nfhs6_rajasthan_districts.csv  validated NFHS-6 Rajasthan extract
  output/checks/data_audit.md               pass/fail log of every check
  output/checks/audit_status.txt            PASS only if every check passes;
                                            analysis scripts refuse to run otherwise
"""
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, CHK = ROOT / "data" / "raw", ROOT / "data" / "clean", ROOT / "output" / "checks"
CHK.mkdir(parents=True, exist_ok=True)

VARS = {
    "Households with any usual member covered under a health insurance/financing scheme (%)": "insur",
    "Average out-of-pocket expenditure per delivery in a public health facility (Rs)": "oop",
    "Institutional births (%)": "inst",
    "Institutional births in public facility (%)": "inst_public",
    "Population living in households with electricity (%)": "electricity",
    "Women with 10 or more years of schooling (%)": "women_school10",
}
PCT = ["insur", "inst", "inst_public", "electricity", "women_school10"]
# CPI-Combined (2012=100). 2013-14 = 112.2 (RBI Handbook); chained with annual
# CPI-C inflation 5.9, 4.9, 4.5, 3.6, 3.4, 4.8, 6.2 % -> 2020-21 = 155.3, which
# matches the mean of RBI's monthly 2020-21 values. NFHS-4 fieldwork centres on
# FY2015-16; NFHS-5 spans FY2019-20 and FY2020-21.
CPI = {"4": 124.7, "5": (146.3 + 155.3) / 2}
CPI_BASE = CPI["5"]  # report real OOP in NFHS-5 (2019-21) rupees

log = []


def check(name, ok, detail=""):
    log.append(f"| {'PASS' if ok else 'FLAG'} | {name} | {detail} |")


def norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


# ---------------------------------------------------------------- 1. load + missing
k = pd.read_csv(RAW / "nfhs_districts_641_kalla.csv", low_memory=False)
k = k[k["Indicator"].isin(VARS)].copy()
k["dt"] = pd.to_numeric(k["DT_CEN_CD"], errors="coerce")
n_new = k.loc[k["dt"].isna(), "District"].nunique()
k = k.dropna(subset=["dt"])  # districts created after the 2011 census
k["v"] = k["Indicator"].map(VARS)
zero_counts = {}
for r, c in [("4", "NFHS 4"), ("5", "NFHS 5")]:
    raw = pd.to_numeric(k[c], errors="coerce")
    zero_counts[r] = k.loc[raw == 0, "v"].value_counts().to_dict()
    k[r] = raw.replace(0, np.nan)
w = k.pivot_table(index=["ST_CEN_CD", "dt"], columns="v", values=["4", "5"], aggfunc="first")
w.columns = [f"{v}_{r}" for r, v in w.columns]
w = w.reset_index()
names = k.drop_duplicates(["ST_CEN_CD", "dt"]).set_index(["ST_CEN_CD", "dt"])[["State", "District"]]
w = w.merge(names, left_on=["ST_CEN_CD", "dt"], right_index=True)
check("Keys unique (state code, district code)", not w.duplicated(["ST_CEN_CD", "dt"]).any(),
      f"{len(w)} districts with census codes; {n_new} post-2011 districts dropped")
check("Zero = missing code", True,
      f"zeros recoded to missing - NFHS-4: {zero_counts['4']}; NFHS-5: {zero_counts['5']}")

# Small-sample flags from the pratapvardhan file (phase-1 states only)
p = pd.read_csv(RAW / "nfhs5_districts_with_nfhs4.csv")
# Match indicator names exactly after dropping numbering, footnote digits and punctuation
p["v"] = p["Indicator"].str.replace(r"^\d+\.\s*", "", regex=True).map(norm).map(
    {norm(key): v for key, v in VARS.items()})
p = p.dropna(subset=["v"])
p["key"] = p["State"].map(norm).str[:6] + p["District"].map(norm)
w["key"] = w["State"].map(norm).str[:6] + w["District"].map(norm)
for r, col in [("4", "NFHS-4-note"), ("5", "NFHS-5-note")]:
    fl = p[p[col].fillna("").str.contains("25-49")][["key", "v"]]
    for v in VARS.values():
        w[f"{v}_{r}_small"] = w["key"].isin(fl.loc[fl.v == v, "key"])
w["flag_source"] = w["key"].isin(set(p["key"]))

# ---------------------------------------------------------------- 2. sanity checks
# Cross-source agreement: Kalla vs pratapvardhan, every outcome and round
p["n4"], p["n5"] = pd.to_numeric(p["NFHS-4"], errors="coerce"), pd.to_numeric(p["NFHS-5"], errors="coerce")
cmp = []
for v in VARS.values():
    pv = p[p.v == v][["key", "n4", "n5"]]
    m = w[["key", f"{v}_4", f"{v}_5"]].merge(pv, on="key")
    for r in ["4", "5"]:
        d = (m[f"{v}_{r}"] - m[f"n{r}"]).abs().dropna()
        cmp.append((v, r, len(d), (d < 0.05).mean() if len(d) else np.nan, d.max() if len(d) else np.nan))
cmp = pd.DataFrame(cmp, columns=["var", "round", "n", "share_exact", "max_abs_diff"])
check("Cross-source: Kalla vs pratapvardhan (341 phase-1 districts)",
      (cmp.share_exact > 0.98).all(),
      "; ".join(f"{r.var}-{r.round}: {r.share_exact:.0%} of {r.n}" for r in cmp.itertuples()))

# Cross-source: NFHS-5 column printed in the NFHS-6 Rajasthan compendium
n6 = pd.read_csv(ROOT / "data" / "interim" / "nfhs6_rajasthan_extracted.csv")
n6["key"] = "rajast" + n6["district"].replace({"Chittorgarh": "Chittaurgarh", "Dholpur": "Dhaulpur",
                                                "Jalore": "Jalor"}).map(norm)
m6 = w.merge(n6, on="key", suffixes=("", "_n6"))
diffs = {v: (m6[f"{v}_5"] - m6[f"{v}_5_n6"]).abs().max() for v in ["insur", "inst", "inst_public", "electricity"]}
check("Cross-source: Kalla NFHS-5 vs NFHS-6 compendium (Rajasthan)", len(m6) == 33 and max(diffs.values()) < 0.05,
      f"{len(m6)}/33 districts matched; max abs diff {diffs}")

# NFHS-6 extract: ranges and logic, then save the validated copy
n6_bad = sum(((n6[c] < 0) | (n6[c] > 100)).sum() for c in n6.columns if c[-2:] in ("_5", "_6"))
n6_logic = sum((n6[f"inst_public_{r}"] > n6[f"inst_{r}"] + 0.5).sum() for r in "56")
check("NFHS-6 extract: 33 districts, values in [0, 100], public <= institutional births",
      len(n6) == 33 and n6_bad == 0 and n6_logic == 0 and not n6.isna().any().any(),
      f"{len(n6)} districts, {n6_bad} range violations, {n6_logic} logic violations")
n6.drop(columns=["key"]).to_csv(CLEAN / "nfhs6_rajasthan_districts.csv", index=False)

# State panel for the event study: NFHS-3 and NFHS-4 (HT file), NFHS-4 and NFHS-5 (pratapvardhan)
STATE_NAMES = {"Andaman & Nicobar Islands": "Andaman and Nicobar Islands", "NCT Delhi": "Delhi",
               "Jammu & Kashmir": "Jammu and Kashmir"}
# Boundaries changed between rounds: J&K lost Ladakh (2019); DNH and Daman & Diu merged (2020)
STATE_DROP = {"Jammu and Kashmir", "Ladakh", "Dadra and Nagar Haveli", "Daman and Diu",
              "Dadra & Nagar Haveli and Daman & Diu", "India"}
s3 = pd.read_csv(RAW / "nfhs4_states_ht.csv")
s3 = s3[s3["indicator"].str.contains("health scheme or health insurance", case=False)]
s3 = s3[["state", "total_2005-06", "total"]].rename(columns={"total_2005-06": "y2005", "total": "y2015_ht"})
s5 = pd.read_csv(RAW / "nfhs5_states_with_nfhs4.csv")
s5 = s5[s5["indicator"].str.contains("health insurance", case=False)]
s5 = s5[["state", "nfhs4_total", "nfhs5_total"]].rename(columns={"nfhs4_total": "y2015", "nfhs5_total": "y2020"})
for f in (s3, s5):
    f["state"] = f["state"].replace(STATE_NAMES)
st = s3.merge(s5, on="state", how="outer", indicator=True)
unmatched = sorted(set(st.loc[st._merge != "both", "state"]) - STATE_DROP)
dropped = sorted(set(st["state"]) & STATE_DROP)
st = st[(st._merge == "both") & ~st.state.isin(STATE_DROP)].drop(columns="_merge")
for c in ["y2005", "y2015_ht", "y2015", "y2020"]:
    st[c] = pd.to_numeric(st[c], errors="coerce").replace(0, np.nan)
st = st.dropna(subset=["y2005", "y2015", "y2020"])
check("State panel: names harmonised, no unmatched states", not unmatched,
      f"{len(st)} states/UTs; dropped (boundary change or aggregate): {', '.join(dropped)}; unmatched: {unmatched}")
gap = (st["y2015"] - st["y2015_ht"]).abs()
check("State panel: NFHS-4 agrees across the two files (<= 1 pp)", gap.max() <= 1.0,
      f"max gap {gap.max():.1f} pp ({', '.join(st.loc[gap > 0, 'state'])}); NFHS-5 file's revised NFHS-4 used")
check("State panel: values in [0, 100]",
      ((st[["y2005", "y2015", "y2020"]] < 0) | (st[["y2005", "y2015", "y2020"]] > 100)).sum().sum() == 0, "")
st.drop(columns=["y2015_ht"]).to_csv(CLEAN / "state_insurance_clean.csv", index=False)

# Ranges and logic
bad_pct = sum(((w[f"{v}_{r}"] < 0) | (w[f"{v}_{r}"] > 100)).sum() for v in PCT for r in "45")
check("Percentages within [0, 100]", bad_pct == 0, f"{bad_pct} violations")
check("OOP > 0", ((w[["oop_4", "oop_5"]] <= 0).sum().sum()) == 0, "")
viol = [(r, (w[f"inst_public_{r}"] > w[f"inst_{r}"] + 0.5).sum()) for r in "45"]
check("Public-facility births <= institutional births (0.5 pp tolerance)", all(n == 0 for _, n in viol),
      f"violations NFHS-4: {viol[0][1]}, NFHS-5: {viol[1][1]}")

# ---------------------------------------------------------------- 3. OOP: real, capped
for r in "45":
    w[f"oop_real_{r}"] = w[f"oop_{r}"] * CPI_BASE / CPI[r]
fences = {}
for r in "45":
    x = w[f"oop_real_{r}"].dropna()
    q1, q3 = x.quantile([0.25, 0.75])
    hi = q3 + 1.5 * (q3 - q1)
    lx = np.log(x)
    lq1, lq3 = lx.quantile([0.25, 0.75])
    llo, lhi = lq1 - 1.5 * (lq3 - lq1), lq3 + 1.5 * (lq3 - lq1)
    fences[r] = dict(level_hi=hi, log_lo=np.exp(llo), log_hi=np.exp(lhi))
    w[f"oop_cap_{r}"] = w[f"oop_real_{r}"].clip(upper=hi)
    w[f"log_oop_{r}"] = np.log(w[f"oop_real_{r}"])
    w[f"log_oop_cap_{r}"] = w[f"log_oop_{r}"].clip(llo, lhi)
    w[f"oop_capped_{r}"] = w[f"oop_real_{r}"] > hi
check("OOP real-terms conversion (CPI-C)", True, f"NFHS-4 x {CPI_BASE / CPI['4']:.3f}, NFHS-5 x {CPI_BASE / CPI['5']:.3f}")
check("OOP 1.5*IQR fences (all comparable districts, per round)", True,
      "; ".join(f"NFHS-{r}: level cap Rs {f['level_hi']:,.0f} ({w[f'oop_capped_{r}'].sum()} capped), "
                f"log fences Rs {f['log_lo']:,.0f}-{f['log_hi']:,.0f}" for r, f in fences.items()))

# ---------------------------------------------------------------- border sample checks
pairs = pd.read_csv(CLEAN / "border_pairs.csv")
raj_keys = set(zip(pairs.raj_st, pairs.raj_dt))
nb_keys = set(zip(pairs.nb_st, pairs.nb_dt))
codes = list(zip(w.ST_CEN_CD, w.dt))
w["side"] = ["raj" if c in raj_keys else "nb" if c in nb_keys else "" for c in codes]
check("All pair districts found in NFHS", raj_keys | nb_keys <= set(codes),
      f"{len(raj_keys)} Rajasthan + {len(nb_keys)} neighbour districts")
b = w[w.side != ""]

# Missingness by side
miss_rows, oop_miss = [], {}
for v in VARS.values():
    for s in ["raj", "nb"]:
        g = b[b.side == s]
        miss_rows.append((v, s, len(g), g[f"{v}_4"].isna().sum(), g[f"{v}_5"].isna().sum()))
miss = pd.DataFrame(miss_rows, columns=["var", "side", "n", "missing_NFHS4", "missing_NFHS5"])
# Structural: districts split after NFHS-4 have every NFHS-4 value missing
structural = b[[f"{v}_4" for v in VARS.values()]].isna().all(axis=1)
check("Structural missingness (districts split after NFHS-4)", True,
      ", ".join(f"{r.District} ({r.State})" for r in b[structural].itertuples()) + " - excluded from all pairs")
comp = b[~structural]
any_miss = comp[["oop_4", "oop_5"]].isna().any(axis=1)
tab = pd.crosstab(comp.side, any_miss).reindex(columns=[False, True], fill_value=0)
p_fisher = stats.fisher_exact(tab.to_numpy())[1]
check("Differential OOP missingness among comparable districts (Fisher exact)", p_fisher > 0.10,
      f"missing: Rajasthan {tab.loc['raj', True]}/{tab.loc['raj'].sum()}, "
      f"neighbours {tab.loc['nb', True]}/{tab.loc['nb'].sum()}; p = {p_fisher:.2f}")

# Large jumps in the border sample
jumps = []
for v in PCT:
    d = (b[f"{v}_5"] - b[f"{v}_4"]).abs()
    jumps += [(r.District, r.State, v, r[f"{v}_4"], r[f"{v}_5"]) for _, r in b[d > 30].iterrows()]
ratio = b["oop_real_5"] / b["oop_real_4"]
jumps += [(r.District, r.State, "oop_real", round(r.oop_real_4), round(r.oop_real_5))
          for _, r in b[(ratio > 3) | (ratio < 1 / 3)].iterrows()]
jumps = pd.DataFrame(jumps, columns=["district", "state", "var", "NFHS-4", "NFHS-5"])
n_ins = (jumps["var"] == "insur").sum()
check("Large jumps (>30 pp, or OOP ratio >3x) in border sample", True,
      f"{len(jumps)} flagged, of which {n_ins} are insurance coverage (the treatment itself); listed below")

# Baseline balance (NFHS-4), within-pair differences
bal = []
for v in ["insur", "oop_real", "inst", "inst_public", "electricity", "women_school10"]:
    col = f"{v}_4"
    pr = pairs.merge(w[["ST_CEN_CD", "dt", col]], left_on=["raj_st", "raj_dt"], right_on=["ST_CEN_CD", "dt"]) \
        .merge(w[["ST_CEN_CD", "dt", col]], left_on=["nb_st", "nb_dt"], right_on=["ST_CEN_CD", "dt"],
               suffixes=("_raj", "_nb"))
    d = (pr[f"{col}_raj"] - pr[f"{col}_nb"]).dropna()
    t = stats.ttest_1samp(d, 0)
    bal.append((v, b.loc[b.side == "raj", col].mean(), b.loc[b.side == "nb", col].mean(), d.mean(), t.pvalue, len(d)))
bal = pd.DataFrame(bal, columns=["var", "raj_mean", "nb_mean", "within_pair_diff", "p", "pairs"])

# ---------------------------------------------------------------- 4. standardisation
z_ref = {}
for v in PCT + ["oop_cap", "log_oop"]:
    ref = b.loc[b.side == "nb", f"{v}_4"]
    mu, sd = ref.mean(), ref.std()
    z_ref[v] = (mu, sd)
    for r in "45":
        w[f"{v}_z_{r}"] = (w[f"{v}_{r}"] - mu) / sd
check("Standardisation reference = NFHS-4 neighbour border districts", True,
      "; ".join(f"{v}: mean {m:,.1f}, SD {s:,.1f}" for v, (m, s) in z_ref.items()))

w.drop(columns=["key"]).to_csv(CLEAN / "insurance_district_clean.csv", index=False)

# ---------------------------------------------------------------- 5. cost-effectiveness inputs
# Kept separate from the main audit: missing CBA inputs block only the CBA,
# never the main analysis. Every value needs a source and location to be used.
REQUIRED = ["p_rsby", "bsby_eligible_families", "bsby_claims_start", "bsby_claims_end", "bsby_coverage_share"]
OPTIONAL = ["p_bsby"]  # premium; not in the SIHFW deck, so a claims-based floor is used
ci = pd.read_csv(RAW / "cba_inputs.csv", dtype={"value": float})
cba_log = []


def cba_check(name, ok, detail=""):
    cba_log.append(f"| {'PASS' if ok else 'FLAG'} | {name} | {detail} |")


for r in ci.itertuples():
    sourced = (pd.notna(r.value) and r.value > 0 and r.status == "sourced"
               and isinstance(r.source, str) and isinstance(r.location, str))
    if r.parameter in OPTIONAL and not sourced:
        cba_log.append(f"| OPTIONAL-MISSING | {r.parameter} | {r.status} |")
        continue
    ok = sourced and (not r.unit.startswith("INR per family per year") or 100 <= r.value <= 5000) \
        and (not r.unit.startswith("share") or 0 < r.value <= 1)
    cba_check(f"input {r.parameter}", ok, f"{r.value:,.2f} {r.unit}; {r.source}, {r.location}")
missing_req = [q for q in REQUIRED if q not in set(ci.loc[ci.status == "sourced", "parameter"])]
cba_check("all required inputs sourced", not missing_req, f"missing: {missing_req}")

# BSBY claims table (SIHFW deck p.19), transcribed: internal consistency checks
cl = pd.read_csv(RAW / "bsby_claims_sihfw.csv").set_index("stage")
cba_check("claims: Pvt + Govt = Total (cases exact, amounts within Rs 0.02 cr)",
          (cl.cases_pvt + cl.cases_govt == cl.cases_total).all()
          and ((cl.amount_cr_pvt + cl.amount_cr_govt - cl.amount_cr_total).abs() <= 0.02).all())
funnel = ["enlisted", "submitted", "approved", "paid"]
cba_check("claims funnel monotone (enlisted >= submitted >= approved >= paid)",
          cl.loc[funnel, "cases_total"].is_monotonic_decreasing
          and cl.loc[funnel, "amount_cr_total"].is_monotonic_decreasing)
avg_claim = cl.loc["paid", "amount_cr_total"] * 1e7 / cl.loc["paid", "cases_total"]
cba_check("average paid claim plausible (Rs 500 - 50,000)", 500 <= avg_claim <= 50000, f"Rs {avg_claim:,.0f}")

# Derived: claims paid per eligible family per year, real 2019-21 rupees (a floor on premium cost)
v = ci.set_index("parameter")["value"]
t0 = pd.Timestamp(str(int(v["bsby_claims_start"])))
t1 = pd.Timestamp(str(int(v["bsby_claims_end"])))
years = (t1 - t0).days / 365.25
# CPI-C: FY2015-16 = 124.7, FY2016-17 = 130.3 (same chain as above); time-weighted over the claims window
fy_split = pd.Timestamp("2016-04-01")
cpi_window = (124.7 * (fy_split - t0).days + 130.3 * (t1 - fy_split).days) / (t1 - t0).days
real = CPI_BASE / cpi_window
claims_paid_yr = cl.loc["paid", "amount_cr_total"] * 1e7 / years
floor = claims_paid_yr / v["bsby_eligible_families"] * real
cba_check("derived BSBY cost per family, claims-paid floor (not the premium)", 100 <= floor <= 5000,
          f"Rs {cl.loc['paid', 'amount_cr_total']} cr over {years:.2f} yrs / {v['bsby_eligible_families']:,.0f} "
          f"families x CPI {real:.3f} = Rs {floor:,.0f} (2019-21 Rs)")
derived = pd.DataFrame([dict(parameter="p_bsby_claims_floor", value=floor,
                             unit="INR per family per year, real 2019-21",
                             source="derived from SIHFW BSBY deck p.2 and p.19",
                             location=f"claims paid Rs 295.63 cr, {t0.date()} to {t1.date()}", status="sourced")])
out_ci = pd.concat([ci.loc[ci.status == "sourced"], derived], ignore_index=True)
out_ci.to_csv(CLEAN / "cba_inputs_clean.csv", index=False)
cba_status = "PASS" if all(l.startswith(("| PASS", "| OPTIONAL")) for l in cba_log) else "INCOMPLETE"
(CHK / "cba_inputs_status.txt").write_text(cba_status + "\n")

# ---------------------------------------------------------------- audit report
md = ["# Data audit: BSBY border analysis", "",
      "Generated by `code/00_clean_and_checks.py`.", "",
      "| Result | Check | Detail |", "|---|---|---|", *log, "",
      "## Small-sample flags", "",
      "NFHS marks estimates from 25-49 unweighted cases with ( ) and suppresses <25 with *. "
      "The 641-district file strips these marks (suppressed values appear as 0 and are treated as missing). "
      "Flags survive only in the pratapvardhan file, which covers phase-1 states: of our border states, only "
      "Gujarat. In that file only OOP is ever flagged (NFHS-4: 24, NFHS-5: 14 of 341 districts). "
      f"Border-sample districts with recoverable flags: {int(b.flag_source.sum())} of {len(b)}; "
      f"flagged OOP values among them: NFHS-4 {int(b.oop_4_small.sum())}, NFHS-5 {int(b.oop_5_small.sum())}.", "",
      "## Missingness in the border sample", "", miss.to_markdown(index=False), "",
      "## Large jumps (border sample)", "", jumps.to_markdown(index=False) if len(jumps) else "None.", "",
      "## Baseline balance (NFHS-4, within-pair Rajasthan minus neighbour)", "",
      bal.round(2).to_markdown(index=False), "",
      "## Cross-source agreement detail", "", cmp.round(3).to_markdown(index=False), "",
      f"## Cost-effectiveness inputs (status: {cba_status})", "",
      "Separate from the main audit; only `code/08_cost_effectiveness.py` depends on it.", "",
      "| Result | Check | Detail |", "|---|---|---|", *cba_log]
(CHK / "data_audit.md").write_text("\n".join(md) + "\n")
status = "PASS" if all(line.startswith("| PASS") for line in log) else "FAIL"
(CHK / "audit_status.txt").write_text(status + "\n")
print(f"AUDIT STATUS: {status}   CBA INPUTS: {cba_status}")
print("\n".join(log))
print(f"\nwrote {CLEAN / 'insurance_district_clean.csv'} and {CHK / 'data_audit.md'}")
