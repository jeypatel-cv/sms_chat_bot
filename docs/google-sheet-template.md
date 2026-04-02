# Google Sheet Template - VP Realty Properties

Use one worksheet tab named `Properties` with these column headers in row 1:

| property_id | property_name | street_address | city | state | zip | rent | bedrooms | bathrooms | availability_status | available_from | description | listing_id | manager_name | manager_phone | contact_owner | notes |
|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|---|---|

## Example rows

| property_id | property_name | street_address | city | state | zip | rent | bedrooms | bathrooms | availability_status | available_from | description | listing_id | manager_name | manager_phone | contact_owner | notes |
|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|---|---|
| VP-1001 | Maple Ridge Apartments | 123 Main St | Dallas | TX | 75201 | 1850 | 2 | 2 | available | 2026-04-15 | Modern two-bedroom apartment near downtown. | LST-1001 | Sarah Khan | +12145550101 | leasing@vprealtyservices.com | Demo property |
| VP-1002 | Cedar Park Lofts | 45 Cedar Park Blvd | Plano | TX | 75024 | 1625 | 1 | 1 | available | 2026-04-01 | Bright loft-style unit with parking. | LST-1002 | Michael Chen | +12145550102 | leasing@vprealtyservices.com | Demo property |

## Notes

- Keep `property_id` unique.
- Keep `listing_id` unique if you use it.
- Keep `manager_phone` in E.164 format if you can, like `+12145550101`.
- Use ISO dates like `2026-04-15` for `available_from`.
- Use plain numbers for rent and room counts.
- Keep one property per row.
- Avoid merged cells or extra title rows.

## Message Log Tab

If you want to store inbound and outbound SMS records in the same spreadsheet, add a second worksheet tab named `MessageLogs` with these column headers in row 1.

This is optional and only used when `MESSAGE_LOG_TO_GOOGLE_SHEETS=true`.

| timestamp | direction | from_number | to_number | message_text | property_id | intent | status | error |
|---|---|---|---|---|---|---|---|---|

Suggested values:
- `direction`: `inbound` or `outbound`
- `status`: `received`, `sent`, `mock`, or `error`
- `error`: blank for success, text when something fails
