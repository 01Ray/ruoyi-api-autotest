"""冒烟测试 + 配置加载验证"""

import pytest


def test_hello():
    """1+1 是否还等于 2"""
    assert 1 + 1 == 2


def test_dict_assertion():
    """字典断言示例"""
    response = {"code": 200, "msg": "操作成功", "data": {"id": 1}}
    assert response["code"] == 200
    assert response["data"]["id"] == 1


# ============================================================
# 验证配置加载（Task 2.3 重点）
# ============================================================
@pytest.mark.smoke
def test_config_loaded(env_config):
    """配置文件能被正确加载"""
    # 注意：这里 env_config 是从 conftest.py 自动注入的
    assert env_config.env == "dev"
    assert env_config.base_url.startswith("http://")
    assert env_config.timeout > 0


@pytest.mark.smoke
def test_admin_account(env_config):
    """admin 账号配置存在"""
    assert env_config.admin.username == "admin"
    assert env_config.admin.password == "admin123"


@pytest.mark.smoke
def test_database_config(env_config):
    """数据库配置存在"""
    assert env_config.database.host == "localhost"
    assert env_config.database.port == 3306
    assert env_config.database.database == "ry-vue"