# VP Realty SMS Pilot

This project contains the VP Realty SMS pilot, with the same backend engine used for local testing and production.

Start here:
- [docs/INDEX.md](docs/INDEX.md)
- [docs/schema-migration-note.md](docs/schema-migration-note.md)
- [docs/render-checklist.md](docs/render-checklist.md)
- `server.py` for local testing
- `production_app.py` for production

## What it does

- serves a local test harness for the SMS engine
- uses the LeasingSnapshot CSV for local and server-side testing
- answers basic leasing questions
- keeps simple conversation context
- simulates human handoff
- logs inbound and outbound messages for review

## Run it

Local testing uses the same backend engine as production, with local defaults:

```powershell
python server.py
```

Then open:

```text
http://127.0.0.1:8000/demo
```

Production uses the same `production_app.py` engine with cloud environment variables.

## Test data

The local demo uses:
- `data/LeasingSnapshot - ChatBotClient.csv`

This keeps local and server-side tests aligned on the same property set.

## Test prompts

- Is 1913 Ridge Creek Ln available?
- How much is rent for 1913 Ridge Creek Ln?
- How many bedrooms and bathrooms does 3136 Overlook Drive have?
- When is 106 Sunberry Drive available from?
- Can I speak to a human?

## Versioning

- The demo page shows the current app version.
- Release notes live in [docs/release-notes.md](docs/release-notes.md).
- Keep each release note short and simple, then bump the version when shipping meaningful changes.

## Files

- `server.py` - local HTTP server and conversation engine
- `data/properties.json` - dummy property dataset
- `data/LeasingSnapshot - ChatBotClient.csv` - current LeasingSnapshot export used by local and demo testing
- `static/index.html` - UI shell
- `static/styles.css` - visual styling
- `static/app.js` - frontend behavior
- `docs/INDEX.md` - navigation for design and deployment notes
