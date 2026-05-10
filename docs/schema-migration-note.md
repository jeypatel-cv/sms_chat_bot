# Property Schema Migration Note

The property source for VP Realty SMS Pilot moved from the legacy live export to the LeasingSnapshot export.

## Current source of truth

- Local testing uses `data/LeasingSnapshot - ChatBotClient.csv`
- Production and shared sheet workflows should use the LeasingSnapshot column set

## Removed legacy fields

- `listing_id`
- `view_details_url`

## Field changes

- `rent` now maps from LeasingSnapshot rent fields such as `advertised_rent`, `schd_rent`, or `new_rent`
- `bedrooms` and `bathrooms` are derived from `bed_and_bath` when separate fields are absent
- `manager_name`, `manager_email`, and `manager_phone` can be parsed from combined `contact_info`
- `street_address` can be synthesized from `street`, `street2`, `city`, `state`, and `zip` when needed

## Implementation notes

- The app loads LeasingSnapshot by default when no explicit property source is configured.
- Smoke tests now verify address, rent, availability, bedroom/bathroom, available-from, contact-info, budget, and handoff flows.
- The legacy live export comparison report remains available for reference in `property-csv-field-comparison-report.md`.
