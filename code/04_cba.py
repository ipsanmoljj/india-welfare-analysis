"""Welfare / cost-benefit analysis of PMUY per beneficiary household.

Links the DiD to welfare in two ways:
  A. Conversion rate: how many PMUY connections turned into households that
     report clean fuel as their MAIN cooking fuel (from the first stage).
  B. Per-household social CBA and MVPF over a 10-year horizon, with the health
     benefit left as a break-even value because the DiD finds no detectable
     health effect at district level.

Every parameter has a source and a confidence tag. VERIFY items marked
[Likely]/[Guessing] against the cited source before submission.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

P = {
    # Costs
    "connection_cost": 1600,     # Rs, GoI assistance per 14.2kg connection, Phase I. pmuy.gov.in [Certain]
    "stove_cost": 1000,          # Rs, one-time stove; beneficiary-financed in Phase I [Guessing]
    "lpg_resource_cost": 850,    # Rs per 14.2kg cylinder, unsubsidised retail price (Delhi, 2025) [Likely]
    "refill_subsidy": 300,       # Rs per cylinder targeted PMUY subsidy from Oct 2023 [Likely]
    "refills_per_year": 3.95,    # PMUY per-capita refills FY2023-24, Rajya Sabha reply Feb 2025 [Certain]
    "full_use_refills": 7.0,     # cylinders/yr for a household cooking only on LPG [Guessing]
    # Benefits
    "collection_hours": 660,     # hrs/yr household firewood collection, traditional stove (Practical Action 2015) [Likely]
    "rural_wage_day": 300,       # Rs/day rural casual wage, women [Guessing; check PLFS / Labour Bureau]
    "time_value_share": 0.5,     # value non-market time at 50% of market wage (standard CBA convention)
    # Evaluation
    "horizon": 10,
    "discount": 0.08,
}
# Programme scale for the conversion-rate calculation
CONNECTIONS_BY_NFHS5 = 8.0e7     # 8 crore connections by Sept 2019 (MoPNG) [Certain]
HOUSEHOLDS_INDIA = 2.9e8         # ~29 crore households c. 2020 [Likely]


def pv(flow, r, T):
    return sum(flow / (1 + r) ** t for t in range(1, T + 1))


def cba(p, health=0.0):
    share = min(p["refills_per_year"] / p["full_use_refills"], 1.0)
    hourly = p["rural_wage_day"] / 8 * p["time_value_share"]
    time_benefit = p["collection_hours"] * share * hourly
    lpg_cost = p["refills_per_year"] * p["lpg_resource_cost"]
    oop = p["refills_per_year"] * (p["lpg_resource_cost"] - p["refill_subsidy"])
    r, T = p["discount"], p["horizon"]
    social_npv = pv(time_benefit + health - lpg_cost, r, T) - p["connection_cost"] - p["stove_cost"]
    gov_cost = p["connection_cost"] + pv(p["refills_per_year"] * p["refill_subsidy"], r, T)
    # Beneficiary WTP for the programme = what they gain net of what they pay
    private_gain = pv(time_benefit + health - oop, r, T) - p["stove_cost"]
    return dict(
        displaced_share=share, time_benefit_yr=time_benefit, lpg_cost_yr=lpg_cost,
        social_npv=social_npv, gov_cost_pv=gov_cost, private_gain_pv=private_gain,
        mvpf=private_gain / gov_cost,
        breakeven_health_yr=max(0.0, -social_npv) / pv(1, r, T),
    )


# A. Conversion rate from the first stage
res = pd.read_csv(OUT / "pmuy_results.csv")
b = res.query("model == 'first_stage' and spec == 'state FE + baseline controls'")["coef"].iloc[0]
panel = pd.read_csv(ROOT / "data" / "clean" / "district_panel.csv")
mean_exposure = (100 - panel["clean_fuel_nfhs4"]).mean()
# Strong assumption: a district with zero exposure gets zero PMUY effect
effect_pp = b * mean_exposure
switchers = effect_pp / 100 * HOUSEHOLDS_INDIA
conversion = switchers / CONNECTIONS_BY_NFHS5

# B. CBA
base = cba(P)
lines = [
    "A. CONVERSION (from DiD first stage)",
    f"  first-stage slope b                  = {b:.3f}",
    f"  mean district exposure (NFHS-4)      = {mean_exposure:.1f}% not on clean fuel",
    f"  implied PMUY effect on clean-fuel use= {effect_pp:.1f} pp of households",
    f"  implied switchers                    = {switchers / 1e7:.2f} crore households",
    f"  conversion rate (switchers/connections) = {conversion:.0%}",
    f"  connection cost per effective switcher  = Rs {P['connection_cost'] / conversion:,.0f}",
    "",
    "B. PER-HOUSEHOLD CBA, base case (health benefit = 0, as the DiD finds)",
] + [f"  {k:22s} = {v:,.2f}" for k, v in base.items()]

# Sensitivity
grid = []
for vt in [0.25, 0.5, 1.0]:
    for R in [2, 3, 3.95, 5, 7]:
        q = dict(P, time_value_share=vt, refills_per_year=R)
        out = cba(q)
        grid.append(dict(time_value_share=vt, refills=R, **out))
sens = pd.DataFrame(grid)
sens.to_csv(OUT / "cba_sensitivity.csv", index=False)
lines += ["", "C. SENSITIVITY (social NPV, Rs per household)",
          sens.pivot(index="refills", columns="time_value_share", values="social_npv").round(0).to_string()]
text = "\n".join(lines)
print(text)
(OUT / "cba_summary.txt").write_text(text + "\n")
pd.Series(P).to_csv(OUT / "cba_parameters.csv", header=["value"])

# Figure: social NPV vs refills for three time valuations
fig, ax = plt.subplots(figsize=(6, 4))
Rs = np.linspace(1, 7, 61)
for vt, c in zip([0.25, 0.5, 1.0], ["#9aa7b8", "#1f4e79", "#c0504d"]):
    ax.plot(Rs, [cba(dict(P, time_value_share=vt, refills_per_year=R))["social_npv"] for R in Rs],
            color=c, label=f"time valued at {int(vt * 100)}% of wage")
ax.axhline(0, color="black", lw=0.8)
ax.axvline(P["refills_per_year"], color="grey", ls="--", lw=0.8)
ax.text(P["refills_per_year"] + 0.05, ax.get_ylim()[1] * 0.9, "actual FY24\n(3.95)", fontsize=8)
ax.set_xlabel("Refills per household per year")
ax.set_ylabel("Social NPV per household (Rs, 10 yrs, 8%)")
ax.set_title("PMUY social NPV: refills and value of time")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "fig_cba_sensitivity.png", dpi=200)
