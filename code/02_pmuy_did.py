"""PMUY (launched May 2016) intensity DiD at district level.

NFHS-4 (2015-16) is pre-PMUY; NFHS-5 (2019-21) is after ~8 crore connections.
Districts with low clean-fuel use in NFHS-4 had more PMUY-eligible households,
so they had more exposure. Two periods, so DiD with district FE = first differences:

  First stage:   d_clean_fuel_i = b * exposure_i + X_i'c + state FE + e_i
  Reduced form:  d_y_i          = g * exposure_i + X_i'c + state FE + e_i
  2SLS:          d_y_i          = t * d_clean_fuel_i + X_i'c + state FE + e_i
                 (exposure instruments d_clean_fuel)

  exposure_i = 100 - clean_fuel_nfhs4_i
  X_i        = NFHS-4 baseline electricity, sanitation, water, women's schooling
               and the baseline level of the outcome (absorbs mean reversion)

Placebo: institutional births should not respond to cooking fuel. If exposure
"predicts" them, exposure is picking up general catch-up, not PMUY.
SEs clustered by state.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.iv import IV2SLS

# Usage: python code/02_pmuy_did.py [STATE]   e.g. Rajasthan; omit for all-India
STATE = sys.argv[1] if len(sys.argv) > 1 else None
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / (STATE.lower().replace(" ", "_") if STATE else "all_india")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "data" / "clean" / "district_panel.csv")
if STATE:
    df = df[df["State"] == STATE].reset_index(drop=True)
    assert len(df), f"no districts for {STATE}"
# Single state: no state FE, heteroskedasticity-robust HC3 SEs (small-sample safe).
# All-India: state FE, SEs clustered by state.
FE = "" if STATE else " + C(State)"
FE_LABEL = "no FE (single state)" if STATE else "state FE"
df["exposure"] = 100 - df["clean_fuel_nfhs4"]
OUTCOMES = ["child_ari", "child_stunted", "child_underweight", "child_anaemic", "women_anaemic_np"]
PLACEBO = ["inst_births"]
for v in ["clean_fuel"] + OUTCOMES + PLACEBO:
    df[f"d_{v}"] = df[f"{v}_nfhs5"] - df[f"{v}_nfhs4"]

BASE = "electricity_nfhs4 + sanitation_nfhs4 + water_nfhs4 + women_school10_nfhs4"


def ols(formula, data):
    m = smf.ols(formula, data).fit()  # fit once to learn which rows survive NA drop
    sub = data.loc[m.model.data.row_labels]
    if STATE:
        return smf.ols(formula, sub).fit(cov_type="HC3")
    return smf.ols(formula, sub).fit(cov_type="cluster", cov_kwds={"groups": sub["State"]})


rows = []


def record(model, spec, m, term):
    rows.append(dict(model=model, spec=spec, term=term, coef=m.params[term],
                     se=m.bse[term], p=m.pvalues[term], n=int(m.nobs)))


# First stage
record("first_stage", FE_LABEL, ols(f"d_clean_fuel ~ exposure{FE}", df), "exposure")
fs = ols(f"d_clean_fuel ~ exposure + {BASE}{FE}", df)
record("first_stage", f"{FE_LABEL} + baseline controls", fs, "exposure")
# The raw scatter is hump-shaped: check curvature
df["exposure_sq"] = df["exposure"] ** 2 / 100
q = ols(f"d_clean_fuel ~ exposure + exposure_sq + {BASE}{FE}", df)
record("first_stage_quadratic", f"{FE_LABEL} + baseline controls", q, "exposure")
record("first_stage_quadratic", f"{FE_LABEL} + baseline controls", q, "exposure_sq")

# Reduced forms, 2SLS, placebo
for y in OUTCOMES + PLACEBO:
    ctrl = f"{BASE} + {y}_nfhs4"
    m = ols(f"d_{y} ~ exposure + {ctrl}{FE}", df)
    record(f"reduced_form_{y}", "controls + baseline outcome", m, "exposure")

    sub = df.dropna(subset=[f"d_{y}", "d_clean_fuel", "exposure", f"{y}_nfhs4",
                            "electricity_nfhs4", "sanitation_nfhs4", "water_nfhs4", "women_school10_nfhs4"])
    iv = IV2SLS.from_formula(f"d_{y} ~ 1 + {ctrl}{FE} + [d_clean_fuel ~ exposure]", sub)
    iv = iv.fit(cov_type="robust") if STATE else iv.fit(
        cov_type="clustered", clusters=sub["State"].astype("category").cat.codes)
    rows.append(dict(model=f"2sls_{y}", spec="controls + baseline outcome", term="d_clean_fuel",
                     coef=iv.params["d_clean_fuel"], se=iv.std_errors["d_clean_fuel"],
                     p=iv.pvalues["d_clean_fuel"], n=int(iv.nobs)))

res = pd.DataFrame(rows)
res.to_csv(OUT / "pmuy_results.csv", index=False)
print(f"[{STATE or 'All India'}] {len(df)} districts")
print(f"First-stage F (robust) ~ t^2 = {(fs.params['exposure'] / fs.bse['exposure']) ** 2:.1f}")
print(res.round(4).to_string(index=False))

# Figure: binned scatter of first stage
df["bin"] = pd.qcut(df["exposure"], 10 if STATE else 20, labels=False)  # deciles for one state
b = df.groupby("bin")[["exposure", "d_clean_fuel"]].mean()
fig, ax = plt.subplots(figsize=(6, 4))
ax.scatter(df["exposure"], df["d_clean_fuel"], s=6, alpha=0.25, color="#9aa7b8", label="District")
ax.scatter(b["exposure"], b["d_clean_fuel"], s=30, color="#1f4e79", label="Bin mean")
slope, icpt = np.polyfit(df["exposure"], df["d_clean_fuel"], 1)
xs = np.linspace(df["exposure"].min(), df["exposure"].max(), 50)
ax.plot(xs, icpt + slope * xs, color="#c0504d", lw=1.5, label=f"raw OLS slope {slope:.2f} (no state FE)")
ax.set_xlabel("PMUY exposure: % households NOT using clean fuel, NFHS-4 (2015-16)")
ax.set_ylabel("Change in clean-fuel use, pp (NFHS-5 − NFHS-4)")
ax.set_title(f"First stage, {STATE or 'India'}: PMUY exposure and LPG uptake ({len(df)} districts)")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "fig_first_stage.png", dpi=200)
