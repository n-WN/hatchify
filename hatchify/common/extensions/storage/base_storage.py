#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/10/11
# @Author  : .*?
# @Email   : amashiro2233@gmail.com
# @File    : base_storage
# @Software: PyCharm
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseStorage(ABC):

    @staticmethod
    @abstractmethod
    def get_client(**kwargs):
        raise NotImplementedError

    @abstractmethod
    async def save(self, key, data, mimetype='application/octet-stream'):
        raise NotImplementedError

    @abstractmethod
    async def upload_file(self, key, path, mimetype='application/octet-stream'):
        raise NotImplementedError

    @abstractmethod
    async def load_once(self, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def load_stream(self, key: str, chunk_size: int = 40960) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError

    @abstractmethod
    async def download(self, key, target_filepath):
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key):
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key):
        raise NotImplementedError

    @abstractmethod
    async def get_pre_signed_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError
