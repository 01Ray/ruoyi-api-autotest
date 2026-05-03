"""
pytest 全局 fixture 文件
=======================

提供：
- env_config: 当前环境配置（session 级，全局唯一）
- admin_client: 已登录的 admin 客户端（session 级，所有用例共享）
- auth_client: 函数级新建客户端（独立测试场景用）
"""

import pytest
from loguru import logger

from common.config import config
from common.http_client import HttpClient


@pytest.fixture(scope="session")
def env_config():
    """当前环境配置（整个会话只加载一次）"""
    return config


@pytest.fixture(scope="session")
def admin_client(env_config):
    """
    已登录的 admin 客户端（session 级共享）
    
    整个测试会话只登录一次，所有用例共享同一个 token
    显著提升测试速度，避免每个用例都登录的浪费
    """
    client = HttpClient()
    client.login(env_config.admin.username, env_config.admin.password)
    logger.info("Session 级 admin_client 已就绪")
    
    yield client
    
    # session 结束后清理
    logger.info("Session 结束，清理 admin_client")


@pytest.fixture(scope="function")
def auth_client(env_config):
    """
    函数级新建客户端（每个用例独立）
    
    用于需要"全新登录状态"的测试，比如测试登录接口本身、
    测试 token 失效场景等
    """
    client = HttpClient()
    client.login(env_config.admin.username, env_config.admin.password)
    return client