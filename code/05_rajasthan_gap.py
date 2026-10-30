"""Did Rajasthan lag the rest of India in PMUY-era clean-fuel adoption?

The within-Rajasthan intensity DiD has no first stage (33 districts, gains are
flat across exposure), so Rajasthan is compared against districts elsewhere with
the same baseline exposure and characteristics:

  d_clean_fuel_i = a + d * Rajasthan_i + f(exposure_i) + X_i'c + e_i

d < 0 means Rajasthan districts gained less than comparable districts elsewhere.
Inference: SEs clustered by state, plus a permutation test that gives every
other state the "Rajasthan" dummy in turn.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "rajasthan"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "data" / "clean" / "district_panel.csv")
df["exposure"] = 100 - df["clean_fuel_nfhs4"]
df["exposure_sq"] = df["exposure"] ** 2 / 100
df["d_clean_fuel"] = df["clean_fuel_nfhs5"] - df["clean_fuel_nfhs4"]
df = df.dropna(subset=["d_clean_fuel", "electricity_nfhs4", "sanitation_nfhs4",
                       "water_nfhs4", "women_school10_nfhs4"]).reset_index(drop=True)
X = "exposure + exposure_sq + electricity_nfhs4 + sanitation_nfhs4 + water_nfhs4 + women_school10_nfhs4"


def gap(state):
    d = df.assign(treat=(df["State"] == state).astype(int))
    return smf.ols(f"d_clean_fuel ~ treat + {X}", d).fit(cov_type="cluster", cov_kwds={"groups": d["State"]})


m = gap("Rajasthan")
d_raj = m.params["treat"]

# Permutation over states with at least 5 districts
big = df["State"].value_counts()
big = big[big >= 5].index
perm = pd.Series({s: gap(s).params["treat"] for s in big}).sort_values()
rank = (perm <= d_raj).sum()
p_perm = (perm.abs() >= abs(d_raj)).mean()

raj = df[df["State"] == "Rajasthan"]
lines = [
    f"Rajasthan districts: {len(raj)}",
    f"Mean change in clean-fuel use: Rajasthan {raj.d_clean_fuel.mean():+.1f} pp, "
    f"rest of India {df.loc[df.State != 'Rajasthan', 'd_clean_fuel'].mean():+.1f} pp",
    f"Conditional gap (Rajasthan vs comparable districts): {d_raj:+.2f} pp "
    f"(cluster SE {m.bse['treat']:.2f}, p = {m.pvalues['treat']:.3f})",
    f"Permutation: Rajasthan ranks {rank} of {len(perm)} states (1 = largest shortfall); "
    f"two-sided permutation p = {p_perm:.2f}",
    "",
    "State gaps (pp, same specification):",
    perm.round(2).to_string(),
]
text = "\n".join(lines)
print(text)
(OUT / "rajasthan_gap.txt").write_text(text + "\n")
perm.rename("gap_pp").to_csv(OUT / "state_gaps.csv")

# Figure: state gaps, Rajasthan highlighted
fig, ax = plt.subplots(figsize=(6, 5))
colors = ["#c0504d" if s == "Rajasthan" else "#9aa7b8" for s in perm.index]
ax.barh(perm.index, perm.values, color=colors)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Gain in clean-fuel use vs comparable districts elsewhere (pp)")
ax.set_title("Which states lagged in PMUY-era LPG adoption?")
ax.tick_params(axis="y", labelsize=7)
fig.tight_layout()
fig.savefig(OUT / "fig_state_gaps.png", dpi=200)
