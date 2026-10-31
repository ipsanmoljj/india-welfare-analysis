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
  output/checks/data_audit.md               pass/fail log of every check
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
n6 = pd.read_csv(CLEAN / "nfhs6_rajasthan_districts.csv")
n6["key"] = "rajast" + n6["district"].replace({"Chittorgarh": "Chittaurgarh", "Dholpur": "Dhaulpur",
                                                "Jalore": "Jalor"}).map(norm)
m6 = w.merge(n6, on="key", suffixes=("", "_n6"))
diffs = {v: (m6[f"{v}_5"] - m6[f"{v}_5_n6"]).abs().max() for v in ["insur", "inst", "inst_public", "electricity"]}
check("Cross-source: Kalla NFHS-5 vs NFHS-6 compendium (Rajasthan)", len(m6) == 33 and max(diffs.values()) < 0.05,
      f"{len(m6)}/33 districts matched; max abs diff {diffs}")

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
      "## Cross-source agreement detail", "", cmp.round(3).to_markdown(index=False)]
(CHK / "data_audit.md").write_text("\n".join(md) + "\n")
print("\n".join(log))
print(f"\nwrote {CLEAN / 'insurance_district_clean.csv'} and {CHK / 'data_audit.md'}")
