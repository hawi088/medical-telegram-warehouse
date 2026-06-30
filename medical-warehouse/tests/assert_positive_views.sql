-- tests/assert_positive_views.sql
-- Ensure view counts are non-negative

SELECT *
FROM {{ ref('stg_telegram_messages') }}
WHERE views < 0