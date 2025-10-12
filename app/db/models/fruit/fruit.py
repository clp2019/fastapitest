import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.types import JSON
from app.db.base import Base


# # 若使用 Postgres，可用 PG_UUID，否则 String(36)
# try:
#     UUIDCol = PG_UUID(as_uuid=False)
# except Exception:
#     UUIDCol = String(36)

class Fruit(Base):
    __tablename__ = "fruits"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name_cn = Column(String(128), nullable=False, index=True)
    images = Column(JSON, nullable=True)
    origin = Column(JSON, nullable=True)
    season = Column(JSON, nullable=True)
    nutritional_value = Column(JSON, nullable=True)
    suitable_for = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
