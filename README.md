# Web服务器设计与实现（Python版）

## 一、项目概述

### 1.1 项目背景

本项目使用Python语言，基于底层Socket API从零实现一个轻量级Web服务器，用于托管个人技术博客网站。通过本项目，深入理解HTTP协议工作原理、Socket网络编程、多线程并发处理等核心概念。

### 1.2 业务场景

搭建的个人技术博客包含以下资源：

```
www/
├── index.html          # 博客首页，包含文章列表和导航
├── about.html          # 关于页面，个人介绍
├── style.css           # 全局CSS样式表
└── article/
    ├── post1.html      # 第一篇文章：Web服务器实现原理
    └── post2.html      # 第二篇文章：多线程编程最佳实践
```

### 1.3 开发环境

| 项目 | 要求 |
|------|------|
| 编程语言 | Python 3.7 及以上 |
| 标准库依赖 | `socket`、`threading`、`queue`、`os`、`sys`、`signal` |
| 外部依赖 | **无**，仅使用Python标准库 |
| 运行平台 | Windows / Linux / macOS 均可 |

---

## 二、项目目录结构

```
webserver/
├── www/                        # 文档根目录（Web资源存放处）
│   ├── index.html              # 博客首页
│   ├── about.html              # 关于页面
│   ├── style.css               # 全局样式表
│   └── article/
│       ├── post1.html          # 文章一：Web服务器实现原理
│       └── post2.html          # 文章二：多线程编程最佳实践
├── src/                        # 源代码目录
│   ├── __init__.py             # 包初始化模块
│   ├── main.py                 # 程序入口
│   ├── config.py               # 【新增】配置管理模块
│   ├── utils.py                # 【新增】工具函数模块
│   ├── request.py              # 【重构】请求处理模块
│   ├── response.py             # 【重构】响应生成模块
│   ├── storage.py              # 【重构】文件处理模块（数据访问层）
│   ├── middleware.py           # 【新增】中间件模块
│   ├── router.py               # 【新增】路由处理模块
│   └── server.py               # 【重构】服务器核心模块
└── README.md                   # 项目说明文档
```

---

## 三、模块功能说明

### 3.1 配置管理模块（`config.py`）

**职责：** 集中管理Web服务器的所有配置参数。

**设计特点：**
- 单一数据源：所有配置集中在一个地方
- 环境变量支持：可通过环境变量覆盖
- 类型安全：明确的类型定义
- 默认值：合理的默认值

**核心类：**

| 类/函数 | 功能说明 |
|--------|---------|
| `ServerConfig` | 服务器配置类，封装所有配置项 |
| `config` | 全局配置单例实例 |

**配置项分类：**

| 分类 | 配置项 | 默认值 |
|------|--------|--------|
| 服务器基础 | HOST, PORT | 0.0.0.0, 8080 |
| 并发处理 | BACKLOG, THREAD_POOL_SIZE, QUEUE_SIZE | 10, 4, 128 |
| 超时设置 | BUFFER_SIZE, CLIENT_TIMEOUT, ACCEPT_TIMEOUT | 8192, 30.0, 1.0 |
| 其他 | SERVER_NAME, DEFAULT_PAGE, CACHE_MAX_AGE | SimplePythonServer/1.0, index.html, 86400 |

---

### 3.2 工具函数模块（`utils.py`）

**职责：** 提供通用工具函数。

**核心函数：**

| 函数 | 功能说明 |
|------|---------|
| `url_decode(url_string)` | URL解码，将百分号编码转换为原始字符 |
| `url_encode(text)` | URL编码，将特殊字符转换为百分号编码 |
| `safe_dict_get(dictionary, key, default)` | 安全获取字典值 |

---

### 3.3 请求处理模块（`request.py`）

**职责：** 负责HTTP请求的解析，提取请求信息。

**核心类与函数：**

| 名称 | 类型 | 功能说明 |
|------|------|---------|
| `HTTPRequest` | 类 | 数据类，封装请求信息（method, path, version, raw_data） |
| `parse_request(raw_data)` | 函数 | 解析原始HTTP请求字节数据 |
| `RequestValidator` | 类 | 请求验证器，提供方法验证 |

**HTTPRequest数据类属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `method` | str | HTTP方法（GET、POST等） |
| `path` | str | 请求路径（如/index.html） |
| `version` | str | HTTP版本（如HTTP/1.0） |
| `raw_data` | bytes | 原始请求字节数据 |

**RequestValidator验证规则：**
- 请求方法必须是GET
- 请求路径必须合法
- 不包含危险字符（.., \\）

---

### 3.4 响应生成模块（`response.py`）

**职责：** 负责HTTP响应的生成，构造符合HTTP协议的响应报文。

**核心类与函数：**

| 名称 | 功能说明 |
|------|---------|
| `HTTPResponse` | 响应类，封装响应信息，支持链式调用 |
| `build_response(status_code, content_type, body)` | 快捷构建HTTP响应 |
| `build_error_response(status_code)` | 构建HTML错误页面 |
| `get_error_description(status_code)` | 获取错误描述 |

**HTTPResponse类特点：**
- 使用`to_bytes()`方法转换为完整的HTTP响应字节
- 自动添加Server、Content-Type、Content-Length等头部
- 支持自定义头部

**支持的状态码：** 200, 400, 403, 404, 405, 408, 500

---

### 3.5 文件处理模块（`storage.py`）

**职责：** 处理所有文件系统操作，包括路径解析、安全检查、MIME类型映射、文件读取。

**核心类：**

| 类 | 功能说明 |
|------|---------|
| `PathResolver` | 路径解析器，负责URL到文件路径的转换和安全检查 |
| `FileHandler` | 文件处理器，负责读取文件内容 |

**PathResolver处理流程：**
1. 处理默认首页（/ → /index.html）
2. 去除前导斜杠
3. 拼接文档根目录
4. 规范化路径（处理.和..）
5. 安全边界检查

**FileHandler读取流程：**
1. 解析文件路径
2. 检查路径安全性
3. 验证文件存在且为普通文件
4. 读取文件内容
5. 返回内容和MIME类型

**MIME类型支持：** .html, .css, .js, .png, .jpg, .gif, .txt等

---

### 3.6 中间件模块（`middleware.py`）

**职责：** 提供请求处理的中间件机制，支持请求/响应的预处理。

**核心概念：**
- 中间件是一种拦截器模式
- 请求经过多个中间件形成处理链
- 支持快速失败（短路响应）

**核心类与函数：**

| 名称 | 功能说明 |
|------|---------|
| `MiddlewareChain` | 中间件链管理器，管理中间件的执行顺序 |
| `logging_middleware` | 日志记录中间件 |
| `method_validator_middleware` | 方法验证中间件 |
| `RequestLogger` | 请求日志记录器 |

**中间件签名：**
```python
Middleware = Callable[[HTTPRequest], Tuple[bool, Optional[HTTPResponse]]]
```

**使用示例：**
```python
chain = MiddlewareChain()
chain.use(logging_middleware)
chain.use(method_validator_middleware)
should_continue, response = chain.execute(request)
```

---

### 3.7 路由处理模块（`router.py`）

**职责：** 管理请求路由，将URL路径映射到对应的处理函数。

**核心类：**

| 类 | 功能说明 |
|------|---------|
| `Route` | 路由类，封装路由信息 |
| `StaticFileHandler` | 静态文件处理器 |
| `Router` | 路由管理器，处理请求分发 |

**Router特点：**
- 支持静态路由注册
- 支持路由装饰器（`@router.route('/path')`）
- 未匹配路由自动使用静态文件处理器

**使用示例：**
```python
@router.route('/about')
def about_page(request):
    return HTTPResponse(200, 'text/html', content)
```

---

### 3.8 服务器核心模块（`server.py`）

**职责：** 实现Web服务器的核心功能，包括Socket通信、多线程处理。

**核心类：**

| 类 | 功能说明 |
|------|---------|
| `ClientHandler` | 客户端处理器，处理单个客户端请求 |
| `WorkerThread` | 工作线程，从队列获取任务并处理 |
| `WebServer` | Web服务器主类，整合所有组件 |

**架构设计：**
- 生产者-消费者模式
- 主线程：接收连接，生产任务
- 工作线程池：处理请求，消费任务

**WebServer主流程：**
1. 创建TCP Socket
2. 启动工作线程池
3. 主循环接收连接
4. 任务加入队列
5. 优雅关闭

---

### 3.9 程序入口（`main.py`）

**职责：** 提供程序入口，启动Web服务器。

**启动方式：**
```bash
python src/main.py
```

---

## 四、模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                      (程序入口)                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                       server.py                              │
│               WebServer, WorkerThread                        │
└──────────┬──────────────────┬───────────────────┬──────────┘
           │                  │                   │
           ▼                  ▼                   ▼
┌──────────────────┐ ┌────────────────┐ ┌────────────────────┐
│    router.py     │ │  middleware.py │ │     request.py     │
│   Router         │ │ MiddlewareChain│ │   HTTPRequest      │
│ StaticFileHandler│ │                │ │  parse_request     │
└────────┬─────────┘ └───────┬────────┘ └────────┬───────────┘
         │                   │                  │
         │                   │                  │
         ▼                   │                  ▼
┌──────────────────┐        │         ┌────────────────────┐
│    storage.py    │        │         │    response.py     │
│  PathResolver    │        │         │   HTTPResponse      │
│   FileHandler    │        │         │  build_response     │
└──────────────────┘        │         └────────────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │     config.py       │
                  │   ServerConfig      │
                  │      config         │
                  └────────────────────┘
```

---

## 五、配置管理

### 5.1 环境变量配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| SERVER_HOST | 监听地址 | 0.0.0.0 |
| SERVER_PORT | 监听端口 | 8080 |
| DOCUMENT_ROOT | 文档根目录 | {项目根目录}/www |
| BACKLOG | 连接队列大小 | 10 |
| THREAD_POOL_SIZE | 工作线程数 | 4 |
| QUEUE_SIZE | 任务队列容量 | 128 |
| BUFFER_SIZE | 接收缓冲区大小 | 8192 |
| CLIENT_TIMEOUT | 客户端超时 | 30.0 |
| ACCEPT_TIMEOUT | accept超时 | 1.0 |

### 5.2 配置优先级

```
环境变量 > 代码默认值
```

---

## 六、运行方式

### 6.1 启动服务器

```bash
cd webserver
python src/main.py
```

### 6.2 服务器启动信息

```
服务器已启动，监听 http://0.0.0.0:8080
文档根目录: /path/to/webserver/www
工作线程数: 4
按 Ctrl+C 停止服务器
```

### 6.3 访问方式

在浏览器中访问：

| 页面 | URL |
|------|-----|
| 首页 | `http://localhost:8080/` |
| 关于页 | `http://localhost:8080/about.html` |
| 文章一 | `http://localhost:8080/article/post1.html` |
| 文章二 | `http://localhost:8080/article/post2.html` |

---

## 七、功能特性

### 7.1 核心功能

- ✅ 静态文件服务（HTML、CSS、JavaScript、图片等）
- ✅ HTTP/1.0 协议支持
- ✅ 多线程并发处理
- ✅ 任务队列缓冲
- ✅ 优雅关闭机制

### 7.2 安全特性

- ✅ 路径穿越攻击防护
- ✅ 请求方法限制（仅支持GET）
- ✅ 文件权限检查

### 7.3 错误处理

- ✅ 404 页面未找到
- ✅ 403 访问禁止
- ✅ 405 方法不允许
- ✅ 408 请求超时
- ✅ 500 服务器内部错误

---

## 八、代码注释说明

### 8.1 注释风格

- **模块级注释**：说明模块职责、功能、设计原则
- **类注释**：说明类的职责、属性、使用方式
- **函数注释**：说明函数功能、参数、返回值、处理流程
- **行内注释**：解释关键代码的设计决策

### 8.2 学习路径

1. **config.py**：了解配置管理机制
2. **request.py**：理解HTTP请求解析
3. **response.py**：掌握响应报文构建
4. **storage.py**：学习路径安全和文件处理
5. **middleware.py**：理解中间件模式
6. **router.py**：掌握路由分发
7. **server.py**：理解服务器核心架构

---

## 九、扩展建议

### 9.1 功能扩展

- 支持HTTP/1.1的Keep-Alive长连接
- 实现动态路由和路由参数
- 添加POST/PUT等方法的文件上传
- 实现简单的模板引擎

### 9.2 性能优化

- 使用线程池而非每次创建新线程
- 实现静态文件的缓存机制
- 使用select/poll/epoll处理高并发
- 添加连接限流

### 9.3 安全增强

- 添加请求频率限制
- 实现基本的身份认证
- 添加HTTPS支持（SSL/TLS）
- 实现更详细的日志和监控

---

## 十、许可证

本项目仅用于学习和教育目的，可自由使用和修改。
