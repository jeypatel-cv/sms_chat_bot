# Google Sheet Template - VP Realty Properties

Use one worksheet tab named `Properties` with these column headers in row 1:

| property_id | property_name | street_address | city | state | zip | rent | bedrooms | bathrooms | availability_status | available_from | listing_id | manager_name | manager_phone | view_details_url | sqft |
|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|---:|

## Example rows

| property_id | property_name | street_address | city | state | zip | rent | bedrooms | bathrooms | availability_status | available_from | listing_id | manager_name | manager_phone | view_details_url | sqft |
|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|---:|
| VP-LIVE-001 | 1913 Ridge Creek Ln | 1913 Ridge Creek Ln | Aubrey | TX | 76227 | 2295 | 3 | 2 | available | NOW | dcccd8f9-a8ad-4948-b288-9289826cda5f | Anjali Sangtani | 972-591-8075 | https://www.vprealtyservices.com/listings/detail/dcccd8f9-a8ad-4948-b288-9289826cda5f | 1924 |
| VP-LIVE-002 | 312 Santa Lucia | 312 Santa Lucia | Anna | TX | 75409 | 3650 | 5 | 4.5 | available | 06/05/2026 | 3848ec4a-898b-42c7-9263-d1c73fb01454 | Anjali Sangtani | 972-591-8075 | https://www.vprealtyservices.com/listings/detail/3848ec4a-898b-42c7-9263-d1c73fb01454 | 3719 |

## Notes

- Keep `property_id` unique.
- Keep `listing_id` unique if you use it.
- Keep `manager_phone` in a simple phone format.
- Keep one property per row.
- Avoid merged cells or extra title rows.

## Message Log Tab

If you want to store inbound and outbound SMS records in the same spreadsheet, add a second worksheet tab named `MessageLogs` with these column headers in row 1.

This is optional and used when the backend logs messages into the sheet.

| timestamp | direction | from_number | to_number | message_text | property_id | intent | status | error |
|---|---|---|---|---|---|---|---|---|

Suggested values:
- `direction`: `inbound` or `outbound`
- `status`: `received`, `sent`, `mock`, or `error`
- `error`: blank for success, text when something fails
