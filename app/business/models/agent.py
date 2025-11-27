from datetime import datetime

from sqlalchemy import String, Text, DateTime, func, JSON, Enum
from sqlalchemy.orm import mapped_column, Mapped

from app.business.db.base import Base
from app.common.domain.enums.agent_category import AgentCategory


class AgentTable(Base):
    __tablename__ = "agent"

    id: Mapped[str] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    graph_id: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[AgentCategory] = mapped_column(Enum(AgentCategory), nullable=False)
    structured_output_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
