# Release Notes

## Versioning

- App version follows a simple release number like `1.1`.
- Update the version when you ship a meaningful change.
- Keep each note brief: what changed, what improved, and anything to watch.

## 1.1

- Switched the property source to the LeasingSnapshot schema.
- Added parsing for combined contact info and bed/bath fields.
- Updated the demo smoke test to cover the new property flow.

## 0.1.0

- Added the VP Realty SMS pilot demo and backend flow.
- Added local smoke testing, property lookup, and handoff behavior.
- Added message logging support and deployment docs.

## Release Process

1. Bump the app version in `production_app.py`.
2. Add a short release note here.
3. Push the change to GitHub or deploy through your production pipeline.
4. The demo page and API version fields will reflect the new release.
