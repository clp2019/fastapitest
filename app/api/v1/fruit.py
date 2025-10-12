from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.fruit import Fruit, FruitCreate, FruitUpdate, ImageMeta, PaginatedFruits
from app.db.session import get_db
from app import crud
from app.core.cloudinary_client import upload_sync, destroy_sync
from fastapi.concurrency import run_in_threadpool
import io
from datetime import datetime

router = APIRouter(prefix="/api/v1/fruits", tags=["fruits"])


@router.get("/", response_model=PaginatedFruits)
async def list_fruits(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    q: Optional[str] = None,
    origin: Optional[str] = None,
    season: Optional[str] = None,
    sort_by: Optional[str] = "name_cn:asc",
    db: AsyncSession = Depends(get_db),
):
    items, total = await crud.list_fruits(db, page=page, per_page=per_page, q=q, origin=origin, season=season, sort_by=sort_by)
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{fruit_id}", response_model=Fruit)
async def get_fruit(fruit_id: str, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_fruit(db, fruit_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Fruit not found")
    return obj


@router.post("/", response_model=Fruit)
async def create_fruit(payload: FruitCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_fruit(db, payload.dict())


@router.post("/bulk_create", response_model=List[Fruit])
async def bulk_create(payload: List[FruitCreate], db: AsyncSession = Depends(get_db)):
    items = [p.dict() for p in payload]
    return await crud.bulk_create(db, items)


@router.put("/bulk_update")
async def bulk_update(payload: List[FruitUpdate], db: AsyncSession = Depends(get_db)):
    items = [p.dict() for p in payload]
    results = await crud.bulk_update(db, items)
    return {"results": results}


@router.delete("/bulk_delete")
async def bulk_delete(ids: List[str], db: AsyncSession = Depends(get_db)):
    deleted = await crud.bulk_delete(db, ids)
    return {"deleted": deleted}


# Image upload endpoint: upload file to Cloudinary and append image meta to fruit
@router.post("/{fruit_id}/images", response_model=ImageMeta)
async def upload_image(fruit_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    fruit = await crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(status_code=404, detail="Fruit not found")

    content = await file.read()
    # validate size (Cloudinary limit: 10 MB max image file size)
    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="Image too large; max 10MB allowed")

    # validate mime/type from filename extension (basic) and check megapixels using Pillow
    allowed = {"jpeg", "jpg", "png", "webp"}
    filename = file.filename or ""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported image type. Allowed: jpg, jpeg, png, webp")

    # check megapixels
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        width, height = img.size
        megapixels = (width * height) / 1_000_000
        if megapixels > 25:
            raise HTTPException(status_code=400, detail="Image too large in pixels; max 25MP allowed")
    except HTTPException:
        raise
    except Exception:
        # if pillow fails to parse, reject
        raise HTTPException(status_code=400, detail="Invalid image file")

    # upload in threadpool because cloudinary SDK is sync
    res = await run_in_threadpool(upload_sync, io.BytesIO(content), folder="fruits")
    image_meta = {
        "url": res.get("url") or res.get("secure_url"),
        "secure_url": res.get("secure_url"),
        "public_id": res.get("public_id"),
        "alt": file.filename,
        "source": "cloudinary",
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    images = fruit.images or []
    images.append(image_meta)
    fruit.images = images
    db.add(fruit)
    await db.commit()
    await db.refresh(fruit)
    return image_meta


@router.delete("/{fruit_id}/images")
async def delete_image(fruit_id: str, public_id: str, db: AsyncSession = Depends(get_db)):
    fruit = await crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(status_code=404, detail="Fruit not found")

    # destroy in threadpool
    await run_in_threadpool(destroy_sync, public_id)
    images = [img for img in (fruit.images or []) if img.get("public_id") != public_id]
    fruit.images = images
    db.add(fruit)
    await db.commit()
    await db.refresh(fruit)
    return {"ok": True}
