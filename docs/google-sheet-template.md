# Leasing Snapshot Template - VP Realty Properties

Use one worksheet tab named `ChatBotClient` with these column headers in row 1. This mirrors `data/LeasingSnapshot - ChatBotClient.csv`.

```text
advertised_rent,posted_to_website,posted_to_internet,property,property_name,amenities,lockbox_enabled,affordable_program,address,street,street2,city,state,zip,unit,unit_tags,unit_type,bed_and_bath,sqft,unit_status,rent_ready,days_vacant,last_rent,schd_rent,new_rent,last_move_in,last_move_out,available_on,next_move_in,description,amenities_price,computed_market_rent,ready_for_showing_on,unit_turn_target_date,property_id,unit_id,contact
```

## Notes

- `bed_and_bath` is the combined bedroom/bathroom field used by the app.
- `contact` or `contact_info` combines the contact name, email, and phone in one cell.
- `address`, `street`, and `street2` can be used together to reconstruct a display address.
- Keep one property/unit per row.
- Avoid merged cells or extra title rows.

## Message Log Tab

If you want to store inbound and outbound SMS records in the same spreadsheet, add a second worksheet tab named `MessageLogs` with these column headers in row 1.

This is optional and used when the backend logs messages into the sheet.

| timestamp | direction | from_number | to_number | message_text | property_id | intent | status | error |
|---|---|---|---|---|---|---|---|---|

Suggested values:
- `direction`: `in-SMS`, `out-SMS`, `in-CALL`, or `out-SMS-C`
- `status`: `received`, `sent`, `mock`, or `error`
- `error`: blank for success, text when something fails
