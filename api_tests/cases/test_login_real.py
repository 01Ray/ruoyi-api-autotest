"""登录模块接口测试"""

import allure
import pytest

from common.http_client import HttpClient


@allure.epic("RuoYi 接口自动化")
@allure.feature("登录模块")
class TestLogin:
    """登录相关用例集"""

    @allure.story("验证码")
    @allure.title("获取验证码接口")
    @allure.description("无需 token，验证 captchaImage 接口可正常返回")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    @pytest.mark.login
    def test_get_captcha(self):
        client = HttpClient()
        result = client.get("/captchaImage")

        assert result["_status_code"] == 200
        assert result["code"] == 200
        assert result["msg"] == "操作成功"

    @allure.story("登录正向")
    @allure.title("admin 账号正确密码登录成功")
    @allure.description("使用默认 admin 账号登录，应返回 token")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.login
    def test_login_admin_success(self, env_config):
        client = HttpClient()
        token = client.login(env_config.admin.username, env_config.admin.password)

        assert token is not None
        assert len(token) > 100, "token 长度太短，疑似异常"
        assert client.token == token, "token 没保存到 client"

    @allure.story("登录正向")
    @allure.title("登录后用 token 调 /getInfo 验证身份")
    @allure.description("登录成功后，HttpClient 应自动注入 token，调用 /getInfo 应返回当前用户信息")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.login
    def test_login_then_get_user_info(self, env_config):
        client = HttpClient()
        client.login(env_config.admin.username, env_config.admin.password)

        user_info = client.get("/getInfo")

        assert user_info["code"] == 200
        assert user_info["user"]["userName"] == "admin"
        assert user_info["user"]["nickName"] == "若依"
        assert "admin" in user_info["roles"]

    @allure.story("登录反向")
    @allure.title("错误密码登录失败")
    @allure.description("使用错误密码登录，业务 code 应返回 500 且消息含错误提示")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.login
    def test_login_wrong_password(self):
        client = HttpClient()

        result = client.post("/login", json={
            "username": "admin",
            "password": "wrong_password"
        })

        assert result["_status_code"] == 200
        assert result["code"] == 500
        assert "密码" in result["msg"] or "错误" in result["msg"]

    @allure.story("登录反向")
    @allure.title("未登录访问受保护接口应返回 401")
    @allure.description("不带 token 直接调 /getInfo，业务层应拒绝并返回 401")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    @pytest.mark.login
    def test_get_info_without_token(self):
        client = HttpClient()
        result = client.get("/getInfo")

        assert result["code"] == 401