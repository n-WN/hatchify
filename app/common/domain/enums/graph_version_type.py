from enum import Enum


class GraphVersionType(str, Enum):
    SNAPSHOT = "snapshot"
    DRAFT = "draft"
