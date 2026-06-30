-- models/marts/dim_channels.sql
-- Channel dimension table with channel attributes

WITH channel_stats AS (
    SELECT
        channel_name,
        channel_name_clean,
        channel_username,
        MIN(message_date) as first_post_date,
        MAX(message_date) as last_post_date,
        COUNT(*) as total_posts,
        AVG(views) as avg_views,
        SUM(views) as total_views,
        SUM(forwards) as total_forwards,
        COUNT(DISTINCT message_id) as unique_messages,
        
        -- Assign channel type based on name patterns
        CASE
            WHEN LOWER(channel_name) LIKE '%pharmacy%' 
              OR LOWER(channel_name) LIKE '%cosmetic%' 
              OR LOWER(channel_name) LIKE '%drug%'
              OR LOWER(channel_name) LIKE '%pharma%'
                THEN 'Pharmaceutical'
            WHEN LOWER(channel_name) LIKE '%medical%' 
              OR LOWER(channel_name) LIKE '%health%' 
              OR LOWER(channel_name) LIKE '%clinic%'
              OR LOWER(channel_name) LIKE '%hospital%'
                THEN 'Medical'
            WHEN LOWER(channel_name) LIKE '%lobelia%'
              OR LOWER(channel_name) LIKE '%cosmetics%'
                THEN 'Cosmetics'
            ELSE 'Other'
        END as channel_type
        
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY channel_name, channel_name_clean, channel_username
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['channel_name']) }} as channel_key,
    channel_name,
    channel_name_clean,
    channel_username,
    channel_type,
    first_post_date,
    last_post_date,
    total_posts,
    ROUND(COALESCE(avg_views, 0), 2) as avg_views,
    COALESCE(total_views, 0) as total_views,
    COALESCE(total_forwards, 0) as total_forwards,
    -- Days active using PostgreSQL compatible syntax
    EXTRACT(DAY FROM (COALESCE(last_post_date, first_post_date) - first_post_date)) as days_active,
    -- Posts per day
    ROUND(total_posts / NULLIF(EXTRACT(DAY FROM (COALESCE(last_post_date, first_post_date) - first_post_date)), 0), 2) as posts_per_day,
    -- Engagement ratio
    ROUND(total_views / NULLIF(total_posts, 0), 2) as avg_views_per_post
    
FROM channel_stats