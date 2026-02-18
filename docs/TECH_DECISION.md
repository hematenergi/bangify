# Tech Decision (MVP)

## Chosen Direction
- Core engine: deterministic, rule-based (non-LLM critical path)
- Execution integration: exchange API wrapper (CCXT-style architecture)
- Storage: lightweight auditable logs (JSONL/SQLite)
- Reporting: concise daily summaries

## Why
- Fastest path to measurable MVP
- Lower operational complexity
- Better reliability under model downgrade

## LLM Role
- Optional copilot for summaries/anomaly explanation only
- Not used as execution decision authority
