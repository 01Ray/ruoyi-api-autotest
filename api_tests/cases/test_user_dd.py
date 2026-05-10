"""
用户管理 - 数据驱动测试
=====================

所有用例数据来自 api_tests/data/user_query_cases.yaml
单一测试函数，配合 pytest.parametrize 自动生成 N 个用例
"""

import allure
import pytest

from common.yaml_loader import load_cases, get_case_id, assert_jsonpath


# ============================================================
# 用例数据加载（模块加载时执行一次）
# ============================================================
USER_QUERY_CASES = load_cases("user_query_cases.yaml")

@allure.epic("RuoYi 接口自动化")
@allure.feature("用户管理")
@allure.story("数据驱动 - 查询")
class TestUserQueryDataDriven:
    """用户查询用例 - 全部由 YAML 驱动"""

    @pytest.mark.parametrize(
        "case",
        USER_QUERY_CASES,
        ids=[c["title"] for c in USER_QUERY_CASES],
    )
    def test_user_query(self, admin_client, case):
        """
        通用查询用例
        
        每条 YAML 数据生成一个独立测试用例，pytest 报告里清晰显示
        """
        # === 动态设置 Allure 元数据 ===
        allure.dynamic.title(case["title"])
        allure.dynamic.description(case.get("description", ""))
        allure.dynamic.severity(
            getattr(allure.severity_level, case.get("severity", "normal").upper())
        )

        # === 发送请求 ===
        req = case["request"]
        method = req["method"].upper()
        path = req["path"]

        if method == "GET":
            result = admin_client.get(path, params=req.get("params") or {})
        elif method == "POST":
            result = admin_client.post(path, json=req.get("json"))
        elif method == "PUT":
            result = admin_client.put(path, json=req.get("json"))
        elif method == "DELETE":
            result = admin_client.delete(path)
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")

        # === 断言 ===
        expected = case["expected"]

        # 1. HTTP 状态码
        assert result["_status_code"] == expected["status_code"], (
            f"HTTP 状态码不符 | 期望: {expected['status_code']} | 实际: {result['_status_code']}"
        )

        # 2. 业务 code
        assert result["code"] == expected["code"], (
            f"业务 code 不符 | 期望: {expected['code']} | 实际: {result['code']}"
        )

        # 3. 自定义 jsonpath 断言
        for a in expected.get("asserts", []) or []:
            assert_jsonpath(
                result,
                jsonpath_expr=a["jsonpath"],
                op=a["op"],
                expected=a["value"],
            )