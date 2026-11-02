"""Tier 1 cost-effectiveness and tier 2 break-even for BSBY.

Incremental cost-effectiveness ratio (Drummond et al.; Boardman et al.;
Dhaliwal, Duflo, Glennerster & Tulloch 2013): incremental cost / incremental effect.

    cost per additionally insured household per year
        = (cost_per_family * s_BSBY  -  p_RSBY * c_cf) / beta

  beta             coverage effect from the border-pair DiD (share of households)
  s_BSBY           share of households covered by BSBY = 0.67 (SIHFW deck p.17:
                   "Covering 67% of Population"; population share used as household share)
  cost_per_family  BSBY cost per covered family per year. The premium is not public,
                   so this is a FLOOR: claims paid per eligible family per year
                   (SIHFW deck p.19: Rs 295.63 cr, 13 Dec 2015 - 10 Feb 2017;
                   p.2: ~1 crore families) = Rs 297 in 2019-21 rupees
  c_cf             counterfactual coverage = c_Raj - beta, c_Raj = NFHS-5 coverage
                   in Rajasthan border districts (any insurance, pair-weighted)
  p_RSBY           counterfactual cost per family; 0 in the main specification

Spending = cost per covered family x covered families; households cancel.

Main specification:
  - s_BSBY = 0.67, not c_Raj = 0.875: c_Raj counts any insurance (employee
    schemes, private), but only BSBY families cost BSBY money. c_Raj is kept as a
    sensitivity (it overstates spending).
  - p_RSBY = 0: Rajasthan "was still in the early stages of rolling-out RSBY as
    of September 2016" (Karan et al. 2017, p.84); offsetting a claims floor with
    a full premium would also mix concepts.
Remaining biases mostly push the true cost ABOVE the main estimate (claims < premium,
launch-year ramp-up), so it is a lower bound.

Break-even (tier 2): the annual benefit per additionally insured household
needed to justify the cost equals the ratio itself.
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
cba_status = (CHK / "cba_inputs_status.txt").read_text().strip()
assert cba_status == "PASS", "Cost-effectiveness inputs must PASS the checks in 00_clean_and_checks.py."

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
B0 = BETAS["main (+52.8 pp)"]

# Rajasthan border coverage in NFHS-5 (any insurance), weighted as in the regression
w = pd.read_csv(CLEAN / "insurance_district_clean.csv")
pairs = pd.read_csv(CLEAN / "border_pairs.csv")
nb_ok = w.dropna(subset=["insur_4", "insur_5"])[["ST_CEN_CD", "dt"]]
usable = pairs.merge(nb_ok, left_on=["nb_st", "nb_dt"], right_on=["ST_CEN_CD", "dt"])
raj = usable.merge(w, left_on=["raj_st", "raj_dt"], right_on=["ST_CEN_CD", "dt"])
c_raj = raj["insur_5"].mean() / 100

inputs = pd.read_csv(CLEAN / "cba_inputs_clean.csv").set_index("parameter")["value"]
p_rsby = inputs["p_rsby"]
s_bsby = inputs["bsby_coverage_share"]
p_bsby = inputs.get("p_bsby", np.nan)  # actual premium, if ever sourced
cost_pf = p_bsby if not np.isnan(p_bsby) else inputs["p_bsby_claims_floor"]
cost_label = "BSBY premium" if not np.isnan(p_bsby) else "BSBY cost per family (claims-paid floor)"


def cer(cost, share, pr, beta):
    """Cost per additionally insured household per year."""
    return (cost * share - pr * (c_raj - beta)) / beta


rows = []
for lab, b in BETAS.items():
    rows.append(dict(spec="main", beta_case=lab, beta=round(b, 3), covered_share=s_bsby, p_rsby_offset=0,
                     cost_per_add_household=cer(cost_pf, s_bsby, 0.0, b)))
rows.append(dict(spec="sensitivity: any-insurance share c_Raj (overstates spending)", beta_case="main (+52.8 pp)",
                 beta=round(B0, 3), covered_share=round(c_raj, 3), p_rsby_offset=0,
                 cost_per_add_household=cer(cost_pf, c_raj, 0.0, B0)))
rows.append(dict(spec="sensitivity: full RSBY premium offset (mixes claims floor with premium)",
                 beta_case="main (+52.8 pp)", beta=round(B0, 3), covered_share=s_bsby, p_rsby_offset=p_rsby,
                 cost_per_add_household=cer(cost_pf, s_bsby, p_rsby, B0)))
tab = pd.DataFrame(rows)
tab.to_csv(OUT / "cost_effectiveness.csv", index=False)

main_cer = cer(cost_pf, s_bsby, 0.0, B0)
lines = [
    f"Inputs: {cost_label} = Rs {cost_pf:,.0f} per family per year (2019-21 Rs; SIHFW deck pp.2, 19); "
    f"BSBY covered share = {s_bsby:.2f} (SIHFW deck p.17); NFHS-5 any-insurance coverage c_Raj = {c_raj:.3f}; "
    f"counterfactual coverage c_cf = {c_raj - B0:.3f}; p_RSBY = 0 main / {p_rsby:,.0f} sensitivity "
    "(Karan et al. 2017, p.84 and Table 1).",
    "",
    "General form (main beta, p_RSBY = 0): cost per additionally insured household = "
    f"{s_bsby / B0:.2f} x BSBY cost per family.",
    "",
    tab.round(1).to_string(index=False),
    "",
    f"MAIN: about Rs {main_cer:,.0f} per additionally insured household per year (2019-21 Rs), a LOWER BOUND; "
    f"Rs {cer(cost_pf, s_bsby, 0, BETAS['95% CI high']):,.0f}-{cer(cost_pf, s_bsby, 0, BETAS['95% CI low']):,.0f} "
    f"over the 95% CI of beta; Rs {cer(cost_pf, s_bsby, 0, BETAS['MP border only (conservative)']):,.0f} "
    "with the MP-only beta.",
    f"Share of BSBY spending on households that would have been insured anyway: (s_BSBY - beta) / s_BSBY = "
    f"({s_bsby:.2f} - {B0:.3f}) / {s_bsby:.2f} = {(s_bsby - B0) / s_bsby:.0%}.",
    f"BREAK-EVEN (tier 2): an additionally insured household must gain at least about Rs {main_cer:,.0f} a year.",
    "Bias directions: claims < premium and launch-year ramp-up -> true cost higher (main is a lower bound); "
    "some counterfactual RSBY spending -> slightly lower.",
]
text = "\n".join(lines)
print(text)
(OUT / "cost_effectiveness.txt").write_text(text + "\n")

# Figure: cost per additionally insured household against cost per family
pb = np.linspace(0, 2000, 101)
fig, ax = plt.subplots(figsize=(6, 4))
lo, hi = BETAS["95% CI low"], BETAS["95% CI high"]
ax.fill_between(pb, cer(pb, s_bsby, 0.0, hi), cer(pb, s_bsby, 0.0, lo), color="#c0504d", alpha=0.15,
                label="95% CI of beta")
ax.plot(pb, cer(pb, s_bsby, 0.0, B0), color="#c0504d", lw=2, label=f"Main: beta 0.528, BSBY share {s_bsby:.2f}")
ax.plot(pb, cer(pb, s_bsby, 0.0, BETAS["MP border only (conservative)"]), color="#1f4e79", lw=1.5, ls="--",
        label="MP-only beta (0.454)")
ax.plot(pb, cer(pb, c_raj, 0.0, B0), color="#999999", lw=1, ls=":",
        label=f"Sensitivity: any-insurance share {c_raj:.2f}")
ax.axvline(cost_pf, color="black", lw=0.8)
ax.plot([cost_pf], [main_cer], "ko", ms=5)
ax.annotate(f"Claims-paid floor\nRs {cost_pf:,.0f}/family/yr\n-> Rs {main_cer:,.0f} per added household",
            xy=(cost_pf, main_cer), xytext=(cost_pf + 750, 150), fontsize=7,
            arrowprops=dict(arrowstyle="-", lw=0.6))
ax.axhline(0, color="black", lw=0.6)
ax.set_xlabel("BSBY cost per covered family per year (Rs, 2019-21)")
ax.set_ylabel("Cost per additionally insured household (Rs/yr)")
ax.set_title("Cost per additionally insured household (border districts)")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "fig_cost_effectiveness.png", dpi=200)
