"""PMUY (launched May 2016) intensity DiD at district level.

Idea: districts with low clean-fuel use in NFHS-4 had more PMUY-eligible
households, so they had more exposure to the scheme. Two periods, so the DiD
with district fixed effects is the first-difference regression:

  (1) d_clean_fuel_i = a + b * exposure_i + state FE + e_i
      exposure_i = 100 - clean_fuel_nfhs4_i   (% not using clean fuel at baseline)
  (2) d_health_i  = a + g * exposure_i + state FE + e_i       (reduced form)
  (3) d_health_i  = a + t * d_clean_fuel_i + state FE + e_i   (2SLS, (1) as first stage)

State FE soak up state-wide shocks (state LPG drives, NFHS timing, COVID phase).
Caveat: low-baseline districts may catch up anyway (mean reversion) -- check
robustness by controlling for baseline electricity and sanitation.
"""
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

df = pd.read_csv(ROOT / "data" / "clean" / "district_panel.csv")
df["exposure"] = 100 - df["clean_fuel_nfhs4"]
for v in ["clean_fuel", "child_ari", "child_stunted", "child_anaemic", "women_anaemic_np"]:
    df[f"d_{v}"] = df[f"{v}_nfhs5"] - df[f"{v}_nfhs4"]


def fit(formula, data):
    data = data.dropna(subset=[c for c in data.columns if c in formula])
    return smf.ols(formula, data).fit(cov_type="cluster", cov_kwds={"groups": data["State"]})


rows = []
specs = {
    "first_stage": "d_clean_fuel ~ exposure + C(State)",
    "first_stage_controls": "d_clean_fuel ~ exposure + electricity_nfhs4 + sanitation_nfhs4 + C(State)",
}
for name, f in specs.items():
    m = fit(f, df)
    rows.append((name, "exposure", m.params["exposure"], m.bse["exposure"], m.pvalues["exposure"], int(m.nobs)))

for y in ["d_child_ari", "d_child_stunted", "d_child_anaemic", "d_women_anaemic_np"]:
    m = fit(f"{y} ~ exposure + C(State)", df)
    rows.append((f"reduced_form_{y}", "exposure", m.params["exposure"], m.bse["exposure"], m.pvalues["exposure"], int(m.nobs)))

res = pd.DataFrame(rows, columns=["model", "term", "coef", "se_cluster_state", "p", "n"])
res.to_csv(OUT / "pmuy_results.csv", index=False)
print(res.round(4).to_string(index=False))

# Simple 2SLS by hand: ratio of reduced form to first stage (Wald / indirect least squares).
# SEs from this are not valid -- use linearmodels.IV2SLS for the write-up if needed.
fs = res.set_index("model").loc["first_stage", "coef"]
for y in ["d_child_ari", "d_child_stunted", "d_child_anaemic", "d_women_anaemic_np"]:
    rf = res.set_index("model").loc[f"reduced_form_{y}", "coef"]
    print(f"IV effect of +1 pp clean fuel on {y}: {rf / fs:.3f} pp")
