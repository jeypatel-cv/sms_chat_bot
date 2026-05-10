# Property CSV Field Comparison Report

This report compares the active LeasingSnapshot schema with the legacy live export and the other sample formats in the repo.

## 1. Active LeasingSnapshot export

Source file:
- `data/LeasingSnapshot - ChatBotClient.csv`

Headers:
- `advertised_rent`
- `posted_to_website`
- `posted_to_internet`
- `property`
- `property_name`
- `amenities`
- `lockbox_enabled`
- `affordable_program`
- `address`
- `street`
- `street2`
- `city`
- `state`
- `zip`
- `unit`
- `unit_tags`
- `unit_type`
- `bed_and_bath`
- `sqft`
- `unit_status`
- `rent_ready`
- `days_vacant`
- `last_rent`
- `schd_rent`
- `new_rent`
- `last_move_in`
- `last_move_out`
- `available_on`
- `next_move_in`
- `description`
- `amenities_price`
- `computed_market_rent`
- `ready_for_showing_on`
- `unit_turn_target_date`
- `property_id`
- `unit_id`
- `contact_info`

## 2. Legacy live export

Source file:
- `data/vp_properties_live_export.csv`

Headers:
- `property_id`
- `property_name`
- `street_address`
- `city`
- `state`
- `zip`
- `rent`
- `bedrooms`
- `bathrooms`
- `availability_status`
- `available_from`
- `listing_id`
- `manager_name`
- `Manager Email`
- `manager_phone`
- `view_details_url`
- `sqft`

## 3. Google Sheet template

Source file:
- `docs/google-sheet-template.md`

Headers:
- same as the active LeasingSnapshot export above

## 4. Other sample CSV format

Source file:
- `data/properties.sample.csv`

Headers:
- `property_id`
- `property_name`
- `street_address`
- `city`
- `state`
- `zip`
- `rent`
- `bedrooms`
- `bathrooms`
- `availability_status`
- `available_from`
- `description`
- `listing_id`
- `manager_name`
- `manager_phone`
- `contact_owner`
- `notes`

## 5. JSON sample format

Source file:
- `data/properties.json`

Observed fields:
- `property_id`
- `name`
- `address`
- `rent_per_month`
- `bedrooms`
- `bathrooms`
- `availability`
- `available_from`
- `description`
- `manager_name`
- `manager_phone`
- `contact_owner`

## 6. Migration summary

Compared with the legacy live export:
- `street_address` maps to `address` plus `street` and `street2`
- `rent` maps to `advertised_rent`, `schd_rent`, or `new_rent`
- `bedrooms` and `bathrooms` map to `bed_and_bath`
- `availability_status` maps to `unit_status` and `rent_ready`
- `available_from` maps to `available_on`, `next_move_in`, or `ready_for_showing_on`
- `manager_name`, `manager_email`, and `manager_phone` now come from `contact_info`
- `listing_id` and `view_details_url` are intentionally not part of the new snapshot schema

## 7. Compatibility note

The loader treats these as aliases rather than separate schemas:
- `property_name` and `name`
- `street_address` and `address`
- `rent` and `rent_per_month`
- `availability_status` and `availability`
- `Manager Email` and `manager_email`
- `manager_phone` and `contact_phone`
- `contact_info` as the combined name/email/phone source in the snapshot

The active LeasingSnapshot export is now the source of truth for local testing and Google Sheets work.
