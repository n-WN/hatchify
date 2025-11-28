from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.business.db.base import Base


class SessionTable(Base):
    __tablename__ = "session"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
    )

    graph_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
