-- insert_test_coords.sql
-- Replace <USER_ID> with the farmer/user id you want to update.
-- Adjust column names if your farmers table uses different names.

-- Example: set coordinates for user id 1
UPDATE farmers
SET latitude = 23.8103,
    longitude = 90.4125
WHERE id = 1;

-- Verify:
SELECT id, name, latitude, longitude, district, division
FROM farmers
WHERE id = 1;
