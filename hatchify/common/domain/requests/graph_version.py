from typing import Optional

from pydantic import Field

from hatchify.common.domain.requests.base import BasePageRequest


class PageGraphVersionRequest(BasePageRequest):
    graph_id: Optional[str] = Field(default=None, description="按 graph_id 过滤")
