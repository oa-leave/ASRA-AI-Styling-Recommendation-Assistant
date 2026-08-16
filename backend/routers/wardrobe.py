from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.schemas.wardrobe import (
    ClothingAnalyzeTaskResponse,
    ClothingAnalyzeResponse,
    ClothingTaskUpdate,
    WardrobeCreate,
    WardrobeResponse,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from backend.services.image_service import (
    analyze_image,
    save_upload_image,
    validate_image_content,
)
from database.models import ClothingRecognitionTask, User, Wardrobe


router = APIRouter(prefix="/wardrobe", tags=["数字衣柜"])

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024


async def _read_upload_limited(file: UploadFile) -> bytes:
    if file.size is not None and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="图片文件不能超过5MB")
    content = b""
    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        content += chunk
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="图片文件不能超过5MB")
    return content


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


@router.post("/analyze-image", response_model=ClothingAnalyzeTaskResponse)
async def upload_clothes_image(
    file: UploadFile = File(...),
    auto_save: bool = Query(default=False),
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    original_name = file.filename or "clothes.jpg"
    content = await _read_upload_limited(file)
    try:
        validate_image_content(content)
    except ValueError:
        raise HTTPException(status_code=400, detail="图片文件无效")
    image_path = save_upload_image(content, original_name)
    candidate = analyze_image(image_path, original_name)

    task = ClothingRecognitionTask(
        user_id=current_user.id,
        image_path=candidate["image_path"],
        result=candidate,
        status="pending",
    )
    database.add(task)
    database.commit()
    database.refresh(task)

    if auto_save:
        new_clothes = Wardrobe(
            image_path=candidate["image_path"],
            recognition_status="confirmed",
            name=candidate["name"],
            category=candidate["category"],
            color=candidate["color"],
            season=candidate["season"],
            style=candidate["style"],
            color_tags=candidate["color_tags"],
            style_tags=candidate["style_tags"],
            fit_tags=candidate["fit_tags"],
            occasion_tags=candidate["occasion_tags"],
            user_id=current_user.id,
        )
        database.add(new_clothes)
        database.commit()
        database.refresh(new_clothes)
        candidate["recognition_status"] = "confirmed"
        candidate["clothes_id"] = new_clothes.id
        task.status = "confirmed"
        task.result = candidate
        database.commit()
        record_event(
            database,
            current_user.id,
            "wardrobe_analyze_auto_save",
            {"clothes_id": new_clothes.id},
        )

    return {
        "task_id": task.id,
        "status": task.status,
        "candidate": candidate,
    }


@router.put("/task/{task_id}")
def update_clothing_task(
    task_id: int,
    payload: ClothingTaskUpdate,
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    task = (
        database.query(ClothingRecognitionTask)
        .filter(ClothingRecognitionTask.id == task_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="识别任务不存在")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该识别任务")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="任务已确认，无法修改")

    result = task.result or {}
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        result[field] = value
    task.result = result
    database.commit()
    database.refresh(task)
    return {
        "task_id": task.id,
        "status": task.status,
        "candidate": task.result,
    }


@router.post("/confirm-task/{task_id}", status_code=201)
def confirm_clothing_task(
    task_id: int,
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    task = (
        database.query(ClothingRecognitionTask)
        .filter(ClothingRecognitionTask.id == task_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="识别任务不存在")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权确认该识别任务")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="任务已确认，无法重复确认")

    candidate = task.result or {}
    if not task.image_path:
        raise HTTPException(status_code=400, detail="缺少图片路径")

    new_clothes = Wardrobe(
        image_path=task.image_path,
        recognition_status="confirmed",
        name=candidate.get("name") or "识别衣物",
        category=candidate.get("category") or "上衣",
        color=candidate.get("color") or "未知",
        season=candidate.get("season") or "四季",
        style=candidate.get("style") or "休闲",
        color_tags=candidate.get("color_tags") or [],
        style_tags=candidate.get("style_tags") or [],
        fit_tags=candidate.get("fit_tags") or [],
        occasion_tags=candidate.get("occasion_tags") or [],
        user_id=current_user.id,
    )
    database.add(new_clothes)
    task.status = "confirmed"
    task.result = {**candidate, "recognition_status": "confirmed"}
    database.commit()
    database.refresh(new_clothes)
    record_event(
        database,
        current_user.id,
        "wardrobe_confirm_task",
        {"task_id": task.id, "clothes_id": new_clothes.id},
    )
    return {"message": "识别任务确认成功", "clothes_id": new_clothes.id}


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


@router.post("/upload-and-confirm", status_code=201)
async def upload_and_confirm_image(
    file: UploadFile = File(...),
    database: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """上传图片后自动识别并直接写入衣柜，无需手动复制结果。"""
    original_name = file.filename or "clothes.jpg"
    content = await _read_upload_limited(file)
    try:
        validate_image_content(content)
    except ValueError:
        raise HTTPException(status_code=400, detail="图片文件无效")
    image_path = save_upload_image(content, original_name)
    candidate = analyze_image(image_path, original_name)

    new_clothes = Wardrobe(
        image_path=candidate["image_path"],
        recognition_status="confirmed",
        name=candidate["name"],
        category=candidate["category"],
        color=candidate["color"],
        season=candidate["season"],
        style=candidate["style"],
        color_tags=candidate["color_tags"],
        style_tags=candidate["style_tags"],
        fit_tags=candidate["fit_tags"],
        occasion_tags=candidate["occasion_tags"],
        user_id=current_user.id,
    )
    database.add(new_clothes)
    database.commit()
    database.refresh(new_clothes)
    record_event(
        database,
        current_user.id,
        "wardrobe_auto_confirm",
        {"clothes_id": new_clothes.id},
    )
    return {"message": "图片已自动识别并入库", "clothes_id": new_clothes.id}


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

    updates = clothes.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(old_clothes, field, value)
    database.commit()
    database.refresh(old_clothes)
    record_event(
        database,
        current_user.id,
        "wardrobe_update",
        {"clothes_id": clothes_id},
    )
    return {"message": "衣物修改成功"}
