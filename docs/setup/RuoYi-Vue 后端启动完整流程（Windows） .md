# RuoYi-Vue 后端启动完整流程（Windows）

> 本文档基于 RuoYi-Vue v3.9.2 + Windows 11 + JDK 17 + MySQL 8.4 + Redis 实际操作整理。
> 涵盖：完整步骤、实际遇到的问题、可能遇到的问题及处理方式。

---

## 0. 环境前置要求

| 组件 | 版本要求 | 备注 |
|---|---|---|
| JDK | 17+ | RuoYi-Vue 3.9.x 基于 SpringBoot 3.x，必须 JDK 17 及以上 |
| Maven | 3.6+ | 推荐 3.8 / 3.9 |
| MySQL | 5.7 / 8.x | 本文档使用 8.4 |
| Redis | 5.x+ | Windows 上推荐用服务化版本 |
| Git | 任意近期版本 | 用于 clone 和后续协作 |
| Node.js | 16 / 18 | 启动前端时需要（本文档不涵盖） |

验证命令：

```powershell
java -version
mvn -v
mysql --version    # 如未识别，参考第 2 节
redis-cli ping     # 应返回 PONG
git --version
```

---

## 1. 拉取代码（Fork → Clone → 设置 upstream）

### 1.1 Fork 官方仓库

浏览器打开 <https://github.com/yangzongzhuan/RuoYi-Vue>，点右上角 **Fork** 到自己账号下。

> **为什么要 fork**：模拟企业协作流程。公司里你不会有权限直接改主仓库，标准流程是 fork → 改 → PR。

### 1.2 Clone 到本地

```powershell
cd D:\learning\ruoyi-ui-autotest
git clone https://github.com/<你的用户名>/RuoYi-Vue.git
cd RuoYi-Vue
```

### 1.3 设置 upstream（指向官方仓库）

```powershell
git remote add upstream https://github.com/yangzongzhuan/RuoYi-Vue.git
git remote -v
```

验证输出应有 4 行：

```
origin    https://github.com/<你的用户名>/RuoYi-Vue.git (fetch)
origin    https://github.com/<你的用户名>/RuoYi-Vue.git (push)
upstream  https://github.com/yangzongzhuan/RuoYi-Vue.git (fetch)
upstream  https://github.com/yangzongzhuan/RuoYi-Vue.git (push)
```

> **概念辨析**：`origin` 和 `upstream` 是 Git 约定俗成的命名。
> - `origin` = 你的 fork（可读可写）
> - `upstream` = 官方仓库（只能拉，push 会被 GitHub 服务器拒绝）
>
> `git remote -v` 显示的 push URL 不代表你有权限 push，权限由服务器判断。

### 1.4（可选）禁用 upstream 的 push URL，避免误操作

```powershell
git remote set-url --push upstream no-push
```

---

## 2. MySQL 安装与服务重建

### 2.1 检查是否已安装

```powershell
Get-Service | Where-Object {$_.Name -like "*mysql*"}
Get-ChildItem "C:\Program Files\" -Filter "*MySQL*" -ErrorAction SilentlyContinue
Get-ChildItem "C:\ProgramData\MySQL\" -ErrorAction SilentlyContinue
```

四种可能：

| 情况 | 处理 |
|---|---|
| 服务在跑 + 程序目录在 + 数据目录在 | 跳到第 3 节 |
| 程序目录在 + 数据目录在 + 服务没了 | **本文档场景**，走 2.2 |
| 只装了 Workbench，没服务端 | 用官方 Installer 重装 MySQL Server |
| 完全没装 | 用官方 Installer 全新安装 |

### 2.2 重建 MySQL 服务（程序和数据都还在）

**前提**：以**管理员权限**打开 PowerShell。

#### Step 1：检查 my.ini 配置文件

```powershell
Get-Content "C:\ProgramData\MySQL\MySQL Server 8.4\my.ini"
```

最小可用配置示例：

```ini
[mysqld]
port=3306
basedir=C:/Program Files/MySQL/MySQL Server 8.4/
datadir=C:/ProgramData/MySQL/MySQL Server 8.4/Data/
character-set-server=utf8mb4
default-time-zone='+08:00'

[client]
port=3306
default-character-set=utf8mb4
```

#### Step 2：注册服务

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" --install MySQL84 --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.4\my.ini"
```

预期输出：`Service successfully installed.`

#### Step 3：启动服务

```powershell
Start-Service MySQL84
Get-Service MySQL84
```

应看到 `Status: Running`。

#### Step 4：设置开机自启

```powershell
Set-Service -Name MySQL84 -StartupType Automatic
```

#### Step 5：永久加 PATH（管理员 PowerShell 执行）

```powershell
[System.Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\MySQL\MySQL Server 8.4\bin", [System.EnvironmentVariableTarget]::Machine)
```

执行后**关闭当前 PowerShell，重开一个**让环境变量生效。

#### Step 6：验证登录

```powershell
mysql -u root -p
```

进入 `mysql>` 提示符即成功。

---

## 3. 创建数据库 + 导入 SQL

### 3.1 创建数据库

进入 mysql 提示符：

```powershell
mysql -u root -p
```

执行：

```sql
CREATE DATABASE IF NOT EXISTS `ry-vue` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
SHOW DATABASES;
```

> ⚠️ **PowerShell 反引号坑**：库名 `ry-vue` 含横杠，必须用反引号包裹。但 PowerShell 里反引号 `` ` `` 是转义字符，会和 SQL 反引号冲突。
>
> 推荐做法：**直接进 mysql 提示符执行 SQL**，避开 PowerShell 转义。
>
> 如果非要在 PowerShell 命令行用 `-e` 执行：用双反引号 `` `` `` 转义。

### 3.2 导入 SQL 文件（关键：字符集！）

#### ❌ 失败方式（会出乱码）

```powershell
mysql -u root -p ry-vue < ry_20260417.sql      # PowerShell 不支持 < 重定向
```

直接进 mysql 后 source（会乱码）：

```sql
source D:/.../ry_20260417.sql;     # 客户端字符集协商错误，中文写入失败
```

报错示例：
```
ERROR 1366 (HY000): Incorrect string value: '\xAE\xE9\x80\x9A...' for column 'dept_name' at row 1
ERROR 1406 (22001): Data too long for column 'role_name' at row 1
```

#### ✅ 正确方式

**方案 A：mysql 客户端显式指定字符集（推荐）**

```powershell
mysql -u root -p --default-character-set=utf8mb4 ry-vue
```

进入后**第一件事**：

```sql
SET NAMES utf8mb4;
SOURCE D:/learning/ruoyi-ui-autotest/RuoYi-Vue/sql/ry_20260417.sql;
SOURCE D:/learning/ruoyi-ui-autotest/RuoYi-Vue/sql/quartz.sql;
```

> **路径写法**：用 `/` 不要用 `\`（`\` 在 SQL 里是转义字符）；路径不加引号。

**方案 B：CMD + 重定向（备选）**

```cmd
chcp 65001
mysql -u root -p --default-character-set=utf8mb4 ry-vue < ry_20260417.sql
```

### 3.3 验证导入

```sql
USE `ry-vue`;
SHOW TABLES;
SELECT user_id, user_name, nick_name FROM sys_user LIMIT 5;
```

应能看到 30+ 张表，且中文字段（如 `若依`）显示正常。

#### 中文乱码处理

如果 `SELECT` 看到 `??` 或 `?¨a?¨a` 等乱码 → 数据已损坏，**删库重建**：

```sql
DROP DATABASE `ry-vue`;
CREATE DATABASE `ry-vue` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

然后按 3.2 方案 A 重新导入。

---

## 4. 验证 Redis

```powershell
redis-cli ping                                          # 应返回 PONG
Get-Service | Where-Object {$_.Name -like "*redis*"}    # 确认是否服务化
```

如果 `redis-cli` 无响应：
- 服务存在但停了 → `Start-Service Redis`
- 服务不存在 → 安装 Memurai / Redis for Windows，或用 Docker `docker run -d -p 6379:6379 redis`

---

## 5. 修改 RuoYi 配置

### 5.1 查看配置文件

```powershell
cd D:\learning\ruoyi-ui-autotest\RuoYi-Vue
Get-Content .\ruoyi-admin\src\main\resources\application-druid.yml -Encoding UTF8
Get-Content .\ruoyi-admin\src\main\resources\application.yml -Encoding UTF8
```

> ⚠️ **PowerShell 5 默认 GBK 读 UTF-8 文件会乱码**。永远显式 `-Encoding UTF8`。

### 5.2 修改数据库密码（必改）

文件：`ruoyi-admin/src/main/resources/application-druid.yml`

```yaml
spring:
    datasource:
        druid:
            master:
                url: jdbc:mysql://localhost:3306/ry-vue?useUnicode=true&characterEncoding=utf8&zeroDateTimeBehavior=convertToNull&useSSL=true&serverTimezone=GMT%2B8
                username: root
                password: <你 MySQL 的真实 root 密码>
```

> **密码含特殊字符**（`:` `#` `@` `!` 空格等）需用双引号包裹：`password: "MyP@ss:word"`。

### 5.3 修改文件上传路径（可选）

文件：`ruoyi-admin/src/main/resources/application.yml`

```yaml
ruoyi:
  profile: D:/learning/ruoyi-ui-autotest/ruoyi/uploadPath
```

> ⚠️ **YAML 路径分隔符用 `/`，不要用 `\`**。Java 在 Windows 上完全支持正斜杠。
> 如要用反斜杠必须双写：`D:\\learning\\...`。

### 5.4 创建上传目录

```powershell
New-Item -Path "D:\learning\ruoyi-ui-autotest\ruoyi\uploadPath" -ItemType Directory -Force
```

### 5.5（可选）让 Maven 默认用 UTF-8

避免编译时中文 properties 乱码。**管理员 PowerShell**：

```powershell
[System.Environment]::SetEnvironmentVariable("MAVEN_OPTS", "-Dfile.encoding=UTF-8", [System.EnvironmentVariableTarget]::Machine)
```

关闭重开 PowerShell，验证：

```powershell
echo $env:MAVEN_OPTS    # 应输出 -Dfile.encoding=UTF-8
mvn -v                  # platform encoding 应变成 UTF-8
```

### 5.6 编辑器选择

| 编辑器 | 是否可用 |
|---|---|
| VS Code | ✅ 推荐 |
| Notepad++ | ✅ 可用 |
| IntelliJ IDEA | ✅ 推荐 |
| **Windows 自带 Notepad** | ❌ 可能加 BOM 头导致 Java 报错 |

---

## 6. Maven 构建

### 6.1 多模块项目结构认知

```
RuoYi-Vue/
├── ruoyi-admin       ← 启动入口（main 方法在这）
├── ruoyi-framework   ← 框架核心
├── ruoyi-system      ← 业务模块
├── ruoyi-common      ← 通用工具
├── ruoyi-quartz      ← 定时任务
├── ruoyi-generator   ← 代码生成器
├── ruoyi-ui          ← 前端（Vue2）
├── sql               ← 初始化 SQL
└── pom.xml           ← Maven 父项目
```

**关键点**：后端是多模块 Maven 项目，启动入口在 `ruoyi-admin` 模块。

### 6.2 构建命令

```powershell
cd D:\learning\ruoyi-ui-autotest\RuoYi-Vue
mvn clean install -DskipTests
```

参数说明：
- `clean` — 清理之前的构建产物
- `install` — 编译 + 打包 + 安装到本地 Maven 仓库（多模块项目必须 install，否则子模块互相找不到）
- `-DskipTests` — 跳过单元测试，加快构建

**首次构建耗时**：5–15 分钟（取决于网速，会下载几百 MB 依赖）。

### 6.3 成功标志

```
[INFO] Reactor Summary for ruoyi 3.9.2:
[INFO] ruoyi .............................................. SUCCESS
[INFO] ruoyi-common ....................................... SUCCESS
[INFO] ruoyi-system ....................................... SUCCESS
[INFO] ruoyi-framework .................................... SUCCESS
[INFO] ruoyi-quartz ....................................... SUCCESS
[INFO] ruoyi-generator .................................... SUCCESS
[INFO] ruoyi-admin ........................................ SUCCESS
[INFO] BUILD SUCCESS
```

### 6.4 构建失败处理

#### 问题 1：依赖下载慢/超时

配置阿里云 Maven 镜像。编辑 `<Maven 安装目录>\conf\settings.xml`，在 `<mirrors>` 标签下加：

```xml
<mirror>
    <id>aliyunmaven</id>
    <mirrorOf>*</mirrorOf>
    <name>阿里云公共仓库</name>
    <url>https://maven.aliyun.com/repository/public</url>
</mirror>
```

或者放到用户级 `~/.m2/settings.xml`（不影响其他用户）。

#### 问题 2：JDK 版本不匹配

报错示例：`class file has wrong version 61.0, should be 52.0`

→ 你装的 JDK 版本和项目要求不符。RuoYi-Vue 3.9.x 必须 JDK 17+。

#### 问题 3：磁盘空间不足

Maven 本地仓库（`C:\Users\<用户名>\.m2\repository`）首次会占 1–2 GB。

---

## 7. 启动后端

### 7.1 启动命令

```powershell
cd D:\learning\ruoyi-ui-autotest\RuoYi-Vue
mvn spring-boot:run -pl ruoyi-admin
```

参数说明：
- `spring-boot:run` — Spring Boot Maven 插件提供的启动指令
- `-pl ruoyi-admin` — 仅在 `ruoyi-admin` 子模块下执行

### 7.2 成功标志

启动日志末尾会出现 RuoYi 字符画 + 类似日志：

```
Tomcat started on port(s): 8080 (http) with context path ''
Started RuoYiApplication in xx.xxx seconds
(♥◡♥) RuoYi-Vue启动成功
```

### 7.3 浏览器验证

打开 <http://localhost:8080>，应看到：

```
欢迎使用RuoYi后台管理框架，当前版本：v3.9.2，请通过前端地址访问。
```

或 JSON 形式的 401 响应（正常的，因为还没登录）：

```json
{
  "msg": "请求访问：/, 认证失败，无法访问系统资源",
  "code": 401
}
```

### 7.4 常见启动失败

| 报错关键字 | 原因 | 处理 |
|---|---|---|
| `Access denied for user 'root'` | 数据库密码错 | 改 `application-druid.yml` |
| `Communications link failure` | MySQL 没启动 | `Get-Service MySQL84` 检查 |
| `Unknown database 'ry-vue'` | 库没建/库名错 | 重新执行第 3 节 |
| `Unable to connect to Redis` | Redis 没启动 | `redis-cli ping` 验证 |
| `Address already in use: bind` | 8080 端口被占 | 见下方处理 |
| `BeanCreationException` | 配置或依赖问题 | 看 `Caused by:` 堆栈 |

#### 端口被占用处理

```powershell
# 查 8080 端口被哪个进程占用
netstat -ano | findstr :8080

# 杀掉占用进程（替换 <PID>）
Stop-Process -Id <PID> -Force

# 或者改 application.yml 里的 server.port
```

#### Redis 连接失败处理

如果 Redis 设了密码，在 `application.yml` 里加：

```yaml
spring:
  data:
    redis:
      password: <你的 redis 密码>
```

---

## 8. 关键经验总结

### 必记的踩坑点

1. **PowerShell 不支持 `<` 输入重定向** —— 改用 mysql 的 `SOURCE` 命令或切到 CMD。
2. **PowerShell 反引号是转义字符** —— SQL 反引号要双写或避开。
3. **PowerShell 5 默认 GBK 读取** —— 永远显式 `Get-Content -Encoding UTF8`。
4. **mysql 客户端字符集协商默认按系统区域** —— 导入 UTF-8 SQL 必须 `--default-character-set=utf8mb4` + `SET NAMES utf8mb4`。
5. **YAML 路径必须用 `/` 或 `\\`** —— 不要用单 `\`。
6. **Windows 自带 Notepad 会加 BOM 头** —— 用 VS Code / Notepad++ / IDEA。
7. **Maven 多模块必须 `install` 不能只 `compile`** —— 否则子模块互相找不到。
8. **RuoYi-Vue 3.9.x 必须 JDK 17+** —— 用 JDK 8 会启动失败。

### 工作流建议

- 后端启动后**保持 PowerShell 窗口运行**，新开窗口做其他事。
- 改完配置文件**重启后端才生效**（除非开了 devtools 热部署）。
- 首次成功后把所有命令记成 `start.ps1` 脚本，下次一键启动。

### 一键启动脚本示例

`scripts/start-backend.ps1`：

```powershell
# 检查依赖服务
if ((Get-Service MySQL84).Status -ne 'Running') { Start-Service MySQL84 }
if ((Get-Service Redis).Status -ne 'Running')   { Start-Service Redis }

# 进入项目目录
cd D:\learning\ruoyi-ui-autotest\RuoYi-Vue

# 启动后端
mvn spring-boot:run -pl ruoyi-admin
```

执行：`powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1`

---

## 9. 下一步

- [ ] 启动前端（`ruoyi-ui` 目录，`npm install` + `npm run dev`）
- [ ] 浏览器登录验证（默认账号 admin / admin123）
- [ ] Docker 化整套环境（MySQL + Redis + 后端 + 前端）
- [ ] 编写 docker-compose.yml 一键启动测试环境
- [ ] 初始化自动化测试仓库（pytest + Allure）

---

**文档版本**：v1.0
**对应 RuoYi-Vue 版本**：3.9.2
**整理日期**：2026-05-01