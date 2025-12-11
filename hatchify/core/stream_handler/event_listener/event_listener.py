from abc import ABC, abstractmethod

from hatchify.common.domain.event.base_event import StreamEvent


class EventListener(ABC):
    """
    事件监听器接口

    所有事件监听器都需要实现此接口
    支持实例级注册，每个 StreamHandler 可以选择性启用监听器
    """

    @abstractmethod
    async def on_event(self, execution_id: str, event: StreamEvent):
        """
        事件回调方法

        Args:
            execution_id: 执行ID
            event: 流事件
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        监听器名称（用于日志和调试）

        Returns:
            监听器的唯一标识名称
        """
        pass