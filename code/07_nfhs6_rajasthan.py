"""Extract NFHS-6 (2023-24, provisional) Rajasthan district fact sheets.

Source: data/raw/NFHS-6_StateFact_Rajasthan__Rajasthan Compendium.pdf (IIPS, Aug 2026).
Fieldwork in Rajasthan: 28 May 2023 - 1 Jan 2024. Districts are the 33 pre-2023
districts, so they line up with NFHS-4/5. Each district sheet reports
NFHS-6 and NFHS-5 side by side.

Neighbouring states' NFHS-6 compendiums are not in the repo, so this is a
Rajasthan-only persistence check, not a border DiD. NFHS-6 drops the
out-of-pocket-per-delivery indicator.

Output: data/interim/nfhs6_rajasthan_extracted.csv (validated by 00_clean_and_checks.py)
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "NFHS-6_StateFact_Rajasthan__Rajasthan Compendium.pdf"
text = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True).stdout

# District order as in the compendium's table of contents (pages 9-137)
toc = re.findall(r"^\s+\d+\.\s+([A-Z][A-Za-z ]+?)\s{2,}\d+\s*$", text.split("Appendix")[0], flags=re.M)
assert len(toc) == 33, toc

INDICATORS = {
    "7": ("Households with any usual member covered under a health insurance", "insur"),
    "35": ("Institutional births (%)", "inst"),
    "36": ("Institutional births in public facility (%)", "inst_public"),
    "4": ("Population living in households with electricity (%)", "electricity"),
}
rows = {}
for num, (label, var) in INDICATORS.items():
    vals = []
    for line in text.splitlines():
        if re.match(rf"^\s*{num}\.\s+{re.escape(label)}", line):
            nums = re.findall(r"\d+\.\d+|\d+", line[line.index(label) + len(label):])
            vals.append([float(x) for x in nums[-2:]])  # last two = NFHS-6, NFHS-5
    assert len(vals) == 34, (var, len(vals))  # state + 33 districts
    rows[var] = vals[1:]  # drop the state sheet

df = pd.DataFrame({"district": toc})
for var, vals in rows.items():
    df[f"{var}_6"] = [v[0] for v in vals]
    df[f"{var}_5"] = [v[1] for v in vals]
out = ROOT / "data" / "interim" / "nfhs6_rajasthan_extracted.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(df.to_string(index=False))

