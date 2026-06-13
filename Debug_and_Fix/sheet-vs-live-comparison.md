# Sheet vs Live Comparison

Date: 2026-06-13

## Sources Checked

- Public Google Sheet export:
  - `https://docs.google.com/spreadsheets/d/18b9gxA8GoC_-cpmjr-nG9ze2wG5NAfWWxhlg5MCfM7k/export?format=csv&gid=0`
- Live Render API:
  - `https://vp-realty-sms-pilot.onrender.com/api/properties`

## High-Level Result

- The public sheet is readable.
- The live API is also readable.
- The target property `1009 Riverstone Trail, Princeton, TX 75407` exists in both sources.
- The live endpoint is not a 1:1 mirror of the sheet export. There are row/field differences, but not a blocker for the target property.

## Key Counts

- Sheet rows: 209
- Live API rows: 200
- Unique `property_id` values in sheet: 181
- Unique `property_id` values in live API: 168

The difference is not just formatting. Some properties appear only in one source or have different canonical rows/variants.

## Target Property: 1009 Riverstone Trail

### Sheet row

- `property_id`: `373`
- `property`: `1009 Riverstone Trail, Princeton, TX 75407 - 1009 Riverstone Trail Princeton, TX 75407`
- `address`: `1009 Riverstone Trail Princeton, TX 75407`
- `street`: `1009 Riverstone Trail`
- `city`: `Princeton`
- `state`: `TX`
- `zip`: `75407`
- `unit_id`: `538`
- `unit_status`: `Vacant-Rented`
- `advertised_rent`: `2195`
- `contact_info`: empty

### Live API row

- `property_id`: `373`
- `name`: `1009 Riverstone Trail, Princeton, TX 75407`
- `address`: `1009 Riverstone Trail Princeton, TX 75407`
- `city`: `Princeton`
- `availability`: `Notice-Unrented`
- `rent_per_month`: `2295`
- `manager_phone`: `903-225-9627`
- `manager_email`: `sana@vprealtyservices.com`

### Conclusion for 1009

- The property is present in the live API.
- The address is normalized the same way in both sources.
- The live row appears to have newer operational data than the sheet row, especially:
  - availability/status
  - rent
  - contact info

## What This Means

- The earlier "not found" behavior was not because the sheet lacked `1009 Riverstone Trail`.
- The current code path should be able to match the property because:
  - the loader maps `property_id`, `address`, and `city`
  - the matcher checks exact and partial address matches before area fallback
- If production still misses this property, the likely cause is stale deploy state or a different environment/config issue, not the sheet row itself.

## Example Mismatches

The sheet and live API do not align perfectly on row population. Examples observed:

- Some sheet rows are absent from the live API with the same `property_id + address` signature.
- Some live rows exist under slightly different address/name variants.
- Several live rows are missing `unit_id` values compared with the sheet.

These differences should be treated as source-drift, not necessarily bugs in the matcher.

