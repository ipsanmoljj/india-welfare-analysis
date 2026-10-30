"""Bihar alcohol prohibition (April 2016): state-level DiD, NFHS-4 vs NFHS-5.

One treated state, so conventional SEs are meaningless. Inference is by
permutation: assign "treatment" to each control state in turn and see where
Bihar's change ranks.

Outcome: ever-married women 18-49 who ever experienced spousal violence (%),
which the NFHS-5 factsheet reports on the same definition for both rounds.
Alcohol use is NOT comparable across rounds (NFHS-4: men 15-49, NFHS-5: men 15+).
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "clean" / "state_panel.csv")

# States/UTs with their own prohibition regimes are not valid controls
DROP = ["Gujarat", "Mizoram", "Nagaland", "India"]
df = df[~df["state"].str.contains("|".join(DROP), case=False)]
df = df.dropna(subset=["spousal_violence_nfhs4", "spousal_violence_nfhs5"])
df["d_sv"] = df["spousal_violence_nfhs5"] - df["spousal_violence_nfhs4"]

is_bihar = df["state"].str.startswith("Bihar")
bihar = df.loc[is_bihar, "d_sv"].iloc[0]
did = bihar - df.loc[~is_bihar, "d_sv"].mean()

# Permutation: DiD estimate if each state were the treated one
perm = [(r.d_sv - df.loc[df.index != i, "d_sv"].mean()) for i, r in df.iterrows()]
p = sum(abs(x) >= abs(did) for x in perm) / len(perm)

print(f"Bihar change in spousal violence: {bihar:+.1f} pp")
print(f"Control mean change:              {df.loc[~is_bihar, 'd_sv'].mean():+.1f} pp")
print(f"DiD estimate:                     {did:+.1f} pp")
print(f"Permutation p-value (two-sided):  {p:.3f}  (n states = {len(df)})")
(ROOT / "output").mkdir(exist_ok=True)
df[["state", "spousal_violence_nfhs4", "spousal_violence_nfhs5", "d_sv"]].sort_values("d_sv").to_csv(
    ROOT / "output" / "bihar_state_changes.csv", index=False
)
