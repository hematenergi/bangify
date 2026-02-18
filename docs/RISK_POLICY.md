# Risk Policy (MVP)

## Hard Rules
- Risk per trade: 0.25% equity (initial)
- Max daily loss: 1.0% equity
- Max open risk: 0.75% equity
- Max leverage: conservative cap per instrument

## Mandatory Stops
- Kill switch on daily hard-stop breach
- Cooldown after 3 consecutive losses
- No new entries when market conditions fail quality checks

## Escalation
- Any rule breach => trading paused + incident note required in `lesson/`
