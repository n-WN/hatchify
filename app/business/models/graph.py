from datetime import datetime

from sqlalchemy import String, JSON, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.business.db.base import Base


class GraphTable(Base):
    __tablename__ = "graph"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    entry_point: Mapped[str] = mapped_column(String(255), nullable=False)
    agents: Mapped[list] = mapped_column(JSON, nullable=True)
    functions: Mapped[list] = mapped_column(JSON, nullable=True)
    edges: Mapped[list] = mapped_column(JSON, nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
