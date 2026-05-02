"""
配置加载器
=========

功能：
1. 根据环境变量 ENV 自动加载对应的 YAML 配置（默认 dev）
2. 支持点号访问：config.base_url、config.admin.username
3. 启动时打印当前环境，方便调试

使用：
    from common.config import config

    print(config.base_url)
    print(config.admin.username)
"""

import os
from pathlib import Path

import yaml
from loguru import logger


# ===================================================================
# 路径工具
# ===================================================================
# __file__ 是当前文件 (common/config.py) 的路径
# .parent 上一级 = common/
# .parent 再上一级 = 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 配置文件目录
CONFIG_DIR = PROJECT_ROOT / "config"


# ===================================================================
# 让字典支持点号访问的辅助类
# ===================================================================
class DotDict(dict):
    """
    支持点号访问的 dict
    
    普通 dict: data["admin"]["username"]
    DotDict :  data.admin.username
    
    嵌套字典也会被自动转成 DotDict
    """

    def __init__(self, data: dict):
        super().__init__()
        for key, value in data.items():
            # 如果值是字典，递归转换
            if isinstance(value, dict):
                value = DotDict(value)
            self[key] = value

    def __getattr__(self, key):
        # 当通过 obj.key 访问时触发
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"配置中不存在 '{key}'，请检查 YAML 文件")

    def __setattr__(self, key, value):
        # 当通过 obj.key = value 赋值时触发
        self[key] = value


# ===================================================================
# 加载配置
# ===================================================================
def load_config() -> DotDict:
    """根据环境变量 ENV 加载对应配置文件"""
    
    # 读环境变量，默认 dev
    env = os.getenv("ENV", "dev").lower()
    
    config_file = CONFIG_DIR / f"{env}.yaml"
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"配置文件不存在：{config_file}\n"
            f"请确认 config/ 目录下有 {env}.yaml"
        )
    
    # 读 YAML
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    # 启动日志（只在第一次加载时打印）
    logger.info(f"加载配置：{config_file.name} | 环境: {env} | URL: {data.get('base_url')}")
    
    return DotDict(data)


# ===================================================================
# 全局唯一配置实例（单例模式）
# ===================================================================
# 模块第一次被 import 时执行 load_config()
# 之后所有地方 import config 都用同一个实例，不重复加载文件
config = load_config()