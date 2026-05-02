# RuoYi-Vue 后端启动完整流程（Linux）

> 本文档基于 RuoYi-Vue v3.9.2 + Ubuntu 22.04 LTS + JDK 17 + MySQL 8.x + Redis 整理。
> 同时标注 CentOS 7/8 / RHEL / Rocky / AlmaLinux 系（使用 `yum` / `dnf`）的差异。
>
> **企业实际场景**：测试 / 生产服务器 99% 是 Linux，掌握这套流程比 Windows 版更有职业价值。

---

## 0. 环境前置要求

| 组件 | 版本要求 | 备注 |
|---|---|---|
| OS | Ubuntu 20.04+ / CentOS 7+ / Rocky 8+ | 本文档基于 Ubuntu 22.04 |
| JDK | 17+ | RuoYi-Vue 3.9.x 基于 SpringBoot 3.x |
| Maven | 3.6+ | 推荐 3.8 / 3.9 |
| MySQL | 5.7 / 8.x | 本文档使用 8.x |
| Redis | 6.x+ | 包管理器装的版本即可 |
| Git | 任意近期版本 | |
| Node.js | 16 / 18 | 启动前端时需要（本文档不涵盖） |

### 包管理器速查

| 发行版 | 包管理器 | 服务管理 |
|---|---|---|
| Ubuntu / Debian | `apt` | `systemctl` |
| CentOS 7 | `yum` | `systemctl` |
| CentOS 8+ / Rocky / AlmaLinux | `dnf` | `systemctl` |

> **本文命令以 Ubuntu 为主**，CentOS 系把 `apt install` 换成 `yum install` 或 `dnf install` 即可。

### 用户与权限说明

- 本文档假设你以**普通用户**登录，需要 root 权限的命令前加 `sudo`。
- 生产环境**不要用 root 跑应用**，要建专门的运行账号（如 `ruoyi`）。

---

## 1. 安装基础组件

### 1.1 更新包索引

```bash
# Ubuntu / Debian
sudo apt update && sudo apt upgrade -y

# CentOS / Rocky
sudo dnf update -y
```

### 1.2 安装 Git

```bash
# Ubuntu
sudo apt install -y git

# CentOS / Rocky
sudo dnf install -y git
```

验证：

```bash
git --version
```

### 1.3 安装 JDK 17

```bash
# Ubuntu 22.04 — 官方仓库就有 JDK 17
sudo apt install -y openjdk-17-jdk

# CentOS / Rocky 8+
sudo dnf install -y java-17-openjdk java-17-openjdk-devel
```

> CentOS 7 默认仓库只有 JDK 8/11，要装 JDK 17 需要从 [Adoptium](https://adoptium.net/) 或手动下载 tar.gz 解压。

验证：

```bash
java -version
```

预期输出 `openjdk version "17.x.x"`。

#### 多版本切换（如果机器上有多个 JDK）

```bash
# Ubuntu
sudo update-alternatives --config java

# CentOS / Rocky
sudo alternatives --config java
```

按提示选 JDK 17 对应的序号。

### 1.4 安装 Maven

```bash
# Ubuntu
sudo apt install -y maven

# CentOS / Rocky
sudo dnf install -y maven
```

验证：

```bash
mvn -v
```

预期看到 Maven 3.6+ 且 `Java version: 17.x.x`。

#### 配置阿里云镜像（强烈推荐）

国外中央仓库下载慢，**第一次构建就要配镜像**，否则后面 `mvn install` 会卡几十分钟。

编辑 Maven 配置（用户级，不影响系统）：

```bash
mkdir -p ~/.m2
nano ~/.m2/settings.xml
```

粘贴以下内容：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              https://maven.apache.org/xsd/settings-1.0.0.xsd">
  <mirrors>
    <mirror>
      <id>aliyunmaven</id>
      <mirrorOf>*</mirrorOf>
      <name>阿里云公共仓库</name>
      <url>https://maven.aliyun.com/repository/public</url>
    </mirror>
  </mirrors>
</settings>
```

保存退出（`Ctrl+O` → 回车 → `Ctrl+X`）。

---

## 2. 安装 MySQL

### 2.1 Ubuntu 22.04 安装 MySQL 8

```bash
sudo apt install -y mysql-server
```

启动并设为开机自启：

```bash
sudo systemctl start mysql
sudo systemctl enable mysql
sudo systemctl status mysql       # 应显示 active (running)
```

### 2.2 CentOS / Rocky 8+ 安装 MySQL 8

CentOS 默认源里是 MariaDB，要装 MySQL 需加官方源：

```bash
# 加 MySQL 官方源
sudo dnf install -y https://dev.mysql.com/get/mysql80-community-release-el8-1.noarch.rpm

# 安装
sudo dnf install -y mysql-community-server

# 启动
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

### 2.3 安全初始化

#### Ubuntu 走法

Ubuntu 装完默认 root 用 `auth_socket`（用 sudo 免密登录），先改成密码登录：

```bash
sudo mysql
```

进入 mysql 后：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '你的强密码';
FLUSH PRIVILEGES;
exit;
```

然后跑安全脚本：

```bash
sudo mysql_secure_installation
```

按提示走（删匿名用户、禁远程 root、删 test 库、刷新权限），生产环境全部 `Y`。

#### CentOS 走法

CentOS 装完会生成临时密码，先取出来：

```bash
sudo grep 'temporary password' /var/log/mysqld.log
```

记下临时密码，然后：

```bash
sudo mysql_secure_installation
```

输入临时密码，按提示设新密码（MySQL 8 默认要求强密码：大写+小写+数字+特殊字符，至少 8 位）。

### 2.4 验证登录

```bash
mysql -u root -p
```

输密码进入 `mysql>` 提示符即成功。

### 2.5 字符集检查（重要！）

进入 mysql 后：

```sql
SHOW VARIABLES LIKE 'character%';
SHOW VARIABLES LIKE 'collation%';
```

预期 `character_set_server` 是 `utf8mb4`。如果不是，编辑配置文件：

```bash
# Ubuntu
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# CentOS
sudo nano /etc/my.cnf
```

在 `[mysqld]` 段下加：

```ini
[mysqld]
character-set-server=utf8mb4
collation-server=utf8mb4_general_ci
default-time-zone='+08:00'

[client]
default-character-set=utf8mb4
```

重启 MySQL：

```bash
sudo systemctl restart mysql       # Ubuntu
sudo systemctl restart mysqld      # CentOS
```

> **企业经验**：服务器装好 MySQL 第一件事就是确认字符集，否则等业务数据进来发现乱码就晚了。

---

## 3. 安装 Redis

### 3.1 安装

```bash
# Ubuntu
sudo apt install -y redis-server

# CentOS / Rocky
sudo dnf install -y redis
```

### 3.2 启动并自启

```bash
# Ubuntu
sudo systemctl start redis-server
sudo systemctl enable redis-server

# CentOS / Rocky
sudo systemctl start redis
sudo systemctl enable redis
```

### 3.3 验证

```bash
redis-cli ping
```

应返回 `PONG`。

### 3.4（可选）设置密码

生产环境 Redis 必须设密码。编辑配置：

```bash
sudo nano /etc/redis/redis.conf       # Ubuntu
sudo nano /etc/redis.conf             # CentOS
```

找到 `# requirepass foobared`，去掉 `#` 并改密码：

```
requirepass YourStrongPassword123
```

重启：

```bash
sudo systemctl restart redis-server   # Ubuntu
sudo systemctl restart redis          # CentOS
```

验证：

```bash
redis-cli
> AUTH YourStrongPassword123
> ping
PONG
```

---

## 4. 拉取代码

### 4.1 Fork 官方仓库

浏览器打开 <https://github.com/yangzongzhuan/RuoYi-Vue>，点 **Fork** 到自己账号。

### 4.2 配置 SSH key（推荐，企业里都用 SSH）

```bash
# 生成 key（如果没有）
ssh-keygen -t ed25519 -C "your_email@example.com"
# 一路回车即可

# 取出公钥
cat ~/.ssh/id_ed25519.pub
```

复制输出，到 GitHub → Settings → SSH and GPG keys → New SSH key 粘贴。

测试连接：

```bash
ssh -T git@github.com
# 看到 "Hi <username>! You've successfully authenticated..." 即成功
```

### 4.3 Clone 项目

```bash
mkdir -p ~/projects && cd ~/projects
git clone git@github.com:<你的用户名>/RuoYi-Vue.git
cd RuoYi-Vue
```

> 用 SSH 协议（`git@github.com:`）而不是 HTTPS（`https://github.com/`），以后 push 不用每次输密码。

### 4.4 设置 upstream

```bash
git remote add upstream https://github.com/yangzongzhuan/RuoYi-Vue.git
git remote -v
```

应看到 4 行（origin 的 fetch/push + upstream 的 fetch/push）。

```bash
# 可选：禁掉 upstream 的 push URL，避免误操作
git remote set-url --push upstream no-push
```

---

## 5. 创建数据库 + 导入 SQL

### 5.1 创建数据库

```bash
mysql -u root -p
```

进入 mysql 提示符后：

```sql
CREATE DATABASE IF NOT EXISTS `ry-vue` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
SHOW DATABASES;
```

> Linux shell 里反引号是命令替换符号，所以**进 mysql 提示符执行 SQL 是最稳的**。
> 如果想在 shell 里直接 `-e` 执行：用单引号包整个 SQL，反引号正常用。

### 5.2 导入 SQL（Linux 没字符集坑，但建议显式指定）

退出 mysql，回到 shell：

```bash
cd ~/projects/RuoYi-Vue/sql
ls
# 应能看到 ry_2026xxxx.sql 和 quartz.sql
```

#### 方式 A：shell 重定向（Linux 推荐，简洁）

```bash
mysql -u root -p --default-character-set=utf8mb4 ry-vue < ry_20260417.sql
mysql -u root -p --default-character-set=utf8mb4 ry-vue < quartz.sql
```

> Linux shell 完美支持 `<` 输入重定向，不像 PowerShell。

#### 方式 B：mysql SOURCE 命令

```bash
mysql -u root -p --default-character-set=utf8mb4 ry-vue
```

进入后：

```sql
SET NAMES utf8mb4;
SOURCE /home/<你的用户名>/projects/RuoYi-Vue/sql/ry_20260417.sql;
SOURCE /home/<你的用户名>/projects/RuoYi-Vue/sql/quartz.sql;
```

> Linux 路径用 `/`，没有 Windows 的反斜杠/正斜杠困扰。

### 5.3 验证

```bash
mysql -u root -p ry-vue -e "SHOW TABLES; SELECT user_id, user_name, nick_name FROM sys_user LIMIT 5;"
```

应看到 30+ 张表 + 中文 `若依` 显示正常。

#### 中文乱码处理

如果 `SELECT` 看到 `??` 或 `?¨a?¨a` 等乱码 → 数据已损坏。

排查 + 修复：

```bash
# 查 MySQL 服务端字符集
mysql -u root -p -e "SHOW VARIABLES LIKE 'character%';"
```

如果服务端字符集不是 `utf8mb4`，回到 2.5 修配置 + 重启 → 然后重建库重导入：

```sql
DROP DATABASE `ry-vue`;
CREATE DATABASE `ry-vue` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

按 5.2 重新导入。

---

## 6. 修改 RuoYi 配置

### 6.1 查看配置文件

```bash
cd ~/projects/RuoYi-Vue
cat ruoyi-admin/src/main/resources/application-druid.yml
cat ruoyi-admin/src/main/resources/application.yml
```

> Linux 终端默认 UTF-8，`cat` 直接显示中文，不像 PowerShell 要 `-Encoding UTF8`。

### 6.2 修改数据库密码（必改）

```bash
nano ruoyi-admin/src/main/resources/application-druid.yml
# 或 vim ruoyi-admin/src/main/resources/application-druid.yml
```

找到：

```yaml
master:
    url: jdbc:mysql://localhost:3306/ry-vue?...
    username: root
    password: password
```

改成你的真实密码：

```yaml
password: YourMySQLRootPassword
```

> **特殊字符密码**用双引号包：`password: "MyP@ss:word"`。

保存退出（nano: `Ctrl+O` 回车 `Ctrl+X`；vim: `Esc` `:wq` 回车）。

### 6.3 修改文件上传路径

```bash
nano ruoyi-admin/src/main/resources/application.yml
```

改 `profile` 配置：

```yaml
ruoyi:
  profile: /home/<你的用户名>/ruoyi/uploadPath
  # 或生产环境标准位置：
  # profile: /opt/ruoyi/uploadPath
```

> Linux 标准做法是把应用数据放在 `/opt/<应用名>/` 或 `/var/lib/<应用名>/`，不放用户目录。

### 6.4 创建上传目录

```bash
mkdir -p /home/<你的用户名>/ruoyi/uploadPath
# 或
sudo mkdir -p /opt/ruoyi/uploadPath
sudo chown -R $USER:$USER /opt/ruoyi
```

> 如果用 `/opt/`，要注意权限——目录所有者必须是跑 RuoYi 的用户，否则启动会因为写不进去报错。

### 6.5（可选）Redis 密码配置

如果你给 Redis 设了密码，改 `application.yml`：

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      password: YourStrongPassword123
```

---

## 7. Maven 构建

### 7.1 多模块项目结构

```
RuoYi-Vue/
├── ruoyi-admin       ← 启动入口
├── ruoyi-framework   ← 框架核心
├── ruoyi-system      ← 业务模块
├── ruoyi-common      ← 通用工具
├── ruoyi-quartz      ← 定时任务
├── ruoyi-generator   ← 代码生成器
├── ruoyi-ui          ← 前端
├── sql               ← 初始化 SQL
└── pom.xml           ← Maven 父项目
```

### 7.2 构建命令

```bash
cd ~/projects/RuoYi-Vue
mvn clean install -DskipTests
```

**首次构建**：5–15 分钟下载依赖（已配阿里云镜像会快很多）。

### 7.3 成功标志

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

### 7.4 构建失败常见处理

| 报错 | 原因 | 处理 |
|---|---|---|
| 依赖下载超时 | 国外仓库慢 | 配阿里云镜像（见 1.4） |
| `class file has wrong version 61.0` | JDK 版本太低 | 必须 JDK 17+ |
| 磁盘空间不足 | `~/.m2/repository` 占用 1-2 GB | `df -h ~` 确认空间 |
| 内存不足 OOM | 小内存机器构建会 OOM | 加 swap 或 `export MAVEN_OPTS="-Xmx1g"` |

---

## 8. 启动后端

### 8.1 前台启动（开发调试）

```bash
cd ~/projects/RuoYi-Vue
mvn spring-boot:run -pl ruoyi-admin
```

日志直接打到当前终端，`Ctrl+C` 停止。

### 8.2 成功标志

```
Tomcat started on port(s): 8080 (http) with context path ''
Started RuoYiApplication in xx.xxx seconds
(♥◡♥) RuoYi-Vue启动成功
```

### 8.3 验证（同机）

```bash
curl http://localhost:8080
```

应返回类似：

```
欢迎使用RuoYi后台管理框架，当前版本：v3.9.2，请通过前端地址访问。
```

或 JSON 401。

### 8.4 验证（远程访问）

如果是远程服务器，需要：

#### 1. 防火墙开放 8080 端口

```bash
# Ubuntu (ufw)
sudo ufw allow 8080/tcp
sudo ufw status

# CentOS (firewalld)
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

#### 2. 云服务器要在控制台开安全组

阿里云、腾讯云、AWS 都需要在 Web 控制台开放 8080 端口入站规则，否则系统防火墙开了也连不上。

#### 3. 浏览器访问

```
http://<服务器公网IP>:8080
```

### 8.5 常见启动失败

| 报错 | 处理 |
|---|---|
| `Access denied for user 'root'` | 改 `application-druid.yml` 密码 |
| `Communications link failure` | `sudo systemctl status mysql` 检查 |
| `Unable to connect to Redis` | `redis-cli ping` 验证 |
| `Address already in use: bind` | 端口被占，见下方 |
| `Permission denied` 写文件 | 上传目录权限问题，`chown` 修正 |

#### 端口占用排查

```bash
# 查端口占用
sudo lsof -i:8080
# 或
sudo netstat -tlnp | grep 8080
# 或（推荐，更现代）
sudo ss -tlnp | grep 8080

# 杀进程
sudo kill -9 <PID>
```

---

## 9. 生产化部署

开发用 `mvn spring-boot:run` 没问题，但**生产环境必须用打好的 jar 包 + systemd 管理**，这才是企业标准做法。

### 9.1 打包

```bash
cd ~/projects/RuoYi-Vue
mvn clean package -DskipTests
```

构建产物路径：

```
ruoyi-admin/target/ruoyi-admin.jar
```

### 9.2 部署到标准位置

```bash
sudo mkdir -p /opt/ruoyi/app
sudo cp ruoyi-admin/target/ruoyi-admin.jar /opt/ruoyi/app/
```

### 9.3 创建专用运行账号

```bash
sudo useradd -r -s /bin/false ruoyi
sudo chown -R ruoyi:ruoyi /opt/ruoyi
```

> `-r` 创建系统账号，`-s /bin/false` 禁止登录，纯粹用于跑服务，符合最小权限原则。

### 9.4 创建 systemd 服务

```bash
sudo nano /etc/systemd/system/ruoyi-backend.service
```

内容：

```ini
[Unit]
Description=RuoYi Backend Service
After=network.target mysql.service redis-server.service
Requires=mysql.service redis-server.service

[Service]
Type=simple
User=ruoyi
Group=ruoyi
WorkingDirectory=/opt/ruoyi/app
ExecStart=/usr/bin/java -Xms512m -Xmx2g -jar /opt/ruoyi/app/ruoyi-admin.jar
SuccessExitStatus=143
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/ruoyi/backend.log
StandardError=append:/var/log/ruoyi/backend-error.log

[Install]
WantedBy=multi-user.target
```

> CentOS 上 redis 的服务名是 `redis.service` 不是 `redis-server.service`，对应改一下。

创建日志目录：

```bash
sudo mkdir -p /var/log/ruoyi
sudo chown ruoyi:ruoyi /var/log/ruoyi
```

### 9.5 启动 + 自启

```bash
sudo systemctl daemon-reload
sudo systemctl start ruoyi-backend
sudo systemctl enable ruoyi-backend
sudo systemctl status ruoyi-backend
```

### 9.6 查看日志

```bash
# 实时跟踪
sudo journalctl -u ruoyi-backend -f

# 看应用日志
sudo tail -f /var/log/ruoyi/backend.log

# 看最近 100 行
sudo journalctl -u ruoyi-backend -n 100
```

### 9.7 常用运维命令

```bash
sudo systemctl restart ruoyi-backend     # 重启
sudo systemctl stop ruoyi-backend        # 停止
sudo systemctl disable ruoyi-backend     # 取消自启
```

---

## 10. Linux 与 Windows 关键差异速查

| 项 | Windows | Linux |
|---|---|---|
| 包管理 | 手动下载 / Chocolatey | `apt` / `dnf` / `yum` |
| 服务管理 | `Get-Service` / `Start-Service` | `systemctl` |
| 路径分隔符 | `\` 或 `/` | 只用 `/` |
| 终端编码 | PowerShell 默认 GBK | 默认 UTF-8 |
| `<` 重定向 | PowerShell 不支持 | 完美支持 |
| 文件权限 | ACL，简单粗暴 | rwx + 用户/组，更细粒度 |
| 反引号 | PowerShell 转义符 | shell 命令替换 |
| 环境变量 | `$env:VAR` / `setx` | `$VAR` / `export` |
| 路径示例 | `C:\Program Files\` | `/opt/` `/usr/local/` |
| 行尾符 | CRLF | LF |

---

## 11. 关键经验总结

### 必记的 Linux 最佳实践

1. **永远不要用 root 跑应用** —— 建专用账号（`ruoyi`、`www-data` 等）。
2. **生产环境必须 systemd 管理** —— 不要 `nohup java -jar &`，重启就丢了。
3. **应用部署到 `/opt/` 或 `/var/lib/`** —— 不要放用户目录。
4. **日志写到 `/var/log/<应用>/`** —— 标准位置，方便运维和日志收集。
5. **配置阿里云镜像** —— Linux 服务器即使在国内也建议配，pull 速度差异巨大。
6. **防火墙 + 云安全组双开** —— 只开系统防火墙不够，云控制台也要开。
7. **MySQL 装完先验字符集** —— 否则后面踩中文乱码坑。
8. **用 SSH key 不用 HTTPS** —— 企业仓库都用 SSH，省事且安全。

### 工作流建议

- **开发调试**：`mvn spring-boot:run` 前台启动，看日志方便。
- **测试环境**：打 jar + systemd，模拟生产但允许快速重启。
- **生产环境**：jar + systemd + 监控（Prometheus / 阿里云 ARMS），日志接 ELK。

### 一键启动脚本

`scripts/start-backend.sh`：

```bash
#!/bin/bash
set -e

# 检查依赖服务
sudo systemctl is-active --quiet mysql || sudo systemctl start mysql
sudo systemctl is-active --quiet redis-server || sudo systemctl start redis-server

# 进入项目目录
cd ~/projects/RuoYi-Vue

# 启动后端
mvn spring-boot:run -pl ruoyi-admin
```

加执行权限并运行：

```bash
chmod +x scripts/start-backend.sh
./scripts/start-backend.sh
```

---

## 12. 故障排查清单

启动失败时按这个清单逐项检查：

```bash
# 1. JDK 版本对吗？
java -version

# 2. MySQL 在跑吗？
sudo systemctl status mysql

# 3. Redis 在跑吗？
redis-cli ping

# 4. 数据库能连吗？
mysql -u root -p ry-vue -e "SHOW TABLES;"

# 5. 配置文件密码改了吗？
grep "password" ~/projects/RuoYi-Vue/ruoyi-admin/src/main/resources/application-druid.yml

# 6. 上传目录存在 + 有权限吗？
ls -la /opt/ruoyi/uploadPath
# 或
ls -la ~/ruoyi/uploadPath

# 7. 8080 端口被占了吗？
sudo ss -tlnp | grep 8080

# 8. 防火墙开了吗？
sudo ufw status                              # Ubuntu
sudo firewall-cmd --list-ports              # CentOS

# 9. SELinux 在 enforcing 吗？（CentOS 系）
getenforce
# 如果是 Enforcing 又遇到莫名权限拒绝，临时关闭测试：
# sudo setenforce 0
```

---

## 13. 下一步

- [ ] 启动前端（`ruoyi-ui` 目录）
- [ ] 配 Nginx 反向代理（前端 + 后端统一域名）
- [ ] HTTPS 证书（Let's Encrypt + certbot）
- [ ] 接入日志收集（ELK / Loki）
- [ ] Docker 化部署（docker-compose）
- [ ] CI/CD 流水线（Jenkins / GitHub Actions）

---

**文档版本**：v1.0
**对应 RuoYi-Vue 版本**：3.9.2
**整理日期**：2026-05-01
**适用系统**：Ubuntu 20.04+ / CentOS 7+ / Rocky 8+ / RHEL 7+
