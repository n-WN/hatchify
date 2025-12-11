from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    func,
    Enum,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from hatchify.business.db.base import Base
from hatchify.common.domain.enums.execution_status import ExecutionStatus
from hatchify.common.domain.enums.execution_type import ExecutionType


class ExecutionTable(Base):
    """执行记录表 - 跟踪异步任务状态"""
    __tablename__ = "execution"

    # 执行ID (UUID hex)
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
    )

    # 执行类型 (webhook/graph_conversation/web_builder/deploy)
    type: Mapped[ExecutionType] = mapped_column(
        Enum(ExecutionType),
        nullable=False,
        index=True,
    )

    # 执行状态 (pending/running/completed/failed/cancelled)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus),
        nullable=False,
        default=ExecutionStatus.PENDING,
        index=True,
    )

    # 错误信息（失败时记录）
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # 关联信息（可选）
    graph_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    # 关联信息（可选）
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    # 时间字段
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
