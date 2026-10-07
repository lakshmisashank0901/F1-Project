# Progress

The dashboard uses the free OpenF1 history of the latest finished race. No F1 TV account.

- The map is the latest finished race whose cars actually move. Kuala Lumpur’s location feed does not, so the circuit shown is the previous one with a real lap.
- That lap is cached. Later rate limits do not wipe it.
- Season points come from Jolpica for the round before that race, so this race is not counted twice.
- The badge says REPLAY.

## Run

```bash
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
cd frontend && npm run dev
```

Dashboard: http://127.0.0.1:3000

