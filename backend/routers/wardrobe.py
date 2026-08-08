from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.schemas.wardrobe import (
    ClothingAnalyzeResponse,
    WardrobeCreate,
    WardrobeResponse,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from backend.services.image_service import analyze_image, save_upload_image
from database.models import User, Wardrobe


router = APIRouter(prefix="/wardrobe", tags=["数字衣柜"])


@router.post("/add", status_code=201)
def add_clothes(
    clothes: WardrobeCreate,
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    new_clothes = Wardrobe(
        image_path=clothes.image_path,
        recognition_status=clothes.recognition_status,
        name=clothes.name,
        category=clothes.category,
        color=clothes.color,
        season=clothes.season,
        style=clothes.style,
        color_tags=clothes.color_tags,
        style_tags=clothes.style_tags,
        fit_tags=clothes.fit_tags,
        occasion_tags=clothes.occasion_tags,
        user_id=current_user.id,
    )
    database.add(new_clothes)
    database.commit()
    database.refresh(new_clothes)
    record_event(
        database,
        current_user.id,
        "wardrobe_add",
        {"clothes_id": new_clothes.id},
    )
    return {"message": "衣物添加成功", "clothes_id": new_clothes.id}


@router.post("/analyze-image", response_model=ClothingAnalyzeResponse)
async def upload_clothes_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    original_name = file.filename or "clothes.jpg"
    content = await file.read()
    image_path = save_upload_image(content, original_name)
    candidate = analyze_image(image_path, original_name)
    return candidate


@router.post("/confirm-image", status_code=201)
def confirm_image(
    clothes: WardrobeCreate,
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    if not clothes.image_path:
        raise HTTPException(status_code=400, detail="缺少图片路径")

    new_clothes = Wardrobe(
        image_path=clothes.image_path,
        recognition_status="confirmed",
        name=clothes.name,
        category=clothes.category,
        color=clothes.color,
        season=clothes.season,
        style=clothes.style,
        color_tags=clothes.color_tags,
        style_tags=clothes.style_tags,
        fit_tags=clothes.fit_tags,
        occasion_tags=clothes.occasion_tags,
        user_id=current_user.id,
    )
    database.add(new_clothes)
    database.commit()
    database.refresh(new_clothes)
    record_event(
        database,
        current_user.id,
        "wardrobe_confirm_image",
        {"clothes_id": new_clothes.id},
    )
    return {"message": "图片确认成功", "clothes_id": new_clothes.id}


@router.get("/", response_model=List[WardrobeResponse])
def list_clothes(
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return (
        database.query(Wardrobe)
        .filter(Wardrobe.user_id == current_user.id)
        .all()
    )


@router.delete("/{clothes_id}", status_code=200)
def delete_clothes(
    clothes_id: int,
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    clothes = (
        database.query(Wardrobe)
        .filter(Wardrobe.id == clothes_id)
        .first()
    )
    if clothes is None:
        raise HTTPException(status_code=404, detail="衣物不存在")
    if clothes.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该衣物")

    database.delete(clothes)
    database.commit()
    record_event(
        database,
        current_user.id,
        "wardrobe_delete",
        {"clothes_id": clothes_id},
    )
    return {"message": "衣物删除成功"}


@router.put("/{clothes_id}")
def update_clothes(
    clothes_id: int,
    clothes: WardrobeCreate,
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    old_clothes = (
        database.query(Wardrobe)
        .filter(Wardrobe.id == clothes_id)
        .first()
    )
    if old_clothes is None:
        raise HTTPException(status_code=404, detail="衣物不存在")
    if old_clothes.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该衣物")

    old_clothes.name = clothes.name
    old_clothes.image_path = clothes.image_path
    old_clothes.recognition_status = clothes.recognition_status
    old_clothes.category = clothes.category
    old_clothes.color = clothes.color
    old_clothes.season = clothes.season
    old_clothes.style = clothes.style
    old_clothes.color_tags = clothes.color_tags
    old_clothes.style_tags = clothes.style_tags
    old_clothes.fit_tags = clothes.fit_tags
    old_clothes.occasion_tags = clothes.occasion_tags
    database.commit()
    database.refresh(old_clothes)
    record_event(
        database,
        current_user.id,
        "wardrobe_update",
        {"clothes_id": clothes_id},
    )
    return {"message": "衣物修改成功"}
