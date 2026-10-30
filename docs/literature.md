# Related literature (methods and topic)

Each paper is mapped to the part of our design it supports.

## Border / contiguous-pair DiD (main specification)

- **Dube, A., Lester, T. W., & Reich, M. (2010).** Minimum wage effects across state borders: Estimates using contiguous counties. *Review of Economics and Statistics*, 92(4), 945–964.
  The template for our design: county pairs straddling a state border, with pair-by-period fixed effects.
- **Card, D., & Krueger, A. B. (1994).** Minimum wages and employment: A case study of the fast-food industry in New Jersey and Pennsylvania. *American Economic Review*, 84(4), 772–793.
  The original cross-border DiD: one treated state against its neighbour, before and after.
- **Holmes, T. J. (1998).** The effect of state policies on the location of manufacturing: Evidence from state borders. *Journal of Political Economy*, 106(4), 667–705.
  An early state-border comparison. Useful for motivating why border units are comparable.

## One treated state: event study and inference

- **Abadie, A., Diamond, A., & Hainmueller, J. (2010).** Synthetic control methods for comparative case studies: Estimating the effect of California's tobacco control program. *Journal of the American Statistical Association*, 105(490), 493–505.
  One treated state, with placebo (permutation) inference across donor states. This is our state-level inference.
- **Conley, T. G., & Taber, C. R. (2011).** Inference with "difference in differences" with a small number of policy changes. *Review of Economics and Statistics*, 93(1), 113–125.
  Why conventional SEs fail with one treated state, and what to do instead.

## Intensity (continuous-treatment) DiD (PMUY appendix)

- **Duflo, E. (2001).** Schooling and labor market consequences of school construction in Indonesia. *American Economic Review*, 91(4), 795–813.
  Program intensity by region × exposure by cohort.
- **Finkelstein, A. (2007).** The aggregate effects of health insurance: Evidence from the introduction of Medicare. *Quarterly Journal of Economics*, 122(1), 1–37.
  Treatment intensity = pre-existing insurance gap by region. The same logic as our PMUY exposure = pre-existing clean-fuel gap.

## Spatial RDD (future work, not used)

- **Dell, M. (2010).** The persistent effects of Peru's mining mita. *Econometrica*, 78(6), 1863–1903.
  The reference spatial/geographic RDD. Needs household or village locations.
- **Sood, N., Bendavid, E., Mukherji, A., Wagner, Z., Nagpal, S., & Mullen, P. (2014).** Government health insurance for people below poverty line in India: Quasi-experimental evaluation of insurance and health outcomes. *BMJ*, 349, g5114.
  Geographic RD across 572 villages on either side of the Vajpayee Arogyashree (Karnataka) rollout boundary. Found lower mortality from covered conditions and 64% lower OOP for covered tertiary care among BPL households.

## Topic: health insurance in India

- **Karan, A., Yip, W., & Mahal, A. (2017).** Extending health insurance to the poor in India: An impact evaluation of Rashtriya Swasthya Bima Yojana on out of pocket spending for healthcare. *Social Science & Medicine*, 181, 83–92.
  DiD on matched districts using NSS. RSBY did **not** reduce OOP, and the probability of any OOP rose. This is the direct prior for our OOP result and the scheme our control states had.
- **Dupas, P., & Jain, R. (2021, rev. 2023).** Women left behind: Gender disparities in utilization of government health insurance in India. NBER Working Paper 28972.
  Uses 4.2 million BSBY (Rajasthan) claims. Women are under-represented in hospital visits. This is our exact scheme. *Working paper; check for a journal version before citing.*

## Topic: PMUY

- **Kar, A., Pachauri, S., Bailis, R., & Zerriffi, H. (2019).** Using sales data to assess cooking gas adoption and the impact of India's Ujjwala programme in rural Karnataka. *Nature Energy*, 4(9), 806–814.
  Connections rose much faster than LPG consumption, which is consistent with our low conversion rate.
