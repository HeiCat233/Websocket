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

**URL解码规则：**
- `%XX` 格式的十六进制编码转为对应ASCII字符
- `+` 号转为空格
- 至少支持 `%20`（空格）、`%2F`（斜杠）的解码

**边界情况处理：**
- 请求数据为空时，返回空对象
- 请求行字段不足时，仅解析可用字段
- 非法十六进制编码时，保留原字符

---

### 3.2 模块二：HTTP响应生成器（`http_response.py`）

**职责：** 根据处理结果生成符合HTTP/1.0规范的响应报文。

**核心函数：**

| 名称 | 功能说明 |
|------|---------|
| `build_response(status_code, content_type, body) -> bytes` | 构造完整的HTTP响应报文 |
| `build_error_response(status_code) -> bytes` | 快捷构造HTML格式的错误响应页面 |

**响应报文格式：**

```
HTTP/1.0 {状态码} {状态短语}\r\n
Server: SimplePythonServer/1.0\r\n
Content-Type: {MIME类型}\r\n
Content-Length: {消息体字节数}\r\n
Connection: close\r\n
\r\n
{消息体内容}
```

**支持的状态码：**

| 状态码 | 状态短语 | 触发场景 |
|--------|---------|---------|
| 200 | OK | 请求资源成功 |
| 403 | Forbidden | 路径穿越攻击被拦截 |
| 404 | Not Found | 请求的资源不存在 |
| 405 | Method Not Allowed | 使用了GET以外的方法 |
| 500 | Internal Server Error | 服务器内部异常 |

**错误页面设计：**

`build_error_response()` 生成的HTML页面需包含：
- 大号状态码显示
- 状态短语说明
- 错误描述文字
- 返回首页的链接
- 简洁美观的内嵌CSS样式

---

### 3.3 模块三：文件处理器（`file_handler.py`）

**职责：** 处理所有文件系统操作，包括路径解析、安全检查、MIME类型映射、文件读取。

**核心函数：**

| 名称 | 功能说明 |
|------|---------|
| `resolve_path(url_path: str) -> tuple` | 将URL路径解析为文件系统绝对路径，并做安全检查 |
| `get_mime_type(file_path: str) -> str` | 根据文件扩展名返回对应的MIME类型 |
| `read_file(file_path: str) -> tuple` | 读取文件内容，返回成功标志、内容和MIME类型 |

**路径解析规则：**

1. 若请求路径为 `/`，自动映射到 `/index.html`
2. 去掉路径开头的 `/`，与文档根目录拼接
3. 使用 `os.path.normpath()` 规范化路径（处理 `.` 和 `..`）
4. 使用 `os.path.realpath()` 解析真实绝对路径
5. 验证真实路径是否在文档根目录之内，防止路径穿越攻击

**MIME类型映射表（至少支持）：**

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

**文件读取逻辑：**

1. 检查路径是否存在且为普通文件（非目录）
2. 以二进制模式打开文件，读取全部内容
3. 根据扩展名获取对应MIME类型
4. 若文件不存在或无法读取，返回失败标志
5. 捕获 `IOError` 和 `PermissionError` 异常

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

**全局变量：**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `shutdown_flag` | `threading.Event` | 全局关闭标志，用于协调所有线程优雅退出 |
| `server_socket` | `socket.socket` | 全局服务器Socket引用，用于信号处理中关闭Socket |

**核心函数：**

| 函数名 | 功能说明 |
|--------|---------|
| `handle_client(client_socket, client_address)` | 处理单个客户端连接的完整流程（由工作线程调用） |
| `worker_thread(task_queue)` | 工作线程主循环，从队列获取任务并调用 `handle_client` |
| `signal_handler(signum, frame)` | SIGINT信号处理器，触发优雅关闭 |
| `main()` | 主函数，服务器启动、运行、关闭的完整流程 |

**`handle_client` 处理流程：**

1. 设置客户端Socket超时（30秒）
2. 调用 `socket.recv()` 接收HTTP请求数据
3. 调用 `http_parser.parse_request()` 解析请求
4. 验证请求方法：非GET方法返回405错误
5. 调用 `file_handler.resolve_path()` 解析文件路径
6. 检查路径安全性：不安全返回403错误
7. 调用 `file_handler.read_file()` 读取文件
8. 文件存在：调用 `http_response.build_response(200, ...)` 返回文件内容
9. 文件不存在：调用 `http_response.build_error_response(404)` 返回错误页面
10. 异常情况：返回500错误页面
11. 通过 `socket.sendall()` 发送响应数据
12. 打印格式化的请求处理日志
13. 关闭客户端Socket

**日志输出格式：**
```
[Thread-{线程ID}] GET {请求路径} → {状态码} {状态短语} ({响应字节数} bytes)
```

**`worker_thread` 主循环逻辑：**

1. 进入无限循环，从任务队列获取 `(client_socket, client_address)` 元组
2. 若取到 `(None, None)` 关闭标记，退出循环
3. 否则调用 `handle_client()` 处理请求
4. 使用 `queue.get(timeout=1)` 实现带超时的阻塞获取，允许定期检查关闭标志

**`signal_handler` 处理逻辑：**

1. 打印关闭提示信息
2. 设置 `shutdown_flag` 事件
3. 关闭服务器Socket以解除主线程 `accept()` 阻塞

**`main` 主函数流程：**

1. **初始化阶段：**
   - 注册 `SIGINT` 信号处理器
   - 创建任务队列 `queue.Queue(QUEUE_SIZE)`
   - 创建TCP Socket：`socket.socket(socket.AF_INET, socket.SOCK_STREAM)`
   - 设置 `SO_REUSEADDR` 选项，允许端口复用
   - 绑定地址 `bind((HOST, PORT))`
   - 开始监听 `listen(BACKLOG)`

2. **启动线程池：**
   - 创建 `THREAD_POOL_SIZE` 个工作线程
   - 每个线程执行 `worker_thread(task_queue)`
   - 线程设为守护线程（`daemon=True`）

3. **主循环（接收连接）：**
   - 使用 `server_socket.accept()` 接收客户端连接
   - 设置超时（1秒），允许定期检查关闭标志

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

## 六、代码注释说明

本项目所有源代码均包含详细的中文注释，方便学习和理解：

### 6.1 注释风格

每个模块开头包含：
- **模块功能说明**：概述模块职责
- **技术背景知识**：HTTP协议基础、Socket编程概念
- **关键设计思路**：为什么这样设计，有什么替代方案

### 6.2 函数注释

每个函数包含：
- **功能说明**：函数做什么
- **参数说明**：每个参数的类型、含义、示例
- **返回值说明**：返回值的类型、含义
- **处理流程**：用流程图或步骤说明执行过程
- **边界情况**：可能出现的异常和错误处理

### 6.3 行内注释

关键代码行包含：
- **为什么这样做**：解释设计决策
- **替代方案**：是否有其他实现方式
- **潜在问题**：可能的风险和注意事项

### 6.4 学习建议

1. **从main.py开始**：了解服务器的整体架构
2. **理解handle_client流程**：掌握请求处理的完整流程
3. **学习http_parser**：理解HTTP协议解析原理
4. **研究http_response**：掌握响应报文构建方法
5. **分析file_handler**：理解路径安全和文件读取

---

## 七、技术亮点

1. **底层Socket编程**：从零实现TCP连接管理和HTTP协议解析
2. **多线程架构**：采用线程池 + 任务队列模式，支持高并发
3. **安全设计**：完整的路径安全检查，防止目录遍历攻击
4. **模块化设计**：代码结构清晰，职责分离，易于维护和扩展
5. **优雅关闭**：支持信号处理，确保所有连接和线程正常退出
6. **详细注释**：每个模块、函数、关键代码行都有详细注释，方便学习

---

## 八、扩展建议

### 8.1 功能扩展

- 支持HTTP/1.1的Keep-Alive长连接
- 实现简单的目录列表功能
- 添加Gzip压缩支持
- 实现POST/PUT等方法的文件上传功能

### 8.2 性能优化

- 使用线程池而非每次创建新线程
- 添加连接超时和请求超时配置
- 实现静态文件的缓存机制
- 使用select/poll/epoll处理高并发

### 8.3 安全增强

- 添加请求频率限制
- 实现基本的身份认证
- 添加HTTPS支持（SSL/TLS）
- 实现日志记录和访问统计

---

## 九、常见问题

### Q1: 为什么使用HTTP/1.0而不是HTTP/1.1？

A: HTTP/1.0使用短连接（每请求关闭连接），实现简单，适合教学目的。HTTP/1.1支持长连接、管道化等高级特性，但实现复杂度更高。

### Q2: 为什么设置Socket超时？

A: 防止恶意的半开连接长期占用服务器资源。设置合理的超时时间可以及时释放资源。

### Q3: 工作线程数量如何确定？

A: 对于IO密集型任务（如文件服务），线程数可以多一些（4-8个）。对于CPU密集型任务，线程数应该接近CPU核心数（2-4个）。

### Q4: 如何处理大文件？

A: 当前实现将整个文件读入内存。小文件没问题，大文件可能占用过多内存。可以改为分块读取和发送。

### Q5: 为什么需要路径安全检查？

A: 防止路径穿越攻击。恶意用户可能构造 `/../../etc/passwd` 这样的URL，尝试访问Web目录之外的文件。

---

## 十、许可证

本项目仅用于学习和教育目的，可自由使用和修改。