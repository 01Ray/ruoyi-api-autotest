"""
pytest 全局 fixture 文件
=======================

conftest.py 是 pytest 的"魔法文件"：
- 文件名必须叫 conftest.py（不能改）
- 不需要 import，pytest 自动发现
- 这里定义的 fixture 在同目录及子目录的所有用例里都能直接用

放在 api_tests/conftest.py 表示对 api_tests 下所有测试生效
"""

import pytest

from common.config import config


@pytest.fixture(scope="session")
def env_config():
    """
    返回当前环境的配置对象（整个测试会话只加载一次）
    
    用例里这么用：
        def test_xxx(env_config):
            print(env_config.base_url)
    """
    return config