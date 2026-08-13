⚡ ElecTrack Pro — Field Intervention Management SaaS for Utility Infrastructure

[🇫🇷 Version française](README.fr.md)

`AppSheet` `Google Apps Script` `Google Sheets` `Multi-Tenant SaaS` `Role-Based Security`

## Overview

Reusable SaaS platform for managing field interventions on utility infrastructure worksites — built on **AppSheet + Google Sheets + Google Apps Script**. Designed not as a one-off data-collection form but as a **productized, multi-client-ready system**: no client-specific hardcoding anywhere in the data model, formulas, or automation scripts.

Currently powering the field tracking of electrical infrastructure worksites for a national utility client across **55 localities in 4 administrative departments**, with a full data hierarchy (Project → Geo → Locality → Intervention → Detail) and role-based access for **Super Admin, Admin, Chef de Mission, and zone-restricted Supervisors**.

Built by Medico Diomande — Electromechanical Engineer (10 years field experience on World Bank / AFD / AfDB electrification projects) turned technical architect. Domain expertise directly shapes the product: the data model, the progress-calculation logic, and the security rules all reflect how electrification worksites are actually run in the field.

## Business Impact

- → Replaces scattered spreadsheets and paper reports with a single governed platform: live worksite progress, weighted advancement tracking, and materials reconciliation
- → Automated email alerting on site inactivity and task anomalies — no more manual follow-up on stalled worksites
- → Role-based data isolation means field supervisors only ever see their assigned zone — no accidental cross-project data exposure
- → Architecture designed from day one for multi-client resale, not a single bespoke deployment

## Key Features

- → Weighted progress tracking (`Avancement_Pondéré`) computed per locality from task-level completion and configurable task weights
- → Automated snapshot & reporting pipeline (Apps Script, scheduled triggers) feeding rankings, recaps, and materials-consumption tables
- → Anomaly detection and automated alerting to the right stakeholders based on project configuration, not hardcoded emails
- → GPS-aware worksite tracking, cleanly separated from submitter location (a subtle but critical distinction in field data collection)
- → User-project membership managed through a proper junction table, not a fragile comma-separated list

## Architecture Highlights

| Concern | Approach |
|---|---|
| **Multi-tenancy** | One dedicated Google Sheets workbook per client (v2) — eliminates cross-client data-leak risk structurally, not just by filter |
| **Security** | Every table filtered by `Actif=TRUE` + role + zone/project scope; circular self-reference on the Users table solved via a read-only mirror table |
| **Automation** | Apps Script layer (not AppSheet Bots) for email delivery, with lock service to prevent overlapping runs and retry wrappers on all Sheets reads |
| **Data integrity** | Stable hex IDs as keys — never mutable display text — to prevent silent referential-integrity breaks on rename |

## Lessons Learned (a sample)

Real production traps, discovered and documented while hardening the platform for commercial deployment:

- **`LOOKUP()` silently fails on Ref-typed columns in AppSheet** — it returns the first row of the target table instead of erroring. The reliable fix: `ANY(SELECT(Table[return_col], [key_col] = [_THISROW].[ref_col]))`.
- **App Formula + Initial Value conflict**: deriving a foreign key via App Formula from a column not yet populated at form-entry time silently breaks every downstream `Valid_If`. Fix: keep only the Initial Value expression.
- **Decimal precision matters for chained calculations**: a Percent virtual column truncated to 2 decimals silently propagated rounding error into a dependent weighted-progress formula — fixed by increasing precision, not by "checking the math."
- **AppSheet can't reference a table in its own Security Filter** — solved with a read-only mirror/pivot table pattern.

## Tech Stack

```
Frontend:      AppSheet (no-code mobile + web app)
Backend:       Google Sheets (structured multi-table data model)
Automation:    Google Apps Script (scheduled triggers, email alerts, snapshot pipeline)
```

## Why My Background Matters

Ten years running electrification worksites for World Bank, AFD, and AfDB-funded projects means I know what actually breaks a field-reporting system in practice: unreliable connectivity, supervisors submitting from the wrong location, materials reconciliation that has to survive renamed reference data. ElecTrack Pro's architecture — the security model, the automated alerting, the weighted-progress logic — is built around those failure modes, not around a generic CRUD tutorial.

---

Author: Medico Diomande · dmedcos@yahoo.fr · linkedin.com/in/medico-diomande-data · Available for remote missions
