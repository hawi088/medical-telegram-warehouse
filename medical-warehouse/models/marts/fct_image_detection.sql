-- models/marts/fct_image_detections.sql
-- Image detection results from YOLO

WITH detection_data AS (
    SELECT
        message_id,
        image_path,
        category,
        category_confidence,
        class_id,
        class_name,
        confidence,
        has_person,
        has_product
    FROM {{ source('staging', 'yolo_detections') }}
)

SELECT
    -- Generate surrogate key
    {{ dbt_utils.generate_surrogate_key(['message_id', 'class_id']) }} as detection_key,
    d.message_id,
    d.channel_key,
    d.date_key,
    det.image_path,
    det.category as image_category,
    det.category_confidence,
    det.class_id,
    det.class_name,
    det.confidence as detection_confidence,
    det.has_person,
    det.has_product,
    -- Engagement metrics from fact table
    d.views,
    d.forwards,
    d.total_engagement,
    -- Message text preview
    LEFT(d.message_text, 100) as message_preview
    
FROM detection_data det
LEFT JOIN {{ ref('fct_messages') }} d ON det.message_id = d.message_key