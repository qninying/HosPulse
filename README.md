<picture>
  <source media="(prefers-color-scheme: dark)" srcset="brand/logo-on-dark.svg">
  <img alt="HosPulse" src="brand/logo.svg" height="44">
</picture>

Early-warning intelligence for companies that manage rural hospitals.

Rural hospital operators usually learn a hospital is in trouble weeks after the problem started, from monthly reports. HosPulse pulls data from every managed hospital into one view and flags trouble early: cash, days in A/R, denial spikes, staffing.

## Status

Pre-product. Validating with rural hospital management companies in Oklahoma and Texas.

## Plan

| Phase | What | Data |
|---|---|---|
| 0 | **Health Snapshot**: free tool built on public CMS cost report data (HCRIS) | Public only |
| 1 | Early-warning briefing for one management company, from exported reports | Financial / operational, no PHI |
| 2 | Automated multi-hospital dashboard, paid pilot per hospital per month | Financial / operational, no PHI |
| 3 | Cost report co-pilot (find missed reimbursement) | Financial |

Patient data (PHI) is out of scope until BAAs and a HIPAA review are in place.

## Repo layout

- `docs/research/` - market research, prospect lists
- `docs/validation/` - customer conversation notes and findings
