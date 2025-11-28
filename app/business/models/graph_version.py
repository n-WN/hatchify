from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    func,
    JSON,
    Integer,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.business.db.base import Base
from app.common.domain.enums.graph_version_type import GraphVersionType


class GraphVersionTable(Base):
    __tablename__ = "graph_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    # 对于 type=SNAPSHOT：是正式版本号（1,2,3...，业务层保证递增）# 对于 type=DRAFT：一般为 None，不占用版本号序列
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[GraphVersionType] = mapped_column(  # 区分正式快照 / 草稿快照
        Enum(GraphVersionType),
        nullable=False,
        default=GraphVersionType.SNAPSHOT,
    )
    spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parent_version_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    branch_session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "graph_id",
            "version",
            "type",
            name="uq_graph_version_per_graph_type"
        ),
    )
