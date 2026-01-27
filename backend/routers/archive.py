from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agent.archive_db import get_my_perfumes, add_my_perfume, delete_my_perfume

router = APIRouter(prefix="/archive", tags=["archive"])

class ArchiveRequest(BaseModel):
    member_id: int
    perfume_id: int
    status: Optional[str] = "HAVE"

@router.get("/perfumes/{member_id}")
def list_archive(member_id: int):
    """
    내 향수 목록 조회
    """
    results = get_my_perfumes(member_id)
    return {"perfumes": results}

@router.post("/perfumes")
def register_archive(req: ArchiveRequest):
    """
    내 향수 등록
    """
    result = add_my_perfume(req.member_id, req.perfume_id, req.status)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.delete("/perfumes/{member_id}/{perfume_id}")
def delete_archive(member_id: int, perfume_id: int):
    """
    내 향수 삭제
    """
    result = delete_my_perfume(member_id, perfume_id)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result
