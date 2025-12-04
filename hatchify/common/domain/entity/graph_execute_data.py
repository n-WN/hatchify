from typing import Dict, List, Any

from pydantic import BaseModel

from hatchify.common.domain.enums.storage_type import StorageType


class FileData(BaseModel):
    key: str
    mime: str
    name: str
    source: StorageType


class GraphExecuteData(BaseModel):
    jsons: Dict[str, Any]
    files: Dict[str, List[FileData]]
