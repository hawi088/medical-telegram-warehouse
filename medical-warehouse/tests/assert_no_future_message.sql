-- tests/assert_no_future_messages.sql
-- Ensure no messages have future dates

SELECT *
FROM {{ ref('stg_telegram_messages') }}
WHERE message_date > CURRENT_TIMESTAMP