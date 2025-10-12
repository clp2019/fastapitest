from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, asc, desc, delete
from sqlalchemy.sql import func
from app.db.models.fruit import Fruit as FruitModel


async def get_fruit(db: AsyncSession, fruit_id: str) -> Optional[FruitModel]:
    q = await db.execute(select(FruitModel).where(FruitModel.id == fruit_id))
    return q.scalars().first()


async def list_fruits(db: AsyncSession, page: int = 1, per_page: int = 20,
                      q: str = None, origin: str = None, season: str = None,
                      sort_by: str = "name_cn:asc") -> Tuple[List[FruitModel], int]:
    stmt = select(FruitModel)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(FruitModel.name_cn.ilike(like), FruitModel.description.ilike(like)))
    if origin:
        stmt = stmt.where(FruitModel.origin.contains([origin]))
    if season:
        stmt = stmt.where(FruitModel.season.contains([season]))

    # sorting
    if sort_by:
        try:
            field, direction = sort_by.split(":")
            column = getattr(FruitModel, field, None)
            if column is not None:
                stmt = stmt.order_by(asc(column) if direction == "asc" else desc(column))
        except Exception:
            pass

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    items_q = await db.execute(stmt.offset((page - 1) * per_page).limit(per_page))
    items = items_q.scalars().all()
    return items, total


async def create_fruit(db: AsyncSession, data: dict) -> FruitModel:
    obj = FruitModel(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def bulk_create(db: AsyncSession, items: List[dict]) -> List[FruitModel]:
    objs = [FruitModel(**i) for i in items]
    db.add_all(objs)
    await db.commit()
    # refresh each
    for o in objs:
        await db.refresh(o)
    return objs


async def bulk_delete(db: AsyncSession, ids: List[str]) -> int:
    res = await db.execute(delete(FruitModel).where(FruitModel.id.in_(ids)))
    await db.commit()
    return res.rowcount if hasattr(res, 'rowcount') else 0


async def bulk_update(db: AsyncSession, items: List[dict]):
    results = []
    for it in items:
        fid = it.get("id")
        if not fid:
            results.append({"id": None, "ok": False, "msg": "missing id"})
            continue
        obj = await get_fruit(db, fid)
        if not obj:
            results.append({"id": fid, "ok": False, "msg": "not found"})
            continue
        for k, v in it.items():
            if k == "id":
                continue
            if hasattr(obj, k):
                setattr(obj, k, v)
        db.add(obj)
        results.append({"id": fid, "ok": True, "msg": "updated"})
    await db.commit()
    return results
