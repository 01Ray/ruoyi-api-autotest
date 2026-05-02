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

## 测试报告

本框架使用 Allure 生成可视化测试报告，包含：

- Epic / Feature / Story 三层业务分组
- 每个用例步骤精确标注（@allure.step）
- 请求体 / 响应体自动附加
- 失败时自动归类（Categories）
- 历史趋势分析（连续运行后可见）

### 生成报告

\`\`\`powershell
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
\`\`\`