"""
YAML 用例数据加载器
=================

提供从 api_tests/data/ 下加载 YAML 用例的工具。

使用：
    from common.yaml_loader import load_cases

    cases = load_cases("role_query_cases.yaml")
    # cases 是一个 list[dict]，每个 dict 是一个用例
"""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger


# 用例数据根目录
DATA_DIR = Path(__file__).parent.parent / "api_tests" / "data"


def load_cases(filename: str) -> list[dict]:
    """
    加载指定 YAML 文件下的所有用例

    Args:
        filename: 文件名，相对 api_tests/data/ 目录
                 比如 "role_query_cases.yaml" 或 "user/list_cases.yaml"

    Returns:
        list[dict]: 用例数据列表

    Raises:
        FileNotFoundError: 文件不存在
        yaml.YAMLError: YAML 解析错误
    """
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"用例文件不存在: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        cases = yaml.safe_load(f)

    if not isinstance(cases, list):
        raise ValueError(f"YAML 顶层必须是 list（用例数组）: {file_path}")

    logger.info(f"加载用例文件: {filename} | 共 {len(cases)} 个用例")
    return cases


def get_case_id(case: dict) -> str:
    """
    从用例中提取 ID，用作 pytest 参数化的 ids
    
    pytest -v 时显示用例标题而不是 case0/case1
    """
    return case.get("case_id", case.get("title", "unnamed"))


# ============================================================
# 自定义断言执行器（处理 expected.asserts 列表）
# ============================================================
def assert_jsonpath(actual: Any, jsonpath_expr: str, op: str, expected: Any):
    """
    根据 jsonpath 表达式 + 操作符 + 期望值，断言响应数据

    支持的操作符：
        ==     精确相等
        !=     不等
        >, >=  大于（用于数字）
        <, <=  小于
        in         actual 包含在 expected 列表中
        contains   actual 中包含 expected 元素
        not_contains  反向

    使用：
        assert_jsonpath(response, "$.total", ">=", 2)
        assert_jsonpath(response, "$.code", "==", 200)
    """
    from jsonpath_ng import parse

    expr = parse(jsonpath_expr)
    matches = [m.value for m in expr.find(actual)]

    # jsonpath 没匹配到任何值
    if not matches:
        raise AssertionError(
            f"jsonpath 未匹配到任何值: {jsonpath_expr}\n"
            f"响应数据: {actual}"
        )

    # 操作符判断
    if op == "==":
        # 单值精确比较
        actual_value = matches[0] if len(matches) == 1 else matches
        assert actual_value == expected, (
            f"jsonpath {jsonpath_expr} 期望 == {expected}，实际 {actual_value}"
        )
    elif op == "!=":
        actual_value = matches[0] if len(matches) == 1 else matches
        assert actual_value != expected, (
            f"jsonpath {jsonpath_expr} 期望 != {expected}，实际 {actual_value}"
        )
    elif op == ">=":
        assert matches[0] >= expected, (
            f"jsonpath {jsonpath_expr} 期望 >= {expected}，实际 {matches[0]}"
        )
    elif op == ">":
        assert matches[0] > expected, (
            f"jsonpath {jsonpath_expr} 期望 > {expected}，实际 {matches[0]}"
        )
    elif op == "<=":
        assert matches[0] <= expected, (
            f"jsonpath {jsonpath_expr} 期望 <= {expected}，实际 {matches[0]}"
        )
    elif op == "<":
        assert matches[0] < expected, (
            f"jsonpath {jsonpath_expr} 期望 < {expected}，实际 {matches[0]}"
        )
    elif op == "contains":
        # actual 是数组，期望数组中包含 expected 元素
        assert expected in matches, (
            f"jsonpath {jsonpath_expr} 期望包含 {expected}，实际 {matches}"
        )
    elif op == "not_contains":
        assert expected not in matches, (
            f"jsonpath {jsonpath_expr} 期望不包含 {expected}，实际 {matches}"
        )
    elif op == "in":
        # actual 单值，应该在 expected 列表中
        assert matches[0] in expected, (
            f"jsonpath {jsonpath_expr} 期望在 {expected} 中，实际 {matches[0]}"
        )
    else:
        raise ValueError(f"不支持的操作符: {op}")