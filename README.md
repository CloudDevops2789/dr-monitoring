# DR Monitoring + ServiceNow Automation

## Features
- Health check (Web, DB, CPU, Memory)
- Auto incident creation in ServiceNow
- Duplicate prevention
- Auto incident closure after DR
- Idempotent logic

## Structure
- scripts/ → monitoring logic
- utils/ → ServiceNow integration
- config/ → config (ignored in git)

## Run
python -m scripts.dr_health_check
