from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime

class Nutrition(BaseModel):
    calories_kcal: Optional[float]
    protein_g: Optional[float]
    fat_g: Optional[float]
    carbs_g: Optional[float]
    sugar_g: Optional[float]
    fiber_g: Optional[float]
    vitamin_c_mg: Optional[float]
    potassium_mg: Optional[float]

class ImageMeta(BaseModel):
    url: HttpUrl
    secure_url: Optional[HttpUrl]
    public_id: Optional[str]
    alt: Optional[str]
    source: Optional[str]
    uploaded_at: Optional[datetime]

class FruitBase(BaseModel):
    name_cn: str
    images: Optional[List[ImageMeta]] = []
    origin: Optional[List[str]] = []
    season: Optional[List[str]] = []
    nutritional_value: Optional[Nutrition]
    suitable_for: Optional[List[str]] = []
    description: Optional[str]

class FruitCreate(FruitBase):
    pass

class FruitUpdate(FruitBase):
    id: str

class Fruit(FruitBase):
    id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    class Config:
        orm_mode = True

class PaginatedFruits(BaseModel):
    items: List[Fruit]
    total: int
    page: int
    per_page: int
