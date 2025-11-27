from pydantic import BaseModel

from app.common.domain.requests.base import BasePageRequest


class PageGraphRequest(BasePageRequest):
    ...


class AddGraphRequest(BaseModel):
    ...


class UpdateGraphRequest(BaseModel):
    ...
