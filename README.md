# Web服务器设计与实现（Python版）

---

## 一、项目概述

### 1.1 项目背景

本项目使用 Python 语言，基于底层 Socket API 从零实现一个轻量级 Web 服务器，用于托管个人技术博客网站。通过本项目，深入理解以下核心概念：

| 核心概念 | 学习目标 |
|---------|---------|
| **HTTP 协议** | 理解请求/响应格式、状态码、头部字段 |
| **Socket 编程** | 掌握 TCP 连接建立、数据收发、端口监听 |
| **多线程并发** | 理解线程池、任务队列、线程同步 |
| **安全防护** | 学习路径穿越攻击防护、输入验证 |
| **模块化设计** | 掌握分层架构、职责分离、低耦合设计 |

### 1.2 业务场景

搭建的个人技术博客包含以下资源：

```
www/
├── index.html          # 博客首页，包含文章列表和导航
├── about.html          # 关于页面，个人介绍
├── style.css           # 全局CSS样式表
├── avatar.png          # 头像图片
└── article/
    ├── post1.html      # 第一篇文章：Web服务器实现原理
    └── post2.html      # 第二篇文章：多线程编程最佳实践
```

### 1.3 开发环境

| 项目 | 要求 | 说明 |
|------|------|------|
| 编程语言 | Python 3.7+ | 支持 dataclass、f-string |
| 标准库依赖 | socket、threading、queue、os、sys、signal | 无需额外安装 |
| 运行平台 | Windows / Linux / macOS | 跨平台支持 |
| 代码风格 | PEP 8 | 规范的代码格式 |

---

## 二、项目目录结构

### 2.1 目录结构总览

```
webserver/                              # 项目根目录
├── config/                             # 配置层：集中管理所有配置参数
│   └── __init__.py                    # Settings类 + 全局配置单例
├── controllers/                        # 控制层：处理HTTP请求，协调服务调用
│   ├── __init__.py                     # 控制器导出
│   ├── static_controller.py            # 静态文件请求处理
│   └── error_controller.py             # 错误响应处理
├── routes/                             # 路由层：URL路径与处理器的映射
│   └── __init__.py                     # Router类 + 路由注册管理
├── services/                           # 服务层：核心业务逻辑实现
│   ├── __init__.py                     # 服务导出
│   ├── request_service.py              # HTTP请求解析
│   ├── response_service.py             # HTTP响应生成
│   └── file_service.py                 # 文件系统操作
├── utils/                              # 工具层：通用工具函数
│   └── __init__.py                     # URL编解码、字典安全访问等
├── www/                                # 静态资源目录（文档根目录）
│   ├── index.html
│   ├── about.html
│   ├── style.css
│   ├── avatar.png
│   └── article/
│       ├── post1.html
│       └── post2.html
├── app.py                              # 应用核心：WebServer主类
├── main.py                             # 程序入口：启动服务器
└── README.md                           # 项目说明文档
```

### 2.2 目录职责说明

| 目录 | 职责 | 设计原则 |
|------|------|---------|
| **config/** | 集中管理配置参数 | 单一职责、易于修改 |
| **controllers/** | 接收请求、调用服务、返回响应 | 协调者模式 |
| **routes/** | 路由分发、URL映射 | 策略模式 |
| **services/** | 核心业务逻辑 | 业务逻辑封装 |
| **utils/** | 通用工具函数 | 无状态、可复用 |
| **www/** | 静态资源文件 | 与代码分离 |

---

## 三、模块功能详细说明

### 3.1 配置模块（`config/__init__.py`）

**职责**：集中管理Web服务器的所有配置参数，支持环境变量覆盖。

**核心类：`Settings`**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `HOST` | str | '0.0.0.0' | 监听地址，'0.0.0.0'监听所有接口 |
| `PORT` | int | 8080 | 监听端口 |
| `DOCUMENT_ROOT` | str | ./www | 静态资源根目录 |
| `BACKLOG` | int | 10 | TCP连接队列大小 |
| `THREAD_POOL_SIZE` | int | 4 | 工作线程数量 |
| `QUEUE_SIZE` | int | 128 | 任务队列容量 |
| `BUFFER_SIZE` | int | 8192 | 接收缓冲区大小（字节） |
| `CLIENT_TIMEOUT` | float | 30.0 | 客户端连接超时（秒） |
| `ACCEPT_TIMEOUT` | float | 1.0 | accept超时（秒） |
| `QUEUE_GET_TIMEOUT` | float | 1.0 | 队列获取超时（秒） |
| `SERVER_NAME` | str | SimplePythonServer/1.0 | 服务器标识 |
| `DEFAULT_PAGE` | str | index.html | 默认首页 |
| `CACHE_MAX_AGE` | int | 86400 | 缓存有效期（秒） |

**配置优先级**：环境变量 > 代码默认值

**使用示例**：
```python
from config import settings

print(f"服务器监听: {settings.HOST}:{settings.PORT}")
print(f"文档根目录: {settings.get_document_root()}")
```

---

### 3.2 工具模块（`utils/__init__.py`）

**职责**：提供通用工具函数，供其他模块调用。

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `url_decode(url_string)` | URL解码 | url_string: str | str |
| `url_encode(text)` | URL编码 | text: str | str |
| `safe_dict_get(d, k, default)` | 安全获取字典值 | d: dict, k: any, default: any | any |

**URL编码规则说明**：
- `%XX`：十六进制编码的字符（如 `%E4%BD%A0` = "你"）
- `+`：表示空格（表单数据中常用）
- 保留字符：`a-z, A-Z, 0-9, -, _, ., ~`

---

### 3.3 服务层（`services/`）

#### 3.3.1 请求服务（`services/request_service.py`）

**职责**：负责HTTP请求的解析和验证。

**核心类与函数**：

| 名称 | 类型 | 功能 |
|------|------|------|
| `HTTPRequest` | dataclass | 封装请求信息 |
| `parse_request(raw_data)` | 函数 | 解析原始HTTP请求 |
| `RequestValidator` | 类 | 请求验证器 |

**HTTPRequest 属性**：
- `method`: HTTP方法（GET、POST等）
- `path`: 请求路径
- `version`: HTTP版本
- `raw_data`: 原始字节数据

**HTTP请求格式**：
```
GET /index.html HTTP/1.1\r\n
Host: localhost:8080\r\n
\r\n
```

**RequestValidator 验证规则**：
1. 请求方法必须是 GET
2. 请求路径不能包含 `..` 或 `\`（防止路径穿越）

#### 3.3.2 响应服务（`services/response_service.py`）

**职责**：负责HTTP响应的生成。

**核心类与函数**：

| 名称 | 功能 |
|------|------|
| `HTTPResponse` | 响应类，封装响应信息 |
| `build_response(status, type, body)` | 构建成功响应 |
| `build_error_response(status)` | 构建错误响应页面 |
| `get_error_description(status)` | 获取中文错误描述 |

**支持的HTTP状态码**：

| 状态码 | 短语 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求格式错误 |
| 403 | Forbidden | 访问禁止 |
| 404 | Not Found | 页面未找到 |
| 405 | Method Not Allowed | 方法不允许 |
| 408 | Request Timeout | 请求超时 |
| 500 | Internal Server Error | 服务器内部错误 |

**HTTP响应格式**：
```
HTTP/1.0 200 OK\r\n
Server: SimplePythonServer/1.0\r\n
Content-Type: text/html\r\n
Content-Length: 1234\r\n
Connection: close\r\n
\r\n
<html>...</html>
```

#### 3.3.3 文件服务（`services/file_service.py`）

**职责**：处理所有文件系统操作，包含路径安全检查。

**核心类**：

| 类 | 功能 |
|----|------|
| `PathResolver` | 路径解析器，将URL路径转换为文件系统路径 |
| `FileService` | 文件处理器，读取文件内容 |

**PathResolver 处理流程**：
```
1. 处理默认首页     / → /index.html
2. 去除前导斜杠    /style.css → style.css
3. 拼接文档根目录  style.css → /www/style.css
4. 规范化路径      处理 . 和 ..
5. 安全边界检查    验证是否在 DOCUMENT_ROOT 内
```

**安全说明**：使用 `os.path.realpath()` 获取真实路径，防止符号链接攻击。

---

### 3.4 控制器层（`controllers/`）

**职责**：处理HTTP请求，协调服务调用。

| 控制器 | 职责 |
|--------|------|
| `StaticFileController` | 处理静态文件请求 |
| `ErrorController` | 处理错误响应 |

**StaticFileController 处理流程**：
```
1. 接收原始请求数据
2. 解析请求 → 获取URL路径
3. 调用 FileService.read() 读取文件
4. 成功 → 构建200响应
5. 失败 → 构建对应错误响应
```

---

### 3.5 路由层（`routes/__init__.py`）

**职责**：管理URL路径与处理器的映射关系。

**核心类：`Router`**

| 方法 | 功能 |
|------|------|
| `add_route(path, handler)` | 注册路由 |
| `route(path)` | 路由装饰器 |
| `handle(raw_data)` | 处理请求（分发到对应控制器） |
| `list_routes()` | 列出所有注册的路由 |

**扩展示例**：
```python
from routes import router

@router.route('/api/data')
def api_handler(request):
    # 自定义API处理逻辑
    return response
```

---

### 3.6 应用核心（`app.py`）

**职责**：实现Web服务器的核心功能，包括Socket通信和多线程处理。

**核心类**：

| 类 | 职责 |
|----|------|
| `ClientHandler` | 处理单个客户端请求 |
| `WorkerThread` | 工作线程，消费任务队列 |
| `WebServer` | 服务器主类，整合所有组件 |

**架构设计：生产者-消费者模式**

```
┌─────────────────────────────────────────────────────────────┐
│                      WebServer (主线程)                      │
│  ┌─────────────┐    ┌─────────────┐                        │
│  │ Server Socket│───▶│   Accept    │───▶│   Task Queue   │  │
│  │  (监听端口)   │    │  (接收连接)   │    │   (任务缓冲)    │  │
│  └─────────────┘    └─────────────┘    └────────┬────────┘  │
└────────────────────────────────────────────────│─────────────┘
                                                 │
        ┌────────────────────────────────────────┼─────────────────────────┐
        │                                        │                         │
        ▼                                        ▼                         ▼
┌───────────────┐                     ┌───────────────┐          ┌───────────────┐
│ WorkerThread 1│                     │ WorkerThread 2│          │ WorkerThread N│
│  ┌─────────┐  │                     │  ┌─────────┐  │          │  ┌─────────┐  │
│  │Client   │  │                     │  │Client   │  │          │  │Client   │  │
│  │Handler  │  │                     │  │Handler  │  │          │  │Handler  │  │
│  └─────────┘  │                     │  └─────────┘  │          │  └─────────┘  │
└───────────────┘                     └───────────────┘          └───────────────┘
```

**ClientHandler 处理流程**：
```
1. 接收请求数据 → recv()
2. 解析请求 → parse_request()
3. 验证请求方法 → RequestValidator.validate_method()
4. 路由分发 → router.handle()
5. 发送响应 → sendall()
6. 关闭连接 → close()
```

---

### 3.7 程序入口（`main.py`）

**职责**：提供程序入口，启动Web服务器。

```python
from app import create_app

def main():
    server = create_app()
    server.start()

if __name__ == '__main__':
    main()
```

---

## 四、模块依赖关系图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                    main.py                                  │
│                                   (程序入口)                                  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                    app.py                                   │
│                          WebServer / ClientHandler                          │
└────────────┬───────────────────────┬───────────────────────┬───────────────┘
             │                       │                       │
             ▼                       ▼                       ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│      routes/          │ │     controllers/      │ │       services/       │
│      Router           │ │ StaticFileController  │ │   parse_request      │
│                       │ │ ErrorController       │ │   build_response     │
└───────────┬───────────┘ └───────────┬───────────┘ └───────────┬───────────┘
            │                         │                         │
            │                         │                         │
            ▼                         │                         ▼
┌───────────────────────┐            │           ┌───────────────────────┐
│    controllers/       │            │           │     file_service      │
│ StaticFileController  │            │           │     PathResolver      │
└───────────────────────┘            │           └───────────┬───────────┘
                                     │                       │
                                     │                       ▼
                         ┌───────────┴───────────┐ ┌───────────────────────┐
                         │       services/       │ │       config/         │
                         │    request_service    │ │       Settings        │
                         │    response_service   │ └───────────────────────┘
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │       utils/          │
                         │    url_decode         │
                         └───────────────────────┘
```

---

## 五、配置管理

### 5.1 环境变量配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SERVER_HOST` | 监听地址 | 0.0.0.0 |
| `SERVER_PORT` | 监听端口 | 8080 |
| `DOCUMENT_ROOT` | 文档根目录 | ./www |
| `BACKLOG` | 连接队列大小 | 10 |
| `THREAD_POOL_SIZE` | 工作线程数 | 4 |
| `QUEUE_SIZE` | 任务队列容量 | 128 |
| `BUFFER_SIZE` | 缓冲区大小 | 8192 |
| `CLIENT_TIMEOUT` | 客户端超时(秒) | 30.0 |
| `ACCEPT_TIMEOUT` | accept超时(秒) | 1.0 |

### 5.2 配置使用示例

**方式1：通过环境变量设置**（Linux/macOS）：
```bash
export SERVER_PORT=8000
export THREAD_POOL_SIZE=8
python main.py
```

**方式2：通过环境变量设置**（Windows PowerShell）：
```powershell
$env:SERVER_PORT = "8000"
$env:THREAD_POOL_SIZE = "8"
python main.py
```

---

## 六、运行方式

### 6.1 启动服务器

**方式1：直接运行**（推荐）
```bash
cd webserver
python main.py
```

**方式2：使用模块方式**
```bash
cd webserver
python -m main
```

### 6.2 服务器启动信息

```
服务器已启动，监听 http://0.0.0.0:8080
文档根目录: /path/to/webserver/www
工作线程数: 4
按 Ctrl+C 停止服务器
```

### 6.3 访问方式

| 页面 | URL |
|------|-----|
| 首页 | `http://localhost:8080/` |
| 关于页 | `http://localhost:8080/about.html` |
| 文章一 | `http://localhost:8080/article/post1.html` |
| 文章二 | `http://localhost:8080/article/post2.html` |
| 样式表 | `http://localhost:8080/style.css` |

### 6.4 测试错误页面

| 测试场景 | URL | 预期状态码 |
|----------|-----|-----------|
| 404 页面未找到 | `http://localhost:8080/nonexist.html` | 404 |
| 403 路径穿越 | `http://localhost:8080/../etc/passwd` | 403 |

---

## 七、功能特性

### 7.1 核心功能

| 功能 | 说明 | 实现位置 |
|------|------|---------|
| ✅ 静态文件服务 | 支持 HTML/CSS/JS/图片等 | `file_service.py` |
| ✅ HTTP/1.0 协议 | 标准HTTP响应格式 | `response_service.py` |
| ✅ 多线程并发 | 线程池 + 任务队列 | `app.py` |
| ✅ 任务队列缓冲 | 平滑流量峰值 | `app.py` |
| ✅ 优雅关闭 | 安全停止服务器 | `app.py` |

### 7.2 安全特性

| 特性 | 说明 | 实现位置 |
|------|------|---------|
| ✅ 路径穿越防护 | 验证真实路径边界 | `file_service.py` |
| ✅ 请求方法限制 | 仅支持 GET | `request_service.py` |
| ✅ 文件权限检查 | 捕获 IOError | `file_service.py` |

### 7.3 错误处理

| 状态码 | 场景 | 处理方式 |
|--------|------|---------|
| 404 | 文件不存在 | 返回错误页面 |
| 403 | 路径非法 | 返回错误页面 |
| 405 | 方法不允许 | 返回错误页面 |
| 408 | 请求超时 | 返回错误页面 |
| 500 | 服务器错误 | 返回错误页面 |

---

## 八、代码注释说明

### 8.1 注释规范

| 注释类型 | 格式 | 示例 |
|----------|------|------|
| **模块注释** | 模块顶部，说明职责和功能 | `""" 配置模块... """` |
| **类注释** | 类定义上方，说明职责和属性 | `""" Settings类... """` |
| **函数注释** | 函数定义上方，说明参数和返回值 | `""" 读取文件... """` |
| **行内注释** | 代码右侧或上方，解释关键逻辑 | `# 设置超时` |

### 8.2 学习路径建议

```
入门阶段（理解基础）:
├── config/__init__.py      # 配置管理机制
├── utils/__init__.py       # 工具函数
└── services/request_service.py  # HTTP请求解析

进阶阶段（理解流程）:
├── services/response_service.py # HTTP响应生成
├── services/file_service.py     # 文件处理
└── controllers/static_controller.py # 请求处理

高级阶段（理解架构）:
├── routes/__init__.py      # 路由分发
├── app.py                  # 服务器核心
└── main.py                 # 程序入口
```

---

## 九、扩展建议

### 9.1 功能扩展

| 扩展项 | 说明 | 实现难度 |
|--------|------|---------|
| HTTP/1.1 Keep-Alive | 支持长连接 | 中等 |
| 动态路由 | 支持路由参数 | 中等 |
| 文件上传 | 支持 POST 方法 | 中等 |
| 模板引擎 | 支持动态页面 | 较高 |
| HTTPS | 添加 SSL/TLS 支持 | 较高 |

### 9.2 性能优化

| 优化项 | 说明 | 预期效果 |
|--------|------|---------|
| 静态文件缓存 | 内存缓存常用文件 | 减少磁盘IO |
| 连接池 | 复用客户端连接 | 减少连接开销 |
| Gzip压缩 | 压缩响应内容 | 减少带宽占用 |
| 限流 | 限制并发连接数 | 防止服务器过载 |

### 9.3 安全增强

| 增强项 | 说明 | 重要性 |
|--------|------|---------|
| 请求频率限制 | 防止暴力攻击 | 高 |
| 输入验证 | 严格验证请求参数 | 高 |
| 日志记录 | 记录请求和错误 | 中 |
| 访问控制 | IP白名单/黑名单 | 中 |

---

## 十、常见问题

### Q1: 为什么启动时报错 "ImportError: attempted relative import"?

**原因**：使用了相对导入但直接运行了模块文件。

**解决方案**：从项目根目录运行：
```bash
cd webserver
python main.py
```

### Q2: 如何修改服务器监听端口?

**方式1**：设置环境变量
```bash
export SERVER_PORT=8000
python main.py
```

**方式2**：修改 `config/__init__.py` 中的默认值
```python
self.PORT = int(os.environ.get('SERVER_PORT', '8000'))
```

### Q3: 如何添加新的静态文件?

将文件放入 `www/` 目录即可，服务器会自动识别。

### Q4: 如何添加自定义路由?

```python
from routes import router

@router.route('/custom/path')
def custom_handler(raw_data):
    # 处理逻辑
    return (response_bytes, status_code)
```

### Q5: 如何查看服务器运行日志?

服务器会在控制台输出请求日志：
```
[Thread-12345] GET /index.html → 200 (1024 bytes)
```

---

## 十一、许可证

本项目仅用于学习和教育目的，可自由使用和修改。

---

*最后更新：2024年1月*
