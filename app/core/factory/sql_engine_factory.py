import json

from sqlalchemy.ext.asyncio import create_async_engine

from app.common.domain.enums.db_type import DatabasePlatform
from app.common.settings.settings import get_hatchify_settings

settings = get_hatchify_settings()

db = settings.db


def create_sql_engine():
    match db.platform:
        case DatabasePlatform.SQLITE | _:
            sqlite_cfg = db.sqlite
            return create_async_engine(
                sqlite_cfg.url,
                echo=sqlite_cfg.echo,
                pool_pre_ping=sqlite_cfg.pool_pre_ping,
                connect_args=sqlite_cfg.connect_args,
                json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
            )
