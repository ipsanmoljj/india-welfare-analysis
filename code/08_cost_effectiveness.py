"""Tier 1 cost-effectiveness and tier 2 break-even for BSBY.

Incremental cost-effectiveness ratio (Drummond et al.; Boardman et al.;
Dhaliwal, Duflo, Glennerster & Tulloch 2013): incremental cost / incremental effect.

    cost per additionally insured household per year
        = (p_BSBY * c_Raj  -  p_RSBY * c_cf) / beta

  beta   coverage effect from the border-pair DiD (share of households)
  c_Raj  NFHS-5 coverage in Rajasthan border districts (pair-weighted, as in beta)
  c_cf   counterfactual coverage = c_Raj - beta
  p_*    annual premium per family; spending = premium x covered families

Households cancel, so no population counts are needed. Assumes the NFHS
"any member insured" share approximates scheme enrolment (it also counts
other insurance, so c_Raj overstates BSBY enrolment and the ratio is an upper bound).

Break-even (tier 2): the annual benefit per additionally insured household
needed to justify the cost equals the ratio itself.

Inputs: cleaned results and data only; data/clean/cba_inputs_clean.csv holds
only sourced parameters. Without a sourced BSBY premium the script reports the
ratio as a function of the premium instead of a single number.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CHK, CLEAN, RES = ROOT / "output" / "checks", ROOT / "data" / "clean", ROOT / "output" / "insurance"
OUT = ROOT / "output" / "cba"
OUT.mkdir(parents=True, exist_ok=True)
assert (CHK / "audit_status.txt").read_text().strip() == "PASS", "Data audit must PASS first."

# Effects from the cleaned border-pair DiD
main = pd.read_csv(RES / "border_pair_did_main.csv").set_index("outcome").loc["insur"]
rob = pd.read_csv(RES / "border_pair_did.csv")
mp = rob[rob["sample"].str.startswith("MP") & (rob.outcome == "insur")].iloc[0]
BETAS = {
    "main (+52.8 pp)": main.beta / 100,
    "95% CI low": (main.beta - 1.96 * main.se) / 100,
    "95% CI high": (main.beta + 1.96 * main.se) / 100,
    "MP border only (conservative)": mp.beta / 100,
}

# Rajasthan border coverage in NFHS-5, weighted as in the regression (once per usable pair)
w = pd.read_csv(CLEAN / "insurance_district_clean.csv")
pairs = pd.read_csv(CLEAN / "border_pairs.csv")
nb_ok = w.dropna(subset=["insur_4", "insur_5"])[["ST_CEN_CD", "dt"]]
usable = pairs.merge(nb_ok, left_on=["nb_st", "nb_dt"], right_on=["ST_CEN_CD", "dt"])
raj = usable.merge(w, left_on=["raj_st", "raj_dt"], right_on=["ST_CEN_CD", "dt"])
c_raj = raj["insur_5"].mean() / 100

inputs = pd.read_csv(CLEAN / "cba_inputs_clean.csv").set_index("parameter")["value"]
p_rsby = inputs.get("p_rsby", np.nan)
p_bsby = inputs.get("p_bsby", np.nan)
cba_status = (CHK / "cba_inputs_status.txt").read_text().strip()


def cer(pb, pr, beta):
    return (pb * c_raj - pr * (c_raj - beta)) / beta


lines = [f"Inputs: c_Raj = {c_raj:.3f} (NFHS-5, {raj.pair_id.nunique()} pairs), "
         f"p_RSBY = {p_rsby:,.0f} (Karan et al. 2017, Table 1), p_BSBY = "
         f"{'not sourced' if np.isnan(p_bsby) else f'{p_bsby:,.0f}'}", ""]

# The ratio as a linear function of the BSBY premium: CER = a * p_BSBY - b
lines.append("Cost per additionally insured household per year as a function of the BSBY premium:")
for lab, b in BETAS.items():
    for pr_lab, pr in [("p_RSBY = 560", p_rsby), ("p_RSBY = 0 (upper bound)", 0.0)]:
        slope = c_raj / b
        icpt = pr * (c_raj - b) / b
        lines.append(f"  beta {lab:32s} {pr_lab:26s}: CER = {slope:.2f} x p_BSBY - {icpt:,.0f}")
lines.append("  Reading: each Rs 1 of BSBY premium per family costs about Rs "
             f"{c_raj / BETAS['main (+52.8 pp)']:.2f} per additionally insured household.")

if cba_status == "PASS" and not np.isnan(p_bsby):
    lines += ["", "COST-EFFECTIVENESS (sourced inputs):"]
    rows = [dict(beta_case=lab, beta=b, p_rsby=pr, cer=cer(p_bsby, pr, b))
            for lab, b in BETAS.items() for pr in (p_rsby, 0.0)]
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "cost_effectiveness.csv", index=False)
    lines.append(tab.round(3).to_string(index=False))
    lines.append(f"Break-even: an additionally insured household must gain about Rs "
                 f"{cer(p_bsby, p_rsby, BETAS['main (+52.8 pp)']):,.0f} a year for benefits to cover costs.")
else:
    lines += ["", f"CBA inputs status: {cba_status}. No single cost figure is reported until a sourced",
              "BSBY premium is added to data/raw/cba_inputs.csv and passes code/00_clean_and_checks.py."]

text = "\n".join(lines)
print(text)
(OUT / "cost_effectiveness.txt").write_text(text + "\n")

# Figure: the ratio as a function of the premium (no invented premium value)
pb = np.linspace(0, 2000, 101)
fig, ax = plt.subplots(figsize=(6, 4))
lo, hi = BETAS["95% CI low"], BETAS["95% CI high"]
ax.fill_between(pb, cer(pb, p_rsby, hi), cer(pb, p_rsby, lo), color="#c0504d", alpha=0.15,
                label="95% CI of beta")
ax.plot(pb, cer(pb, p_rsby, BETAS["main (+52.8 pp)"]), color="#c0504d", lw=2, label="Main beta (0.528)")
ax.plot(pb, cer(pb, p_rsby, BETAS["MP border only (conservative)"]), color="#1f4e79", lw=1.5, ls="--",
        label="MP-only beta (0.454)")
if not np.isnan(p_bsby):
    ax.axvline(p_bsby, color="black", lw=0.8)
    ax.text(p_bsby, ax.get_ylim()[1] * 0.95, f" sourced BSBY premium\n Rs {p_bsby:,.0f}", fontsize=7, va="top")
ax.axhline(0, color="black", lw=0.6)
ax.set_xlabel("BSBY premium per family per year (Rs)")
ax.set_ylabel("Cost per additionally insured household (Rs/yr)")
ax.set_title("Cost-effectiveness as a function of the BSBY premium\n(RSBY counterfactual premium Rs 560)")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "fig_cost_effectiveness.png", dpi=200)
