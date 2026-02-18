# Bangify

Bangify is a risk-first, evidence-driven DeFi/perps execution system.

## Repository Structure
- `docs/` — product, architecture, execution, risk, and metric docs
- `lesson/` — incidents, failures, and prevention rules

## Current Objective
Build a semi-auto MVP that can prove positive net expectancy after all costs (fees, slippage, funding), then scale safely.

## Operating Rules
1. Real data only.
2. No evidence, no scale.
3. Risk first, returns second.
4. Keep changes small and auditable.

## Risk Engine (MVP)
Core module lives in `risk_engine/` and currently enforces:
- Position sizing by risk percent + stop distance
- Daily loss cap guard
- Kill-switch logic (manual or max consecutive losses)

### Run tests
```bash
python -m pip install -U pytest
pytest
```
