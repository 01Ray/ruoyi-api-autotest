"""
HTTP 客户端封装
==============

基于 requests.Session 封装，提供：
1. base_url 自动拼接（用例只关心 path）
2. token 自动管理（登录后所有请求自动带 Authorization 头）
3. 自动 JSON 解析（直接返回 dict）
4. 请求/响应统一日志
5. 超时统一控制

使用：
    from common.http_client import HttpClient

    client = HttpClient()
    client.login("admin", "admin123")
    
    user_info = client.get("/getInfo")
    print(user_info["user"]["nickName"])
"""

import json as json_lib

import requests
from loguru import logger

from common.config import config


class HttpClient:
    """RuoYi 接口测试专用 HTTP 客户端"""

    def __init__(self, base_url: str = None, timeout: int = None):
        """
        初始化客户端

        Args:
            base_url: 基础 URL，默认从配置文件读取
            timeout: 请求超时（秒），默认从配置文件读取
        """
        self.base_url = base_url or config.base_url
        self.timeout = timeout or config.timeout
        self.token = None

        # 用 Session 复用 TCP 连接（性能 + 自动管理 cookie）
        self.session = requests.Session()

        logger.info(f"HttpClient 初始化 | base_url: {self.base_url} | timeout: {self.timeout}s")

    # =========================================================
    # 核心：发请求的统一入口
    # =========================================================
    def request(self, method: str, path: str, **kwargs) -> dict:
        """
        统一请求入口，所有 get/post/put/delete 内部都走这里

        Args:
            method: HTTP 方法（GET/POST/PUT/DELETE）
            path: 接口路径（如 /login、/getInfo）
            **kwargs: 透传给 requests（json、params、data、headers 等）

        Returns:
            dict: 响应 JSON（自动 .json()）
        """
        url = f"{self.base_url}{path}"

        # 自动注入 token 到 Authorization 头
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        kwargs["headers"] = headers

        # 设置超时
        kwargs.setdefault("timeout", self.timeout)

        # 请求日志
        logger.info(f"==> {method} {url}")
        if kwargs.get("json"):
            logger.debug(f"    Body: {json_lib.dumps(kwargs['json'], ensure_ascii=False)}")
        if kwargs.get("params"):
            logger.debug(f"    Params: {kwargs['params']}")

        # 发请求
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接失败：{url} | {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时：{url} | {e}")
            raise

        # 响应日志
        logger.info(f"<== {response.status_code} {url}")
        
        # 解析 JSON
        try:
            result = response.json()
        except ValueError:
            logger.warning(f"响应不是合法 JSON：{response.text[:200]}")
            return {"_raw_text": response.text, "_status_code": response.status_code}

        logger.debug(f"    响应: {json_lib.dumps(result, ensure_ascii=False)[:300]}")

        # 把 HTTP 状态码也塞进结果，方便用例断言
        result["_status_code"] = response.status_code

        return result

    # =========================================================
    # 便捷方法（业务用例直接用这些）
    # =========================================================
    def get(self, path: str, params: dict = None, **kwargs) -> dict:
        """GET 请求"""
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, json: dict = None, **kwargs) -> dict:
        """POST 请求（JSON body）"""
        return self.request("POST", path, json=json, **kwargs)

    def put(self, path: str, json: dict = None, **kwargs) -> dict:
        """PUT 请求"""
        return self.request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> dict:
        """DELETE 请求"""
        return self.request("DELETE", path, **kwargs)

    # =========================================================
    # 业务方法：登录（拿 token）
    # =========================================================
    def login(self, username: str, password: str) -> str:
        """
        登录拿 token，并自动保存到 self.token，之后所有请求自动带

        Args:
            username: 用户名
            password: 密码

        Returns:
            str: token

        Raises:
            AssertionError: 登录失败
        """
        result = self.post("/login", json={
            "username": username,
            "password": password
        })

        # 校验登录成功
        assert result.get("code") == 200, f"登录失败: {result.get('msg')}"
        assert result.get("token"), "登录响应里没有 token"

        self.token = result["token"]
        logger.info(f"登录成功 | 用户: {username} | token: {self.token[:30]}...")

        return self.token

    def logout(self):
        """登出（调用 RuoYi 的 logout 接口 + 清本地 token）"""
        if self.token:
            self.post("/logout")
            self.token = None
            logger.info("登出成功")