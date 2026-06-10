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

用户通过浏览器访问 `http://localhost:8080` 即可浏览博客。点击链接在页面间跳转，CSS样式正常加载，图片正常显示。访问不存在的路径返回404错误页面。

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
│   ├── main.py                 # 主程序入口，Socket通信与多线程管理
│   ├── http_parser.py          # HTTP请求解析模块
│   ├── http_response.py        # HTTP响应生成模块
│   └── file_handler.py         # 文件处理模块
└── README.md                   # 项目说明文档
```

---

## 三、模块功能说明

### 3.1 模块一：HTTP请求解析器（`http_parser.py`）

**职责：** 解析客户端发来的原始HTTP请求报文，提取请求行中的方法、路径、版本信息。

**核心类与函数：**

| 名称 | 类型 | 功能说明 |
|------|------|---------|
| `HTTPRequest` | 类 | 封装解析后的HTTP请求信息，包含 `method`、`path`、`version`、`raw_data` 四个属性 |
| `parse_request(raw_data: bytes) -> HTTPRequest` | 函数 | 解析原始HTTP请求字节数据，返回 `HTTPRequest` 对象 |
| `url_decode(url_string: str) -> str` | 函数 | 对URL中的百分号编码（如 `%20`）进行解码 |

**处理流程：**

1. 将接收到的字节数据解码为UTF-8字符串
2. 按 `\r\n` 分割数据行，提取第一行作为请求行
3. 按空格分割请求行，依次提取方法、路径、HTTP版本
4. 对路径调用 `url_decode()` 进行URL解码
5. 将解析结果封装到 `HTTPRequest` 对象中返回

---

### 3.2 模块二：HTTP响应生成器（`http_response.py`）

**职责：** 根据处理结果生成符合HTTP/1.0规范的响应报文。

**核心函数：**

| 名称 | 功能说明 |
|------|---------|
| `build_response(status_code, content_type, body) -> bytes` | 构造完整的HTTP响应报文 |
| `build_error_response(status_code) -> bytes` | 快捷构造HTML格式的错误响应页面 |

**支持的状态码：**

| 状态码 | 状态短语 | 触发场景 |
|--------|---------|---------|
| 200 | OK | 请求资源成功 |
| 403 | Forbidden | 路径穿越攻击被拦截 |
| 404 | Not Found | 请求的资源不存在 |
| 405 | Method Not Allowed | 使用了GET以外的方法 |
| 500 | Internal Server Error | 服务器内部异常 |

---

### 3.3 模块三：文件处理器（`file_handler.py`）

**职责：** 处理所有文件系统操作，包括路径解析、安全检查、MIME类型映射、文件读取。

**核心函数：**

| 名称 | 功能说明 |
|------|---------|
| `resolve_path(url_path: str) -> tuple` | 将URL路径解析为文件系统绝对路径，并做安全检查 |
| `get_mime_type(file_path: str) -> str` | 根据文件扩展名返回对应的MIME类型 |
| `read_file(file_path: str) -> tuple` | 读取文件内容，返回成功标志、内容和MIME类型 |

**MIME类型映射表：**

| 扩展名 | MIME类型 |
|--------|---------|
| .html / .htm | text/html |
| .css | text/css |
| .js | application/javascript |
| .png | image/png |
| .jpg / .jpeg | image/jpeg |
| .gif | image/gif |
| .txt | text/plain |
| 其他 | application/octet-stream |

---

### 3.4 主程序（`main.py`）

**职责：** 整合所有模块，实现完整的Web服务器功能，包括Socket通信和多线程并发处理。

**配置常量：**

| 常量名 | 建议值 | 说明 |
|--------|--------|------|
| `HOST` | `'0.0.0.0'` | 监听所有网络接口 |
| `PORT` | `8080` | 监听端口号 |
| `BACKLOG` | `10` | 最大等待连接队列长度 |
| `THREAD_POOL_SIZE` | `4` | 工作线程数量 |
| `QUEUE_SIZE` | `128` | 任务队列最大容量 |
| `BUFFER_SIZE` | `8192` | 接收数据缓冲区大小（字节） |

**核心函数：**

| 函数名 | 功能说明 |
|--------|---------|
| `handle_client(client_socket, client_address)` | 处理单个客户端连接的完整流程 |
| `worker_thread(task_queue)` | 工作线程主循环，从队列获取任务并调用 `handle_client` |
| `signal_handler(signum, frame)` | SIGINT信号处理器，触发优雅关闭 |
| `main()` | 主函数，服务器启动、运行、关闭的完整流程 |

---

## 四、运行方式

### 4.1 启动服务器

```bash
cd webserver
python src/main.py
```

### 4.2 服务器启动信息

```
服务器已启动，监听 http://0.0.0.0:8080
文档根目录: /path/to/webserver/www
工作线程数: 4
按 Ctrl+C 停止服务器
```

### 4.3 访问方式

在浏览器中访问以下地址：

| 页面 | URL |
|------|-----|
| 首页 | `http://localhost:8080/` |
| 关于页 | `http://localhost:8080/about.html` |
| 文章一 | `http://localhost:8080/article/post1.html` |
| 文章二 | `http://localhost:8080/article/post2.html` |

---

## 五、功能特性

### 5.1 核心功能

- ✅ 静态文件服务（HTML、CSS、JavaScript、图片等）
- ✅ HTTP/1.0 协议支持
- ✅ 多线程并发处理
- ✅ 任务队列缓冲
- ✅ 优雅关闭机制

### 5.2 安全特性

- ✅ 路径穿越攻击防护
- ✅ 请求方法限制（仅支持GET）
- ✅ 文件权限检查

### 5.3 错误处理

- ✅ 404 页面未找到
- ✅ 403 访问禁止
- ✅ 405 方法不允许
- ✅ 500 服务器内部错误

---

## 六、技术亮点

1. **底层Socket编程**：从零实现TCP连接管理和HTTP协议解析
2. **多线程架构**：采用线程池 + 任务队列模式，支持高并发
3. **安全设计**：完整的路径安全检查，防止目录遍历攻击
4. **模块化设计**：代码结构清晰，职责分离，易于维护和扩展
5. **优雅关闭**：支持信号处理，确保所有连接和线程正常退出