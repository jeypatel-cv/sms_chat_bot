# VP Realty SMS Pilot

This project contains the VP Realty SMS pilot, with the same backend engine used for local testing and production.

Start here:
- [docs/INDEX.md](docs/INDEX.md)
- [docs/render-checklist.md](docs/render-checklist.md)
- `server.py` for local testing
- `production_app.py` for production

## What it does

- serves a local test harness for the SMS engine
- uses the live export CSV for local and server-side testing
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
- `data/vp_properties_live_export.csv`

This keeps local and server-side tests aligned on the same property set.

## Test prompts

- Is 123 Main St available?
- How much is rent for Maple Ridge Apartments?
- How many bedrooms and bathrooms does 45 Cedar Park Blvd have?
- When is Sycamore Flats available from?
- Can I speak to a human?

## Files

- `server.py` - local HTTP server and conversation engine
- `data/properties.json` - dummy property dataset
- `data/vp_properties_live_export.csv` - current live property export used by local and demo testing
- `static/index.html` - UI shell
- `static/styles.css` - visual styling
- `static/app.js` - frontend behavior
- `docs/INDEX.md` - navigation for design and deployment notes
