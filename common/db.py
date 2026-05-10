"""
数据库客户端封装
==============

提供 RuoYi MySQL 数据库的连接和查询能力，用于接口测试后的数据落地验证。

设计原则：
1. 只读取，不修改 —— 测试代码不应该绕过接口直接改数据库
2. 连接池复用 —— 避免每次查询都建连接
3. 自动 dict 化 —— 查询结果用列名做 key，比元组好用 N 倍
4. 统一日志 —— SQL 执行可追溯

使用：
    from common.db import db

    user = db.fetch_one("SELECT * FROM sys_user WHERE user_id = %s", (1,))
    print(user["user_name"])  # admin
"""

import pymysql
from loguru import logger
from pymysql.cursors import DictCursor

from common.config import config


class DbClient:
    """RuoYi MySQL 数据库客户端"""

    def __init__(self, db_config=None):
        """初始化连接配置（不立即连接）"""
        self.db_config = db_config or config.database
        self._connection = None
        logger.info(
            f"DbClient 初始化 | host: {self.db_config.host}:{self.db_config.port}"
            f" | database: {self.db_config.database}"
        )

    def _get_connection(self):
        """
        获取连接（懒加载 + 自动重连）
        
        如果连接断开（MySQL 默认 8 小时空闲超时），自动重建
        """
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                user=self.db_config.user,
                password=self.db_config.password,
                database=self.db_config.database,
                charset=self.db_config.charset,
                cursorclass=DictCursor,        # ← 关键：返回 dict 而不是元组
                autocommit=True,                # 测试场景不需要手动 commit
            )
        return self._connection

    def fetch_one(self, sql: str, params: tuple = None) -> dict | None:
        """
        查询单条记录
        
        Args:
            sql: SQL 语句，用 %s 占位
            params: 参数元组
        
        Returns:
            dict | None: 查到返回 dict，没查到返回 None
        
        示例：
            user = db.fetch_one(
                "SELECT user_name, nick_name FROM sys_user WHERE user_id = %s",
                (1,)
            )
            # {"user_name": "admin", "nick_name": "若依"}
        """
        conn = self._get_connection()
        with conn.cursor() as cursor:
            logger.debug(f"SQL: {sql} | params: {params}")
            cursor.execute(sql, params)
            result = cursor.fetchone()
            logger.debug(f"结果: {result}")
            return result

    def fetch_all(self, sql: str, params: tuple = None) -> list[dict]:
        """查询多条记录"""
        conn = self._get_connection()
        with conn.cursor() as cursor:
            logger.debug(f"SQL: {sql} | params: {params}")
            cursor.execute(sql, params)
            results = cursor.fetchall()
            logger.debug(f"结果: 共 {len(results)} 条")
            return results

    def count(self, sql: str, params: tuple = None) -> int:
        """
        快速 count 查询
        
        SQL 必须返回单一数字（用 SELECT COUNT(*) 之类）
        """
        result = self.fetch_one(sql, params)
        if not result:
            return 0
        # 取第一个字段的值
        return list(result.values())[0]

    def close(self):
        """关闭连接（一般不用手动调，session 结束自动关）"""
        if self._connection and self._connection.open:
            self._connection.close()
            logger.info("数据库连接已关闭")


# 全局单例（模块级别，不重复创建）
db = DbClient() 