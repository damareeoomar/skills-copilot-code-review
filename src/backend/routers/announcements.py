"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict) -> Dict:
    """Convert MongoDB document to JSON-serializable format"""
    if announcement:
        announcement["_id"] = str(announcement["_id"])
    return announcement


@router.get("")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (not expired, and started if start_date is set)"""
    current_time = datetime.utcnow().isoformat()
    
    # Query for announcements that:
    # 1. Have not expired (expiration_date >= current_time)
    # 2. Either have no start_date OR start_date <= current_time
    query = {
        "expiration_date": {"$gte": current_time},
        "$or": [
            {"start_date": None},
            {"start_date": {"$lte": current_time}}
        ]
    }
    
    announcements = list(announcements_collection.find(query))
    return [serialize_announcement(a) for a in announcements]


@router.get("/all")
def get_all_announcements(username: str = Query(...)) -> List[Dict[str, Any]]:
    """Get all announcements (for management). Requires authentication."""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    return [serialize_announcement(a) for a in announcements]


@router.post("")
def create_announcement(
    message: str,
    expiration_date: str,
    username: str = Query(...),
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement. Requires authentication."""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= exp_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Start date must be before expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Validate expiration date is in the future
    if exp_date <= datetime.utcnow():
        raise HTTPException(
            status_code=400, 
            detail="Expiration date must be in the future"
        )
    
    # Create announcement
    current_time = datetime.utcnow().isoformat()
    announcement = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_at": current_time,
        "updated_at": current_time
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    username: str = Query(...),
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an existing announcement. Requires authentication."""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= exp_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Start date must be before expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Update announcement
    current_time = datetime.utcnow().isoformat()
    update_data = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "updated_at": current_time
    }
    
    announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    updated = announcements_collection.find_one({"_id": obj_id})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    username: str = Query(...)
) -> Dict[str, str]:
    """Delete an announcement. Requires authentication."""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
