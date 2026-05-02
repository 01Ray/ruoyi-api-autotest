"""第一个真实接口测试 - 验证 HttpClient 封装"""

import pytest

from common.http_client import HttpClient


@pytest.mark.smoke
@pytest.mark.login
def test_get_captcha():
    """获取验证码接口（无需 token）"""
    client = HttpClient()
    result = client.get("/captchaImage")

    # HTTP 层
    assert result["_status_code"] == 200
    # 业务层
    assert result["code"] == 200
    assert result["msg"] == "操作成功"


@pytest.mark.smoke
@pytest.mark.login
def test_login_admin_success(env_config):
    """admin 账号登录成功"""
    client = HttpClient()
    token = client.login(env_config.admin.username, env_config.admin.password)

    assert token is not None
    assert len(token) > 100, "token 长度太短，疑似异常"
    assert client.token == token, "token 没保存到 client"


@pytest.mark.smoke
@pytest.mark.login
def test_login_then_get_user_info(env_config):
    """登录后用 token 调 /getInfo（验证 token 自动注入）"""
    client = HttpClient()
    client.login(env_config.admin.username, env_config.admin.password)

    user_info = client.get("/getInfo")

    assert user_info["code"] == 200
    assert user_info["user"]["userName"] == "admin"
    assert user_info["user"]["nickName"] == "若依"
    assert "admin" in user_info["roles"]


@pytest.mark.smoke
@pytest.mark.login
def test_login_wrong_password():
    """密码错误，登录失败"""
    client = HttpClient()
    
    result = client.post("/login", json={
        "username": "admin",
        "password": "wrong_password"
    })

    # HTTP 层 200，业务层失败
    assert result["_status_code"] == 200
    assert result["code"] == 500
    assert "密码" in result["msg"] or "错误" in result["msg"]


@pytest.mark.smoke
@pytest.mark.login
def test_get_info_without_token():
    """不带 token 调 /getInfo，应该 401"""
    client = HttpClient()
    # 注意：这里不调 login，直接 GET
    result = client.get("/getInfo")

    assert result["code"] == 401