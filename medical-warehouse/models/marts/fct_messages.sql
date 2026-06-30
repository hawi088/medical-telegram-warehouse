-- models/marts/fct_messages.sql
-- Fact table containing message events

WITH messages AS (
    SELECT
        id,
        message_id,
        channel_name,
        message_date::DATE as message_date,
        message_text,
        views,
        forwards,
        has_image_flag,
        message_length
    FROM {{ ref('stg_telegram_messages') }}
)

SELECT
    -- Primary key (message_id is unique per channel)
    message_id as message_key,
    {{ dbt_utils.generate_surrogate_key(['channel_name']) }} as channel_key,
    TO_CHAR(message_date, 'YYYYMMDD')::INTEGER as date_key,
    message_text,
    views,
    forwards,
    has_image_flag,
    message_length,
    -- Engagement total
    COALESCE(views, 0) + COALESCE(forwards, 0) as total_engagement,
    -- Has image description
    CASE 
        WHEN has_image_flag = 1 THEN 'Has Image'
        ELSE 'No Image'
    END as image_status

FROM messages