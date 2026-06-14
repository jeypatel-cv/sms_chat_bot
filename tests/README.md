# Tests

Run the local test suite with:

```bash
python -m unittest discover -s tests -v
```

What it covers:
- property record parsing from the snapshot CSV
- contact column parsing
- exact and partial property lookup
- budget queries and session clearing
- code / contact / availability flows
- real log-derived customer messages from the last 14 days
- a 200-case regression matrix with 160 real log-derived prompts and 40 synthetic prompts
- saved test run notes in `tests/test_log.md`

Notes:
- The tests use the checked-in `data/LeasingSnapshot - ChatBotClient.csv` snapshot.
- If the snapshot changes, update the tests to keep the real-log cases aligned with the new inventory.
- The smoke test in `static/app.js` now runs 15 real-life prompts only.
