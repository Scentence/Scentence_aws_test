from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agent.archive_db import get_my_perfumes, add_my_perfume_logic, delete_my_perfume_logic, update_my_perfume_logic

# 프론트엔드가 호출하는 기존 경로(/users/...)를 그대로 지원하기 위해 prefix를 /users로 설정
router = APIRouter(prefix="/users", tags=["archive_fixed"])

class MyPerfumeRequest(BaseModel):
    perfume_id: int
    perfume_name: str
    register_status: str  # HAVE, HAD, RECOMMENDED
    preference: Optional[str] = "NEUTRAL"

class UpdatePerfumeStatusRequest(BaseModel):
    register_status: str
    preference: Optional[str] = None

@router.get("/{member_id}/perfumes")
def list_archive(member_id: int):
    """
    기존 프론트엔드 경로: GET /users/{member_id}/perfumes
    """
    return get_my_perfumes(member_id)

@router.post("/{member_id}/perfumes")
def register_archive(member_id: int, req: MyPerfumeRequest):
    """
    기존 프론트엔드 경로: POST /users/{member_id}/perfumes
    """
    result = add_my_perfume_logic(member_id, req.perfume_id, req.perfume_name, req.register_status, req.preference)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return {"status": "ok"}

@router.delete("/{member_id}/perfumes/{perfume_id}")
def delete_archive(member_id: int, perfume_id: int):
    """
    기존 프론트엔드 경로: DELETE /users/{member_id}/perfumes/{perfume_id}
    """
    result = delete_my_perfume_logic(member_id, perfume_id)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return {"status": "ok"}

@router.patch("/{member_id}/perfumes/{perfume_id}")
def update_my_perfume(member_id: int, perfume_id: int, req: UpdatePerfumeStatusRequest):
    """
    기존 프론트엔드 경로: PATCH /users/{member_id}/perfumes/{perfume_id}
    """
    result = update_my_perfume_logic(member_id, perfume_id, req.register_status, req.preference)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return {"status": "ok"}
