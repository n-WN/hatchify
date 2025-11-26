from functools import lru_cache
from typing import Type, Tuple, Optional

from dotenv import load_dotenv
from pydantic import Field, BaseModel, model_validator
from pydantic_settings import (
    PydanticBaseSettingsSource,
    BaseSettings,
    YamlConfigSettingsSource,
    SettingsConfigDict,
)

from app.common.constants.constants import Constants
from app.common.domain.enums.storage_type import StorageType

load_dotenv(dotenv_path=Constants.Path.ENV_PATH)


class ProviderSettings(BaseSettings):
    model: str
    provider: Optional[str] = Field(default=None)


class ModelSettings(BaseSettings):
    """不同用途的模型配置"""
    spec_generator: ProviderSettings = Field(
        ...,
        description="用于生成 GraphSpec 架构的模型"
    )
    schema_extractor: ProviderSettings = Field(
        ...,
        description="用于从 Agent Instructions 提取 JSON Schema 的模型"
    )


class OpenDal(BaseModel):
    opendal_schema: str = Field(alias='schema')
    bucket: str
    folder: str | None
    root: str | None


class StorageSettings(BaseModel):
    platform: StorageType

    opendal: OpenDal | None

    @model_validator(mode='before')
    def clear_conflicting_settings(self):
        for key in [member for member in StorageType if member != self['platform']]:
            self[key] = None
        return self


class HatchifySettings(BaseModel):
    application: str
    models: ModelSettings | None = Field(default=None)
    storage: StorageSettings | None = Field(default=None)


class AppSettings(BaseSettings):
    hatchify: HatchifySettings | None = Field(default=None)

    model_config = SettingsConfigDict(
        yaml_file=Constants.Path.YAML_FILE_PATH,
        yaml_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache
def get_hatchify_settings():
    app_settings = AppSettings()
    return app_settings.hatchify
