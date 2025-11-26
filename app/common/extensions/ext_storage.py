#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/10/11
# @Author  : .*?
# @Email   : amashiro2233@gmail.com
# @File    : ext_storage
# @Software: PyCharm
from collections.abc import Generator
from typing import Union, Type

from loguru import logger

from app.common.domain.enums.storage_type import StorageType
from app.common.extensions.storage.base_storage import BaseStorage
from app.common.extensions.storage.opendal import OpenDalStorage
from app.common.settings.settings import get_hatchify_settings

settings = get_hatchify_settings()


class Storage:

    def __init__(self):
        self.storage_runner = None

    async def init_app(self) -> None:
        storage_constructor = self.get_storage_factory(settings.storage.platform)
        self.storage_runner = storage_constructor()

    @staticmethod
    def get_storage_factory(storage_type: StorageType) -> Type[BaseStorage]:
        match storage_type:
            case StorageType.LOCAL | _:
                return OpenDalStorage

    async def save(self, key, data, mimetype='application/octet-stream'):
        try:
            await self.storage_runner.save(key, data, mimetype)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise e

    async def upload_file(self, key, path, mimetype='application/octet-stream'):
        try:
            await self.storage_runner.upload_file(key, path, mimetype)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise e

    async def download(self, key, target_filepath):
        try:
            await self.storage_runner.download(key, target_filepath)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise e

    async def load(self, key: str, stream: bool = False) -> Union[bytes, Generator]:
        try:
            if stream:
                return await self.load_stream(key)
            else:
                return await self.load_once(key)
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            raise e

    async def load_once(self, key: str) -> bytes:
        try:
            return await self.storage_runner.load_once(key)
        except Exception as e:
            logger.error(f"Failed to load_once file: {e}")
            raise e

    async def load_stream(self, key: str, chunk_size: int = 40960) -> Generator:
        try:
            return await self.storage_runner.load_stream(key, chunk_size)
        except Exception as e:
            logger.error(f"Failed to load_stream file: {e}")
            raise e

    async def download(self, key, target_filepath):  # type: ignore
        try:
            await self.storage_runner.download(key, target_filepath)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise e

    async def exists(self, key):
        try:
            return await self.storage_runner.exists(key)
        except Exception as e:
            logger.error(f"Failed to check file exists: {e}")
            raise e

    async def delete(self, key):
        try:
            return await self.storage_runner.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise e

    async def get_pre_signed_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            return await self.storage_runner.get_pre_signed_url(key, expires_in=expires_in)
        except Exception as e:
            raise e

    def __getattr__(self, item):
        if self.storage_runner is None:
            raise RuntimeError("Storage clients is not initialized. Call init_app first.")
        return getattr(self.storage_runner, item)


storage_client = Storage()


async def init_storage():
    logger.info("Initializing storage")
    await storage_client.init_app()
    logger.info("Initialized storage")
