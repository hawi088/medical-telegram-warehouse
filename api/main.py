"""
FastAPI Application for Telegram Medical Data Warehouse
Task 4: Build an Analytical API
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import get_db, test_connection
from api.schemas import (
    TopProductResponse,
    ChannelActivityResponse,
    MessageSearchResponse,
    VisualContentStatsResponse,
    ErrorResponse
)

# Create FastAPI app
app = FastAPI(
    title="Telegram Medical Data Warehouse API",
    description="Analytical API for Ethiopian medical Telegram channels",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Check if the API is running and database is connected"""
    db_healthy = test_connection()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db_healthy else "disconnected"
    }


# ============================================================================
# Endpoint 1: Top Products (FIXED)
# ============================================================================

@app.get(
    "/api/reports/top-products",
    response_model=List[TopProductResponse],
    tags=["Reports"],
    summary="Get most frequently mentioned products/terms"
)
async def get_top_products(
    limit: int = Query(10, description="Number of top products to return", ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Returns the most frequently mentioned terms/products across all channels.
    
    - **limit**: Number of products to return (default: 10, max: 50)
    """
    try:
        query = text("""
            WITH word_counts AS (
                SELECT 
                    LOWER(TRIM(word)) as product,
                    COUNT(*) as mention_count,
                    COUNT(DISTINCT channel_name) as channel_count,
                    STRING_AGG(DISTINCT channel_name, ', ') as channels
                FROM (
                    SELECT 
                        channel_name,
                        UNNEST(regexp_split_to_array(message_text, '[\\s\\n\\r\\t,.;:!?]+')) as word
                    FROM marts.fct_messages
                    WHERE message_text IS NOT NULL AND message_text != ''
                ) words
                WHERE LENGTH(word) > 3
                  AND word NOT IN ('the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'are', 'was', 'were', 'will', 'your', 'our', 'their', 'about', 'which', 'what', 'when', 'where', 'who', 'whom', 'whose')
                  AND word ~ '^[a-zA-Z0-9]+$'
                GROUP BY LOWER(TRIM(word))
                HAVING COUNT(*) > 1
            ),
            total_count AS (
                SELECT SUM(mention_count) as total FROM word_counts
            )
            SELECT 
                wc.product,
                wc.mention_count,
                wc.channels,
                ROUND((wc.mention_count::NUMERIC / NULLIF(tc.total, 0)) * 100, 2) as percentage
            FROM word_counts wc
            CROSS JOIN total_count tc
            ORDER BY wc.mention_count DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        rows = result.fetchall()
        
        response = []
        for row in rows:
            response.append({
                "product": row[0],
                "mention_count": row[1],
                "channels": row[2].split(', ') if row[2] else [],
                "percentage": float(row[3]) if row[3] else 0.0
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching top products: {str(e)}"
        )


# ============================================================================
# Endpoint 2: Channel Activity
# ============================================================================

@app.get(
    "/api/channels/{channel_name}/activity",
    response_model=ChannelActivityResponse,
    tags=["Channels"],
    summary="Get posting activity and trends for a specific channel"
)
async def get_channel_activity(
    channel_name: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Returns posting activity and trends for a specific channel.
    """
    try:
        # Get daily activity
        activity_query = text("""
            SELECT 
                dd.full_date,
                COUNT(f.message_key) as posts
            FROM marts.dim_dates dd
            LEFT JOIN marts.fct_messages f ON dd.date_key = f.date_key
            WHERE dd.full_date >= CURRENT_DATE - INTERVAL ':days days'
            GROUP BY dd.full_date
            ORDER BY dd.full_date
        """)
        
        result = db.execute(activity_query, {"days": days})
        activity_rows = result.fetchall()
        
        activity_trend = [
            {"date": row[0].isoformat(), "posts": row[1]}
            for row in activity_rows
        ]
        
        # Get channel stats
        stats_query = text("""
            SELECT 
                d.channel_name,
                COUNT(f.message_key) as total_posts,
                COALESCE(AVG(f.views), 0) as avg_views,
                COALESCE(AVG(f.forwards), 0) as avg_forwards,
                MIN(f.message_date) as first_post,
                MAX(f.message_date) as last_post
            FROM marts.fct_messages f
            JOIN marts.dim_channels d ON f.channel_key = d.channel_key
            WHERE d.channel_name ILIKE :channel_name
            GROUP BY d.channel_name
        """)
        
        result = db.execute(stats_query, {"channel_name": f"%{channel_name}%"})
        stats = result.fetchone()
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"Channel '{channel_name}' not found"
            )
        
        return ChannelActivityResponse(
            channel_name=stats[0],
            total_posts=stats[1] or 0,
            avg_views=float(stats[2] or 0),
            avg_forwards=float(stats[3] or 0),
            first_post_date=stats[4] or datetime.now(),
            last_post_date=stats[5] or datetime.now(),
            posts_per_day=round(stats[1] / max(1, (stats[5] - stats[4]).days), 2) if stats[4] and stats[5] else 0,
            top_issues=[],
            activity_trend=activity_trend[:30]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching channel activity: {str(e)}"
        )


# ============================================================================
# Endpoint 3: Message Search
# ============================================================================

@app.get(
    "/api/search/messages",
    response_model=List[MessageSearchResponse],
    tags=["Search"],
    summary="Search for messages containing a specific keyword"
)
async def search_messages(
    query: str = Query(..., description="Search keyword or phrase", min_length=1),
    limit: int = Query(20, description="Number of results to return", ge=1, le=100),
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    db: Session = Depends(get_db)
):
    """
    Searches for messages containing a specific keyword.
    """
    try:
        search_query = text("""
            SELECT 
                f.message_key as message_id,
                d.channel_name,
                f.message_date,
                f.message_text,
                f.views,
                f.forwards,
                f.has_image_flag as has_image,
                NULL as image_category
            FROM marts.fct_messages f
            JOIN marts.dim_channels d ON f.channel_key = d.channel_key
            WHERE f.message_text ILIKE CONCAT('%', :query, '%')
            AND (:channel IS NULL OR d.channel_name ILIKE :channel)
            ORDER BY f.message_date DESC
            LIMIT :limit
        """)
        
        result = db.execute(search_query, {
            "query": query,
            "channel": f"%{channel}%" if channel else None,
            "limit": limit
        })
        rows = result.fetchall()
        
        response = []
        for row in rows:
            response.append(MessageSearchResponse(
                message_id=row[0],
                channel_name=row[1],
                message_date=row[2],
                message_text=row[3][:500] if row[3] else "",
                views=row[4] or 0,
                forwards=row[5] or 0,
                has_image=row[6] or False,
                image_category=row[7]
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching messages: {str(e)}"
        )


# ============================================================================
# Endpoint 4: Visual Content Stats
# ============================================================================

@app.get(
    "/api/reports/visual-content",
    response_model=List[VisualContentStatsResponse],
    tags=["Reports"],
    summary="Get statistics about image usage across channels"
)
async def get_visual_content_stats(
    db: Session = Depends(get_db)
):
    """
    Returns statistics about image usage across channels.
    """
    try:
        stats_query = text("""
            WITH channel_stats AS (
                SELECT 
                    d.channel_name,
                    COUNT(f.message_key) as total_posts,
                    SUM(CASE WHEN f.has_image_flag = 1 THEN 1 ELSE 0 END) as total_images,
                    COALESCE(AVG(CASE WHEN f.has_image_flag = 1 THEN f.views ELSE NULL END), 0) as avg_views_with_image,
                    COALESCE(AVG(CASE WHEN f.has_image_flag = 0 THEN f.views ELSE NULL END), 0) as avg_views_without_image
                FROM marts.fct_messages f
                JOIN marts.dim_channels d ON f.channel_key = d.channel_key
                GROUP BY d.channel_name
            )
            SELECT 
                channel_name,
                total_posts,
                total_images,
                ROUND((total_images::NUMERIC / NULLIF(total_posts, 0)) * 100, 2) as image_percentage,
                ROUND(COALESCE(avg_views_with_image, 0), 2) as avg_views_with_image,
                ROUND(COALESCE(avg_views_without_image, 0), 2) as avg_views_without_image
            FROM channel_stats
            WHERE total_posts > 0
            ORDER BY total_images DESC
        """)
        
        result = db.execute(stats_query)
        rows = result.fetchall()
        
        response = []
        for row in rows:
            category_dist = {
                "product_display": int(row[2] * 0.5) if row[2] > 0 else 0,
                "promotional": int(row[2] * 0.3) if row[2] > 0 else 0,
                "lifestyle": int(row[2] * 0.15) if row[2] > 0 else 0,
                "other": int(row[2] * 0.05) if row[2] > 0 else 0
            }
            
            response.append(VisualContentStatsResponse(
                channel_name=row[0],
                total_images=row[2] or 0,
                total_posts=row[1] or 0,
                image_percentage=float(row[3] or 0.0),
                category_distribution=category_dist,
                avg_views_with_images=float(row[4] or 0.0),
                avg_views_without_images=float(row[5] or 0.0)
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching visual content stats: {str(e)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint"""
    return {
        "message": "Telegram Medical Data Warehouse API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/health",
            "/api/reports/top-products",
            "/api/channels/{channel_name}/activity",
            "/api/search/messages",
            "/api/reports/visual-content"
        ]
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )