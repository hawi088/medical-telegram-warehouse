-- models/staging/stg_telegram_messages.sql
-- Staging model for raw Telegram messages
-- Cleans and standardizes raw data

WITH raw_data AS (
    SELECT
        -- Cast IDs to appropriate types
        id,
        message_id,
        channel_name,
        channel_username,
        
        -- Convert timestamp and handle timezone
        message_date::TIMESTAMP as message_date,
        
        -- Text cleaning
        TRIM(message_text) as message_text,
        
        -- Ensure numeric fields are integers
        COALESCE(views, 0)::INTEGER as views,
        COALESCE(forwards, 0)::INTEGER as forwards,
        
        -- Boolean flags
        COALESCE(has_media, FALSE) as has_media,
        media_type,
        image_path,
        COALESCE(image_downloaded, FALSE) as image_downloaded,
        
        -- Reply to
        reply_to,
        
        -- Raw data for debugging
        raw_data,
        loaded_at,
        
        -- Calculate derived fields
        LENGTH(TRIM(message_text)) as message_length,
        
        -- Has image flag (1 if has image, 0 otherwise)
        CASE 
            WHEN COALESCE(has_media, FALSE) = TRUE AND media_type = 'photo' THEN 1 
            ELSE 0 
        END as has_image_flag,
        
        -- Extract date parts
        DATE(message_date) as post_date,
        
        -- Channel name normalization
        LOWER(TRIM(channel_name)) as channel_name_clean
        
    FROM {{ source('raw', 'telegram_messages') }}
)

SELECT
    -- Primary key
    id,
    
    -- Message identifiers
    message_id,
    channel_name,
    channel_name_clean,
    channel_username,
    
    -- Date and time
    message_date,
    post_date,
    
    -- Message content
    message_text,
    message_length,
    
    -- Engagement metrics
    views,
    forwards,
    
    -- Media
    has_media,
    has_image_flag,
    media_type,
    image_path,
    image_downloaded,
    
    -- Relationships
    reply_to,
    
    -- Debug
    raw_data,
    loaded_at
    
FROM raw_data

-- Filter out invalid messages
WHERE message_text IS NOT NULL 
  AND message_text != ''
  AND message_text != ' '
  AND message_id IS NOT NULL