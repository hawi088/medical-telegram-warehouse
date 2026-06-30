-- models/marts/dim_dates.sql
-- Date dimension table with date attributes

WITH date_range AS (
    -- Get min and max dates from messages (with 30-day padding)
    SELECT
        DATE_TRUNC('day', MIN(message_date)) - INTERVAL '30 days' as start_date,
        DATE_TRUNC('day', MAX(message_date)) + INTERVAL '30 days' as end_date
    FROM {{ ref('stg_telegram_messages') }}
),

date_spine AS (
    -- Generate all dates from min to max
    SELECT
        GENERATE_SERIES(
            (SELECT start_date FROM date_range)::DATE,
            (SELECT end_date FROM date_range)::DATE,
            INTERVAL '1 day'
        )::DATE as full_date
)

SELECT
    -- Surrogate key (YYYYMMDD format)
    TO_CHAR(full_date, 'YYYYMMDD')::INTEGER as date_key,
    full_date,
    EXTRACT(DAY FROM full_date) as day_of_month,
    EXTRACT(DOW FROM full_date) as day_of_week,
    CASE EXTRACT(DOW FROM full_date)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    EXTRACT(WEEK FROM full_date) as week_of_year,
    EXTRACT(MONTH FROM full_date) as month,
    TO_CHAR(full_date, 'Month') as month_name,
    EXTRACT(QUARTER FROM full_date) as quarter,
    EXTRACT(YEAR FROM full_date) as year,
    CASE 
        WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN 1 
        ELSE 0 
    END as is_weekend,
    CASE 
        WHEN EXTRACT(DOW FROM full_date) NOT IN (0, 6) THEN 1 
        ELSE 0 
    END as is_weekday,
    'Q' || EXTRACT(QUARTER FROM full_date) || ' ' || EXTRACT(YEAR FROM full_date) as quarter_name,
    TO_CHAR(full_date, 'YYYY-MM') as year_month

FROM date_spine