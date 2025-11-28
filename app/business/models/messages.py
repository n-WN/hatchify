from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    func,
    Text,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.business.db.base import Base
from app.common.domain.enums.message_role import MessageRole


class MessageTable(Base):
    __tablename__ = "message"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
