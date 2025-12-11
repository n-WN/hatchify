from enum import Enum


class ExecutionStatus(str, Enum):
    """
    执行状态 - 对应 StreamEvent 生命周期

    生命周期映射：
    - PENDING: 任务创建但未开始
    - RUNNING: 收到 StartEvent
    - COMPLETED: 收到 DoneEvent(reason="completed")
    - CANCELLED: 收到 DoneEvent(reason="cancel") 或 CancelEvent
    - FAILED: 收到 DoneEvent(reason="error") 或 ErrorEvent
    """
    PENDING = "pending"          # 等待中
    RUNNING = "running"          # 处理中 (StartEvent)
    COMPLETED = "completed"      # 完成 (DoneEvent: completed)
    FAILED = "failed"            # 失败 (DoneEvent: error / ErrorEvent)
    CANCELLED = "cancelled"      # 已取消 (DoneEvent: cancel / CancelEvent)