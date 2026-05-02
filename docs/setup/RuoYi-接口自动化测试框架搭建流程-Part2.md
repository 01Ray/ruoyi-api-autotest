# RuoYi 接口自动化测试框架搭建流程（Part 2）

> **承接 Part 1**：上一份文档完成了 RuoYi-Vue 后端在 Windows 本地的部署与启动。
> **本文档目标**：从零搭建独立的接口自动化测试框架（pytest + venv + 多环境配置），完成 Git 初始化与首次推送 GitHub。
>
> **完成本文档后你将拥有**：
> - 一个独立的、企业级目录结构的 Python 测试仓库
> - venv 隔离的 Python 环境 + 11 个核心依赖
> - 多环境配置加载机制（dev/test/prod）
> - 5 个绿色冒烟测试 + 完整的 git 历史
> - 一个 GitHub 公开仓库（可放进简历）

---

## 0. 前置检查

开始前确认 Part 1 的成果都在：

```powershell
# 1. RuoYi 后端能跑（不需要常开，但配置文件要在）
ls D:\learning\ruoyi-ui-autotest\RuoYi-Vue\ruoyi-admin\src\main\resources\application-druid.yml

# 2. MySQL 服务在
Get-Service MySQL84

# 3. Redis 服务在
redis-cli ping
```

> 后端不需要全程运行——本文档主要搭测试框架本身，到 Task 2.6 写真实接口用例时才需要后端在跑。

### 还需要的工具

| 工具 | 用途 | 验证命令 |
|---|---|---|
| Python 3.11+ | 测试框架运行时 | `python --version` |
| pip 24+ | 包管理 | `pip --version` |
| Git 2.x+ | 版本控制 | `git --version` |
| VS Code | 编辑器（推荐） | 命令面板能用 |
| GitHub 账号 | 远程仓库 | 浏览器登录 |

---

## 1. 整体设计与决策

### 1.1 仓库选型：独立仓库还是同仓库？

**推荐：独立仓库**（本文档采用）

| 维度 | 同仓库（autotest 目录在 RuoYi-Vue 里）| 独立仓库（推荐） |
|---|---|---|
| 版本管理 | 测试代码跟着业务版本走 | 测试代码独立演进 |
| CI 触发 | 业务改动触发测试构建 | 测试可独立调度 |
| 权限控制 | 测试团队需要业务仓库权限 | 测试团队独立权限 |
| 多项目复用 | 无法复用 | 一套框架可测多个项目 |
| 简历呈现 | 混在业务代码里 | 作为独立作品集 |

**企业实际情况**：99% 的成熟测试团队都是独立仓库。

### 1.2 Python 环境管理：venv vs 原生 vs conda

**推荐：venv**（Python 3 自带，零安装成本）

| 方案 | 优点 | 缺点 |
|---|---|---|
| **原生 Python** | 上手快 | 多项目依赖冲突，无法复现环境 |
| **venv（推荐）** | Python 自带，企业标准 | 需要每次激活 |
| **conda** | 包管理强大 | 体积大（500MB+），主要用于数据科学 |

**venv 核心规则**：
- 每个项目一个 venv
- venv 不进 git（.gitignore 必须忽略）
- 依赖只记在 `requirements.txt`
- 把它当一次性的——出问题直接删了重建

### 1.3 技术栈

| 类别 | 选型 | 理由 |
|---|---|---|
| 测试框架 | **pytest 8.x** | 国内外大厂主流 |
| HTTP 客户端 | **requests** | 简单稳定 |
| 数据驱动 | **PyYAML + jsonpath-ng** | YAML 易读，jsonpath 处理复杂响应 |
| 日志 | **loguru** | 比 logging 简单 100 倍 |
| 数据生成 | **Faker** | 中文姓名、手机号、地址等 |
| 数据库验证 | **PyMySQL** | 接口测完查库验证 |
| 报告 | **allure-pytest** | 企业标配，支持历史趋势 |
| 代码质量 | **ruff** | 替代 flake8 + black，速度快 10 倍 |
| 并行 | **pytest-xdist** | `pytest -n 4` 多进程并行 |

---

## 2. Task 2.1：建仓库 + venv + 目录骨架

### 2.1.1 在 GitHub 建空仓库

1. 浏览器打开 [GitHub](https://github.com)，登录账号
2. 右上角 **+** → **New repository**
3. 填写：
   - Repository name：**`ruoyi-api-autotest`**（推荐用 `-api-` 明确职责）
   - Description：`RuoYi-Vue 接口自动化测试框架（pytest + Allure + Jenkins）`
   - 勾选 **Public**（开源做作品集）
   - ⚠️ **不要勾任何初始化选项**（README、.gitignore、license 全都不勾）
4. 点 **Create repository**

> **为什么不勾初始化选项**：勾了之后远程仓库会有一个初始 commit，本地首次 push 会因为"分支历史不一致"被拒绝。保持空仓库最干净。

### 2.1.2 本地建项目目录

```powershell
cd D:\learning\ruoyi-ui-autotest
mkdir ruoyi-api-autotest
cd ruoyi-api-autotest
```

> **目录命名规则**：和 GitHub 仓库名一致，方便 clone 后路径统一。

### 2.1.3 创建 venv

```powershell
python -m venv .venv
```

**原理**：

`python -m venv .venv` 在当前目录建一个名为 `.venv` 的虚拟环境。

venv 不是完全独立的 Python，它**共享系统 Python 的核心**（解释器二进制），但有**独立的包目录**（`Lib/site-packages`）。这样省空间又有隔离。

`.venv` 目录结构：

```
.venv/
├── Scripts/                  # Windows 可执行文件（Linux 是 bin/）
│   ├── python.exe            # venv 专属 Python（实际是系统 Python 的快捷方式）
│   ├── pip.exe               # venv 专属 pip
│   ├── Activate.ps1          # PowerShell 激活脚本
│   └── deactivate.bat        # 退出激活
├── Lib/site-packages/        # 包安装目录
└── pyvenv.cfg                # 配置（指向系统 Python 路径）
```

### 2.1.4 激活 venv

```powershell
.\.venv\Scripts\Activate.ps1
```

**激活成功标志**：命令行前面出现 `(.venv)` 前缀。

#### 可能遇到的问题：禁止运行脚本

报错：

```
.\.venv\Scripts\Activate.ps1 : 无法加载文件 ... 因为在此系统上禁止运行脚本
```

**原因**：Windows PowerShell 默认禁止执行 `.ps1` 脚本（安全策略）。

**解决**（管理员 PowerShell 跑一次）：

```powershell
Set-ExecutionPolicy RemeoteSigned -Scope CurrentUser
```

参数说明：
- `RemoteSigned` —— 本地脚本可执行，从网络下载的脚本必须签名
- `-Scope CurrentUser` —— 只对当前用户生效，不影响系统其他用户

执行后回到普通 PowerShell 重新激活，永久生效。

### 2.1.5 验证 venv 激活了"对的"那个

**关键步骤，必做**：

```powershell
python -c "import sys; print(sys.executable)"
```

**预期输出**：

```
D:\learning\ruoyi-ui-autotest\ruoyi-api-autotest\.venv\Scripts\python.exe
```

#### 可能遇到的问题：激活了别的 venv

如果输出是别的路径（比如父目录的 venv 或系统 Python），说明 PATH 被污染。

**常见原因**：
1. VS Code 自动在父目录建过一个 `.venv`，扫描时优先找到了它
2. 之前的会话 cd 出去后没 deactivate，新会话继承了状态

**排查步骤**：

```powershell
# 1. 查父目录是否有多余 venv
ls D:\learning\ruoyi-ui-autotest\.venv -ErrorAction SilentlyContinue

# 2. 如果有，删掉
deactivate
Remove-Item D:\learning\ruoyi-ui-autotest\.venv -Recurse -Force

# 3. cd 回项目目录重新激活
cd D:\learning\ruoyi-ui-autotest\ruoyi-api-autotest
.\.venv\Scripts\Activate.ps1

# 4. 再次验证
python -c "import sys; print(sys.executable)"
```

### 2.1.6 建目录骨架

```powershell
mkdir api_tests, api_tests\cases, api_tests\data, common, config, reports, logs, scripts, docs, docs\setup

New-Item -ItemType File -Path api_tests\__init__.py
New-Item -ItemType File -Path api_tests\cases\__init__.py
New-Item -ItemType File -Path common\__init__.py
New-Item -ItemType File -Path reports\.gitkeep
New-Item -ItemType File -Path logs\.gitkeep

tree /F
```

**最终结构**：

```
ruoyi-api-autotest/
├── .venv/                  # 虚拟环境（不进 git）
├── api_tests/              # 接口测试主目录
│   ├── __init__.py
│   ├── cases/              # 测试用例
│   │   └── __init__.py
│   └── data/               # YAML 测试数据
├── common/                 # 框架基础组件
│   └── __init__.py
├── config/                 # 多环境配置
├── docs/                   # 文档
│   └── setup/
├── logs/                   # 运行日志（不进 git）
│   └── .gitkeep
├── reports/                # Allure 报告（不进 git）
│   └── .gitkeep
└── scripts/                # 工具脚本
```

#### 设计原理

| 文件/目录 | 作用 |
|---|---|
| `__init__.py` | 让 Python 把目录识别为"包"，可以用 `from common.config import xxx` 导入 |
| `.gitkeep` | Git 不追踪空目录，放空文件让目录被纳入版本控制 |
| `api_tests/cases/` | 用例和框架代码分离 |
| `api_tests/data/` | 测试数据外置（YAML），方便修改不改代码 |
| `common/` | 通用工具：HTTP 客户端、配置、日志、断言 |
| `config/` | 环境配置外置，一份代码跑多环境 |
| `reports/` `logs/` | 输出目录独立，方便挂载到 CI、归档清理 |

---

## 3. Task 2.2：装依赖 + pytest 配置 + 第一个测试

### 3.1 创建 requirements.txt

VS Code 项目根目录新建文件 **`requirements.txt`**，内容：

```
# ===== 测试核心 =====
pytest==8.3.4
pytest-html==4.1.1
pytest-xdist==3.6.1

# ===== HTTP =====
requests==2.32.3

# ===== 数据驱动 =====
PyYAML==6.0.2
jsonpath-ng==1.7.0

# ===== 日志 =====
loguru==0.7.3

# ===== 数据生成 =====
Faker==33.3.1

# ===== 数据库验证 =====
PyMySQL==1.1.1

# ===== 报告 =====
allure-pytest==2.13.5

# ===== 代码质量 =====
ruff==0.9.2
```

`Ctrl+S` 保存。

#### 原理：为什么必须锁定版本（==）

| 写法 | 含义 | 风险 |
|---|---|---|
| `pytest` | 任意版本 | 今天装 8.3，明天可能装到 9.0，行为变了 |
| `pytest>=8.0` | 8.0 及以上 | 可能装到不兼容的新版本 |
| `pytest==8.3.4` | **精确 8.3.4** | 所有人、所有环境一致 ✅ |

**企业必做**：每个直接依赖都用 `==` 锁定。这是测试代码"可复现"的基础。

#### 可能遇到的问题：用 PowerShell here-string 写文件失败

如果你尝试用 here-string 写：

```powershell
@"...内容..."@ | Out-File requirements.txt
```

**容易踩的坑**：
- `@"` 必须**单独占一行**，后面不能有空格
- `"@` 必须**顶格在新行第一个字符**

**最稳的做法**：直接用 VS Code 编辑器新建文件粘贴内容 + `Ctrl+S`。复杂文本生成不要靠 PowerShell 拼字符串。

### 3.2 安装依赖

```powershell
pip install -r requirements.txt
```

**预期过程**：下载安装 30 个包（直接 11 个 + 间接 19 个），2-5 分钟。

#### 可能遇到的问题 1：下载超时/慢

**解决**：临时用阿里云镜像：

```powershell
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

**永久配置**（推荐）：

```powershell
mkdir $env:APPDATA\pip -ErrorAction SilentlyContinue
@"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
"@ | Out-File -FilePath "$env:APPDATA\pip\pip.ini" -Encoding ASCII
```

执行后所有 `pip install` 自动走阿里云。

#### 可能遇到的问题 2：VS Code 弹"创建虚拟环境"提示

VS Code 检测到你装测试包时，会弹窗问"是否创建虚拟环境隔离依赖"。

**正确处理**：**点"否"或"取消"**。

**原因**：你已经在 venv 里了（命令行有 `(.venv)` 前缀）。点"是"会让 VS Code 再建一个 venv，导致两个虚拟环境冲突。

#### 可能遇到的问题 3：装到了系统 Python

如果你激活的是错的 venv 或没激活，依赖会装到系统 Python，污染全局环境。

**预防**：每次 `pip install` 前验证：

```powershell
python -c "import sys; print(sys.executable)"
```

确认输出是项目 venv 的 python.exe。

### 3.3 验证依赖装好

```powershell
pip list | Select-String "pytest|requests|allure|loguru|PyYAML"
```

应该看到这几个包都在。

### 3.4 创建 pytest.ini

VS Code 项目根目录新建 **`pytest.ini`**：

```ini
# ===============================================================
# pytest 配置文件
# ===============================================================

[pytest]

# ---------------------------------------------------------------
# 一、测试文件搜索路径
# ---------------------------------------------------------------
testpaths = api_tests/cases


# ---------------------------------------------------------------
# 二、测试用例命名规则
# ---------------------------------------------------------------
python_files = test_*.py
python_classes = Test*
python_functions = test_*


# ---------------------------------------------------------------
# 三、默认命令行参数
# ---------------------------------------------------------------
addopts = 
    -v
    --tb=short
    --strict-markers
    --color=yes


# ---------------------------------------------------------------
# 四、自定义 marker
# ---------------------------------------------------------------
markers =
    smoke: 冒烟测试 - 最核心的功能验证
    regression: 回归测试 - 全量
    login: 登录模块
    user: 用户模块
    role: 角色模块
```

#### 配置项原理（重要，面试常问）

| 配置 | 作用 |
|---|---|
| `testpaths` | pytest 只在这里搜索用例（不写会全项目扫，慢且容易扫到不该跑的） |
| `python_files` | 文件名模式（`test_*.py`） |
| `python_classes` | 类名模式（`Test*`） |
| `python_functions` | 函数名模式（`test_*`） |
| `-v` | verbose 模式，显示每个用例结果 |
| `--tb=short` | 失败时显示简短堆栈 |
| `--strict-markers` | 用了未声明的 marker 直接报错（防止打错字还跑过去） |
| `--color=yes` | 彩色输出 |
| `markers` | 自定义标签，用 `pytest -m smoke` 筛选执行 |

#### marker 的实战用法（CI 流水线常用）

```powershell
pytest -m smoke              # 只跑冒烟（CI 提交触发）
pytest -m regression         # 跑全量回归（每晚定时）
pytest -m "smoke or login"   # 跑冒烟或登录
pytest -m "not slow"         # 排除慢用例
```

### 3.5 写第一个测试

VS Code 在 `api_tests/cases/` 下新建 **`test_smoke.py`**：

```python
"""冒烟测试 - 验证 pytest 框架本身能跑"""


def test_hello():
    """1+1 是否还等于 2"""
    assert 1 + 1 == 2


def test_string_contains():
    """字符串断言示例"""
    name = "RuoYi"
    assert "Yi" in name


def test_dict_assertion():
    """字典断言示例 - 接口测试中最常用"""
    response = {"code": 200, "msg": "操作成功", "data": {"id": 1}}
    assert response["code"] == 200
    assert response["msg"] == "操作成功"
    assert response["data"]["id"] == 1
```

`Ctrl+S` 保存。

#### 可能遇到的问题：文件创建了但内容为 0

**现象**：

```powershell
ls api_tests\cases\
# Length 列显示 0
```

**原因**：VS Code 里建了文件但没保存内容（标签页文件名末尾有 `●` 表示未保存）。

**解决**：双击文件确认有内容，`Ctrl+S` 保存。

**判断技巧**：VS Code 标签页：
- `test_smoke.py ●` ← 未保存
- `test_smoke.py ×` ← 已保存

### 3.6 跑测试

```powershell
pytest
```

**预期输出**：

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.6.0 -- D:\...\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\learning\ruoyi-ui-autotest\ruoyi-api-autotest
configfile: pytest.ini
testpaths: api_tests/cases
plugins: allure-pytest-2.13.5, Faker-33.3.1, html-4.1.1, metadata-3.1.1, xdist-3.6.1
collected 3 items

api_tests/cases/test_smoke.py::test_hello PASSED                         [ 33%]
api_tests/cases/test_smoke.py::test_string_contains PASSED               [ 67%]
api_tests/cases/test_smoke.py::test_dict_assertion PASSED                [100%]

============================== 3 passed in 0.05s ==============================
```

### 3.7 看懂 pytest 输出（必备技能）

每次跑 pytest，**先扫这 4 个关键点**：

| 看什么 | 确认什么 | 异常信号 |
|---|---|---|
| `python.exe` 路径 | venv 是否激活 | 路径不在 `.venv` 里 |
| `configfile` | 配置是否生效 | 显示了别的配置文件 |
| `testpaths` | 用例搜索路径 | 没显示 = 没配 testpaths |
| `collected N items` | 收集到几个用例 | 0 = 用例没写或没识别到 |

#### `collected 0 items` 的常见原因

1. 文件名不对（不是 `test_*.py` 或 `*_test.py`）
2. 函数名不对（不是 `def test_*`）
3. **文件是空的**（VS Code 没保存）
4. 类有 `__init__` 方法（pytest 会跳过）
5. 不在 `testpaths` 配置的目录里

---

## 4. Task 2.3：多环境配置加载

### 4.1 设计目标

让框架根据环境变量 `ENV` 自动加载对应的 YAML 配置：

```
$env:ENV = "dev"   →  加载 config/dev.yaml
$env:ENV = "test"  →  加载 config/test.yaml
$env:ENV = "prod"  →  加载 config/prod.yaml
```

**一份代码跑多环境**——这是企业测试框架的标配。

### 4.2 PowerShell 环境变量原理

`$env:ENV = "dev"` 拆解：

```
$env:ENV = "dev"
│  │  │   │
│  │  │   └── 值
│  │  └────── 变量名
│  └───────── 冒号（PowerShell 驱动器语法）
└──────────── $env: 是"环境变量驱动器"
```

PowerShell 把环境变量当虚拟盘符访问。类比：

| 操作 | 文件系统 | 环境变量 |
|---|---|---|
| 读 | `Get-Content C:\file.txt` | `$env:ENV` |
| 写 | `Set-Content C:\file.txt "data"` | `$env:ENV = "dev"` |
| 删 | `Remove-Item C:\file.txt` | `Remove-Item Env:\ENV` |
| 列出 | `dir C:\` | `dir Env:\` |

#### 三种作用域

| 作用域 | 命令 | 持久度 |
|---|---|---|
| 进程级 | `$env:ENV = "dev"` | 当前 PowerShell 窗口，关掉就没 |
| 用户级 | `[Environment]::SetEnvironmentVariable("ENV", "dev", "User")` | 当前用户永久 |
| 系统级 | `[Environment]::SetEnvironmentVariable("ENV", "dev", "Machine")` | 全系统永久（需管理员） |

测试中**用进程级最合适**——临时切环境，不污染系统。

#### Linux 对比

| 操作 | Windows PowerShell | Linux Bash |
|---|---|---|
| 设置 | `$env:ENV = "dev"` | `export ENV=dev` |
| 读取 | `$env:ENV` | `$ENV` |
| 一次性运行 | 不直接支持 | `ENV=dev pytest` |

### 4.3 创建 dev.yaml

VS Code 在 `config/` 下新建 **`dev.yaml`**：

```yaml
# 开发环境配置（本地 RuoYi）
env: dev

base_url: http://localhost:8080
timeout: 10

admin:
  username: admin
  password: admin123

ry_user:
  username: ry
  password: admin123

database:
  host: localhost
  port: 3306
  user: root
  password: "你的MySQL密码"   # 改成你真实密码
  database: ry-vue
  charset: utf8mb4

redis:
  host: localhost
  port: 6379
  password: ""
  db: 0
```

⚠️ 把 `database.password` 改成你 Part 1 里设置的 MySQL root 密码。

### 4.4 创建 test.yaml（占位）

`config/test.yaml`：

```yaml
# 测试环境配置（公司测试服务器，目前占位）
env: test

base_url: http://test-server.example.com:8080
timeout: 15

admin:
  username: admin
  password: admin123

ry_user:
  username: ry
  password: admin123

database:
  host: test-db.example.com
  port: 3306
  user: ruoyi_test
  password: "test_password"
  database: ry-vue
  charset: utf8mb4

redis:
  host: test-redis.example.com
  port: 6379
  password: "test_redis_pwd"
  db: 0
```

### 4.5 创建配置加载器

`common/config.py`：

```python
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
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


# ===================================================================
# 让字典支持点号访问的辅助类
# ===================================================================
class DotDict(dict):
    """支持点号访问的 dict"""

    def __init__(self, data: dict):
        super().__init__()
        for key, value in data.items():
            if isinstance(value, dict):
                value = DotDict(value)
            self[key] = value

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"配置中不存在 '{key}'，请检查 YAML 文件")

    def __setattr__(self, key, value):
        self[key] = value


# ===================================================================
# 加载配置
# ===================================================================
def load_config() -> DotDict:
    """根据环境变量 ENV 加载对应配置文件"""

    env = os.getenv("ENV", "dev").lower()
    config_file = CONFIG_DIR / f"{env}.yaml"

    if not config_file.exists():
        raise FileNotFoundError(
            f"配置文件不存在：{config_file}\n"
            f"请确认 config/ 目录下有 {env}.yaml"
        )

    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    logger.info(f"加载配置：{config_file.name} | 环境: {env} | URL: {data.get('base_url')}")

    return DotDict(data)


# ===================================================================
# 全局唯一配置实例（单例模式）
# ===================================================================
config = load_config()
```

#### 关键设计原理

**1. 单例模式**

```python
config = load_config()
```

模块第一次被 import 时执行 `load_config()`，所有地方 `import config` 都拿到同一个实例。Python 模块本身就是单例的（缓存在 `sys.modules`），不需要额外写单例类。

**2. DotDict 点号访问**

普通 dict：`data["admin"]["username"]`（嵌套层级深时丑）
DotDict：`data.admin.username`（清晰）

通过重写 `__getattr__` 实现：当通过 `obj.key` 访问时被触发，转去 dict 里找 key。

**3. PROJECT_ROOT 的算法**

```python
PROJECT_ROOT = Path(__file__).parent.parent
```

- `__file__` = 当前文件路径（`common/config.py`）
- `.parent` = 上一级（`common/`）
- `.parent.parent` = 项目根目录

这种写法**和当前工作目录无关**——不管在哪个目录跑 pytest，都能找到正确的 config 路径。

### 4.6 创建 conftest.py

`api_tests/conftest.py`：

```python
"""
pytest 全局 fixture 文件
=======================

conftest.py 是 pytest 的"魔法文件"：
- 文件名必须叫 conftest.py
- 不需要 import，pytest 自动发现
- 这里定义的 fixture 在同目录及子目录的所有用例里都能直接用

放在 api_tests/conftest.py 表示对 api_tests 下所有测试生效
"""

import pytest

from common.config import config


@pytest.fixture(scope="session")
def env_config():
    """返回当前环境的配置对象（整个会话只加载一次）"""
    return config
```

#### conftest.py 的魔力

1. **自动发现**：pytest 启动时扫描所有目录的 `conftest.py`，无需 import
2. **作用域继承**：放在哪个目录，就对哪个目录及其子目录生效
3. **多层 conftest**：`api_tests/conftest.py` 全局、`api_tests/cases/login/conftest.py` 只对 login 模块生效

#### fixture scope 等级

| scope | 创建/销毁时机 | 用途 |
|---|---|---|
| `function`（默认） | 每个用例前后 | 独立测试数据 |
| `class` | 每个测试类前后 | 类内共享 |
| `module` | 每个模块前后 | 模块共享 |
| `session` | 整个测试会话开始/结束 | **全局共享，如配置、token** |

`env_config` 用 `session` 表示整个测试期间只加载一次配置文件。

### 4.7 写验证用例

替换 `api_tests/cases/test_smoke.py` 的内容：

```python
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


@pytest.mark.smoke
def test_config_loaded(env_config):
    """配置文件能被正确加载"""
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
```

### 4.8 跑测试

```powershell
pytest
```

预期：5 passed，并看到 loguru 日志：

```
2026-05-01 23:xx:xx | INFO | common.config:load_config:62 - 加载配置：dev.yaml | 环境: dev | URL: http://localhost:8080
```

### 4.9 验证多环境切换

```powershell
$env:ENV = "test"
pytest
```

预期：

- 加载日志变成 `加载配置：test.yaml | 环境: test`
- `test_config_loaded` FAILED（因为断言 `env == "dev"`）
- `test_database_config` FAILED（因为断言 `host == "localhost"`）

**这两个 FAILED 正是想要的结果**——证明环境切换真的生效了。

#### pytest 失败信息阅读

```
api_tests\cases\test_smoke.py:25: in test_config_loaded     ← 文件:行号:函数名
    assert env_config.env == "dev"                          ← 失败的断言代码
E   AssertionError: assert 'test' == 'dev'                  ← 错误类型 + 消息
E     - dev                                                 ← 期望值
E     + test                                                ← 实际值
```

**3 个关键信息**：
1. **位置**：`test_smoke.py:25` — Ctrl+点击直接跳转
2. **断言代码**：哪个表达式失败
3. **diff 对比**：`-` 期望、`+` 实际

#### 切回 dev

```powershell
Remove-Item Env:\ENV    # 推荐：清除环境变量
# 或
$env:ENV = "dev"        # 显式设回
```

---

## 5. Task 2.4：Git 初始化与首次推送

### 5.1 创建 .gitignore

VS Code 项目根目录新建 **`.gitignore`**：

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/

# 虚拟环境
.venv/
venv/

# pytest
.pytest_cache/

# 测试输出
reports/*
!reports/.gitkeep
logs/*
!logs/.gitkeep
allure-results/
allure-report/

# IDE
.idea/
*.iml

# 系统
.DS_Store
Thumbs.db
```

#### .gitignore 语法说明

| 语法 | 含义 |
|---|---|
| `__pycache__/` | 忽略所有名为 __pycache__ 的目录 |
| `*.py[cod]` | 通配 .pyc / .pyo / .pyd |
| `.venv/` | 忽略 .venv 目录 |
| `reports/*` | 忽略 reports 下所有文件 |
| `!reports/.gitkeep` | 但保留 .gitkeep（`!` 是反向规则） |

**关键**：venv 必须忽略——里面的包是机器相关的二进制，进 git 既无意义又巨大。

### 5.2 创建 README.md

项目根目录新建 **`README.md`**：

````markdown
# RuoYi-Vue 接口自动化测试框架

> 基于 pytest + Allure + Jenkins 的企业级 API 自动化测试方案，被测系统为 [RuoYi-Vue](https://github.com/yangzongzhuan/RuoYi-Vue)。

## 技术栈

| 类别 | 选型 |
|---|---|
| 测试框架 | pytest 8.x |
| HTTP | requests |
| 数据驱动 | PyYAML + jsonpath-ng |
| 日志 | loguru |
| 数据生成 | Faker |
| 数据库验证 | PyMySQL |
| 测试报告 | allure-pytest |
| 代码质量 | ruff |

## 项目结构

```
ruoyi-api-autotest/
├── api_tests/          # 接口测试
│   ├── conftest.py
│   ├── cases/
│   └── data/
├── common/             # 框架基础组件
├── config/             # 多环境配置
├── reports/            # Allure 报告
├── logs/               # 运行日志
├── pytest.ini
├── requirements.txt
└── README.md
```

## 快速开始

```powershell
git clone https://github.com/<你的用户名>/ruoyi-api-autotest.git
cd ruoyi-api-autotest

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pytest
```

## 多环境运行

```powershell
$env:ENV = "test"
pytest
```

## 进度

- [x] 框架初始化
- [x] 多环境配置加载
- [ ] HTTP 客户端封装
- [ ] Token 认证 fixture
- [ ] 业务模块用例
- [ ] Allure 报告
- [ ] Jenkins 流水线
- [ ] Docker 化测试环境

## License

MIT
````

> ⚠️ 上面 README 内层代码块用三个反引号包裹，复制到 VS Code 时把外层 4 个反引号改成 3 个。

### 5.3 git 初始化

```powershell
# 配置 git 用户信息（首次使用 git 必做）
git config --global user.name "01Ray"
git config --global user.email "你的GitHub邮箱"

# 初始化仓库
git init

# 设置默认分支为 main（GitHub 标准）
git branch -M main

# 添加所有文件（受 .gitignore 控制）
git add .

# 查看状态
git status
```

#### 关键检查 `git status` 输出

应该看到一堆 `new file:`，但**绝对不能出现**：

- ❌ `.venv/` 任何文件
- ❌ `__pycache__/` 任何文件
- ❌ `.pytest_cache/`

预期看到：

```
new file:   .gitignore
new file:   README.md
new file:   api_tests/__init__.py
new file:   api_tests/cases/__init__.py
new file:   api_tests/cases/test_smoke.py
new file:   api_tests/conftest.py
new file:   common/__init__.py
new file:   common/config.py
new file:   config/dev.yaml
new file:   config/test.yaml
new file:   logs/.gitkeep
new file:   pytest.ini
new file:   reports/.gitkeep
new file:   requirements.txt
```

#### 可能遇到的问题：.venv 被加入了

如果 `git status` 看到 `.venv/...`，说明 `.gitignore` 没生效。

**原因**：可能 `.gitignore` 在 `git add` 之后才创建。

**解决**：

```powershell
# 1. 撤销已添加的所有文件
git rm -r --cached .

# 2. 确认 .gitignore 内容正确
Get-Content .gitignore

# 3. 重新 add
git add .
git status
```

`git rm --cached` 只从 git 索引移除，不删本地文件——很安全。

### 5.4 首次 commit

```powershell
git commit -m "feat: 初始化接口自动化测试框架

- pytest 8.x + venv 环境
- 多环境配置加载 (dev/test)
- DotDict 点号访问配置
- 5 个冒烟测试通过"
```

#### Conventional Commits 规范（企业必备）

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | 修 bug |
| `docs:` | 改文档 |
| `refactor:` | 重构（不改功能） |
| `test:` | 改测试代码 |
| `chore:` | 杂项（依赖升级、配置） |
| `perf:` | 性能优化 |
| `style:` | 代码格式（不影响逻辑） |
| `ci:` | CI 配置改动 |

**格式**：
```
<type>: <短描述>（50 字符内）
<空行>
<详细变更点>
```

**好处**：commit 历史清晰，能用工具自动生成 CHANGELOG。

### 5.5 关联远程仓库

```powershell
git remote add origin https://github.com/01Ray/ruoyi-api-autotest.git
git remote -v
```

预期看到 4 行（fetch + push）。

### 5.6 推送到 GitHub

```powershell
git push -u origin main
```

`-u` (`--set-upstream`) 设置上游分支——以后只需 `git push` 不用每次写 `origin main`。

#### 可能遇到的情况

**情况 A：直接成功**

```
* [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

**情况 B：弹出浏览器要求 GitHub 授权**

按提示点击"Authorize"或"Continue"，授权完自动回 PowerShell。

**情况 C：要求输入用户名密码**

```
Username for 'https://github.com':
```

⚠️ **GitHub 2021 年起不接受账号密码**，需要 Personal Access Token。

**生成 Token**：
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → 勾选 `repo` 权限 → 生成
3. **复制保存**（只显示一次）
4. 在 PowerShell 提示密码处粘贴 Token

**情况 D：报错 `Updates were rejected`**

说明远程仓库不是空的（创建时勾了 README 或 .gitignore）。

**解决**：

```powershell
git pull origin main --rebase --allow-unrelated-histories
git push -u origin main
```

#### 可能遇到的 Warning

**Warning 1：TLS certificate verification has been disabled**

之前手动关过 SSL 校验，安全隐患。修复：

```powershell
git config --global http.sslVerify true
```

修完再次 push。如果出错（"unable to get local issuer certificate"），需要更新证书或安装 Git Credential Manager 新版。

**Warning 2：'credential-manager' is not a git command**

凭据管理器配置过时。修复：

```powershell
git config --global credential.helper manager
```

如果还报错，试 `manager-core`。

### 5.7 验证推送成功

浏览器打开：

```
https://github.com/01Ray/ruoyi-api-autotest
```

应该看到：

- ✅ 14 个文件
- ✅ README.md 自动渲染
- ✅ "1 commit" 标签
- ✅ 完整目录结构
- ❌ **没有 .venv 目录**（关键，证明 .gitignore 生效）

---

## 6. VS Code 配置（可选但强烈推荐）

让 VS Code 正确识别 venv，启用测试面板和自动格式化。

### 6.1 装 4 个扩展

VS Code 左侧 Extensions（`Ctrl+Shift+X`）：

| 扩展 | 作者 | 作用 |
|---|---|---|
| **Python** | Microsoft | Python 基础支持 |
| **Pylance** | Microsoft | 智能补全（装 Python 时自动装上） |
| **Ruff** | Astral Software | 代码检查 + 格式化 |
| **YAML** | Red Hat | YAML 语法高亮 |

⚠️ Python 扩展必须**认准 Microsoft 官方**那个，下载量上亿的。

### 6.2 选择 Python 解释器

1. `Ctrl+Shift+P` → `Python: Select Interpreter`
2. 找带 `('.venv': venv)` 标记的项

如果列表里没有：

1. 点 `+ Enter interpreter path...`
2. 浏览到 `D:\learning\ruoyi-ui-autotest\ruoyi-api-autotest\.venv\Scripts\python.exe`
3. 选中确定

成功后右下角状态栏显示 `Python 3.12.x ('.venv': venv)`。

### 6.3 项目级 VS Code 配置

新建 `.vscode/settings.json`：

```json
{
  "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["api_tests/cases"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "files.encoding": "utf8",
  "files.eol": "\n",
  "python.createEnvironment.contentButton": "hide"
}
```

效果：
1. 自动识别 venv，新开终端自动激活
2. 启用 pytest 测试面板（侧边栏烧瓶图标）
3. 保存时自动格式化 + 整理 import
4. 强制 UTF-8 + LF 行尾符（CI 不出乱码）

---

## 7. 关键经验总结

### 必记的 venv 规则

1. **每个项目一个 venv**，永不复用
2. **venv 不进 git**，靠 `requirements.txt` 重建
3. **每次开终端都要激活**（看到 `(.venv)` 才安全）
4. **每次 pip install 前验证**：`python -c "import sys; print(sys.executable)"`
5. **出问题直接删了重建**：venv 是一次性工件

### 常用命令速查

```powershell
# venv 操作
python -m venv .venv                          # 建
.\.venv\Scripts\Activate.ps1                  # 激活
deactivate                                    # 退出激活
Remove-Item .venv -Recurse -Force             # 删除（出问题就重建）

# 依赖管理
pip install -r requirements.txt               # 装依赖
pip freeze > requirements.txt                 # 导出当前依赖
pip list                                      # 列出所有包
pip show <pkg>                                # 看某个包详情

# pytest 运行
pytest                                        # 跑全部
pytest -v                                     # 详细输出
pytest -m smoke                               # 按 marker 跑
pytest -k "login"                             # 按名字跑
pytest api_tests/cases/test_login.py          # 跑指定文件
pytest --lf                                   # 跑上次失败的（last failed）
pytest -n 4                                   # 4 进程并行（需要 pytest-xdist）

# 多环境
$env:ENV = "test"                             # 切到 test
$env:ENV                                      # 看当前
Remove-Item Env:\ENV                          # 清除

# git 常用
git status                                    # 看状态
git add .                                     # 加全部
git commit -m "..."                           # 提交
git push                                      # 推送
git log --oneline -10                         # 看最近 10 个 commit
git diff                                      # 看未暂存改动
git diff --cached                             # 看已暂存改动
```

### Windows 特有踩坑速查

| 问题 | 解决 |
|---|---|
| PowerShell 禁止运行脚本 | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| here-string 写文件失败 | 用 VS Code 编辑器代替 |
| PowerShell 不支持 `<` 重定向 | 用 mysql `SOURCE` 命令或 cmd |
| PowerShell 反引号是转义 | SQL 反引号要双写或避开 |
| Get-Content 默认 GBK | 加 `-Encoding UTF8` |
| Notepad 加 BOM 头 | 用 VS Code / Notepad++ |

### 排查清单（出问题先过一遍）

```powershell
# 1. venv 激活了吗？
python -c "import sys; print(sys.executable)"

# 2. 装的包对吗？
pip list | Select-String "pytest"

# 3. pytest 配置生效了吗？
pytest --collect-only

# 4. 当前环境是什么？
$env:ENV

# 5. git 状态？
git status

# 6. 远程仓库关联了吗？
git remote -v
```

---

## 8. 当前进度

- [x] **Task 2.1** 独立测试仓库 + venv + 目录骨架
- [x] **Task 2.2** 11 个核心依赖 + pytest.ini + 第一个测试
- [x] **Task 2.3** 多环境配置加载 + DotDict + conftest.py
- [x] **Task 2.4** Git 初始化 + 首次推送 GitHub
- [ ] **Task 2.5** HTTP 客户端封装（下一步）
- [ ] **Task 2.6** Token fixture + 登录 fixture
- [ ] **Task 2.7** 第一个真实业务用例（登录正向 + 反向）
- [ ] **Task 2.8** Allure 报告

---

## 9. 下一步预告

**Task 2.5：HTTP 客户端封装**

将完成：

1. 启动 RuoYi 后端
2. 用 requests 直接发一次登录请求，看响应结构
3. 封装 `HttpClient` 类（自动加 token、统一日志、统一错误处理）
4. 写第一个真实接口用例：`/captchaImage` 验证码接口

**期望产出**：测试框架真的连上 RuoYi 后端发请求，看到第一个真实响应。

---

**文档版本**：v1.0  
**对应仓库**：ruoyi-api-autotest  
**整理日期**：2026-05-01
