"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., description="Search keyword or phrase", min_length=1)
    limit: int = Field(20, description="Number of results to return", ge=1, le=100)


class TopProductResponse(BaseModel):
    """Top products response"""
    product: str = Field(..., description="Product name/term")
    mention_count: int = Field(..., description="Number of mentions")
    channels: List[str] = Field(..., description="Channels where mentioned")
    percentage: float = Field(..., description="Percentage of total mentions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product": "paracetamol",
                "mention_count": 45,
                "channels": ["Lobelia pharmacy", "Medical Information"],
                "percentage": 12.5
            }
        }


class ChannelActivityResponse(BaseModel):
    """Channel activity response"""
    channel_name: str = Field(..., description="Channel name")
    total_posts: int = Field(..., description="Total posts")
    avg_views: float = Field(..., description="Average views per post")
    avg_forwards: float = Field(..., description="Average forwards per post")
    first_post_date: datetime = Field(..., description="First post date")
    last_post_date: datetime = Field(..., description="Last post date")
    posts_per_day: float = Field(..., description="Posts per day")
    top_issues: List[str] = Field(..., description="Top issues mentioned")
    activity_trend: List[Dict[str, Any]] = Field(..., description="Daily activity trend")
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_name": "Lobelia pharmacy and cosmetics",
                "total_posts": 500,
                "avg_views": 250,
                "avg_forwards": 15,
                "first_post_date": "2025-01-01T00:00:00",
                "last_post_date": "2025-12-31T00:00:00",
                "posts_per_day": 1.37,
                "top_issues": ["product pricing", "availability", "quality"],
                "activity_trend": [
                    {"date": "2025-01-01", "posts": 5},
                    {"date": "2025-01-02", "posts": 3}
                ]
            }
        }


class MessageSearchResponse(BaseModel):
    """Message search response"""
    message_id: int = Field(..., description="Message ID")
    channel_name: str = Field(..., description="Channel name")
    message_date: datetime = Field(..., description="Message date")
    message_text: str = Field(..., description="Message text")
    views: int = Field(..., description="Number of views")
    forwards: int = Field(..., description="Number of forwards")
    has_image: bool = Field(..., description="Whether message has image")
    image_category: Optional[str] = Field(None, description="Image category if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": 12345,
                "channel_name": "Lobelia pharmacy and cosmetics",
                "message_date": "2025-01-15T10:30:00",
                "message_text": "New shipment of paracetamol available!",
                "views": 350,
                "forwards": 12,
                "has_image": True,
                "image_category": "product_display"
            }
        }


class VisualContentStatsResponse(BaseModel):
    """Visual content statistics response"""
    channel_name: str = Field(..., description="Channel name")
    total_images: int = Field(..., description="Total images")
    total_posts: int = Field(..., description="Total posts")
    image_percentage: float = Field(..., description="Percentage of posts with images")
    category_distribution: Dict[str, int] = Field(..., description="Distribution by category")
    avg_views_with_images: float = Field(..., description="Average views for posts with images")
    avg_views_without_images: float = Field(..., description="Average views for posts without images")
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_name": "Lobelia pharmacy and cosmetics",
                "total_images": 150,
                "total_posts": 500,
                "image_percentage": 30.0,
                "category_distribution": {
                    "product_display": 80,
                    "promotional": 40,
                    "lifestyle": 20,
                    "other": 10
                },
                "avg_views_with_images": 320,
                "avg_views_without_images": 180
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[str] = Field(None, description="Additional error details")