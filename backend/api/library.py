"""Read-only Unified Library API."""
from fastapi import APIRouter, Query
from backend.services import library_service
router=APIRouter()
@router.get("/api/library")
def library(q:str="",source:str="all",item_type:str=Query("all",alias="type")):
 return library_service.list_items(q=q,source=source,item_type=item_type)
