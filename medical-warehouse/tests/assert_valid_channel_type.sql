-- tests/assert_valid_channel_type.sql
-- Ensure channel types are valid

SELECT *
FROM {{ ref('dim_channels') }}
WHERE channel_type NOT IN ('Pharmaceutical', 'Cosmetics', 'Medical', 'Other')