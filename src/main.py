"""
================================================================================
HTTP请求解析模块
================================================================================

【模块功能】
本模块负责解析客户端发来的原始HTTP请求报文，提取请求行中的关键信息。

【HTTP协议基础】
HTTP（HyperText Transfer Protocol）是Web通信的基础协议，采用请求-响应模型：
- 客户端发送HTTP请求（Request）
- 服务器返回HTTP响应（Response）

【HTTP请求报文格式】
    GET /index.html HTTP/1.1\r\n       ← 请求行：方法 路径 HTTP版本
    Host: localhost:8080\r\n           ← 请求头（可以有多个）
    User-Agent: Mozilla/5.0\r\n
    \r\n                               ← 空行，标识头部结束
    [请求体（GET请求通常为空）]

【什么是URL编码】
URL中某些字符无法直接使用（如空格、中文、特殊符号），需要百分号编码：
- 空格 → %20 或 +
- 中文"你" → %E4%BD%A0（UTF-8编码的十六进制表示）
- 斜杠/ → %2F

================================================================================
"""

import socket      # 底层网络通信库，用于创建TCP连接
import threading   # 多线程支持，实现并发处理多个客户端请求
import queue       # 线程安全的任务队列，用于负载均衡
import os          # 操作系统接口，用于路径处理和文件操作
import sys         # 系统相关功能，用于退出程序
import signal      # 信号处理模块，用于优雅关闭服务器（Ctrl+C）

# 导入自定义模块
from http_parser import parse_request    # HTTP请求解析器
from http_response import build_response, build_error_response  # HTTP响应生成器
from file_handler import resolve_path, read_file  # 文件处理器

# ==================== 服务器配置常量 ====================
# 【为什么需要这些配置？】
# 1. HOST/PORT：确定服务器监听的地址，这是客户端访问的唯一标识
# 2. BACKLOG：TCP三次握手后的全连接队列长度，影响并发能力
# 3. THREAD_POOL_SIZE：工作线程数量，决定同时处理多少个请求
# 4. QUEUE_SIZE：任务队列容量，防止高并发时内存溢出
# 5. BUFFER_SIZE：每次recv()读取的数据量，影响内存使用和效率

HOST = '0.0.0.0'           # 监听地址：'0.0.0.0'表示接受所有网络接口的连接
                            # '127.0.0.1'或'localhost'只接受本机访问
PORT = 8080                # 监听端口号：客户端通过此端口访问服务器
                            # 常用端口：80(HTTP)、443(HTTPS)、8080(开发测试)
BACKLOG = 10               # TCP连接队列最大长度：等待处理的连接数上限
                            # 超过10个的连接会被客户端重试
THREAD_POOL_SIZE = 4       # 工作线程数量：同时处理4个客户端请求
                            # 建议：CPU密集型2-4核，IO密集型4-8核
QUEUE_SIZE = 128           # 任务队列容量：最多缓存128个待处理请求
                            # 超过128个请求会被直接拒绝
BUFFER_SIZE = 8192         # 接收缓冲区大小：单次recv()最多读取8KB数据
                            # 8KB对于普通HTTP请求足够，通常一行header<1KB

# 全局变量：用于优雅关闭机制
# 【为什么需要全局变量？】
# 1. shutdown_flag：主线程和工作线程之间共享，用于协调关闭
# 2. server_socket：信号处理器需要关闭socket，触发accept()异常退出
shutdown_flag = threading.Event()  # 线程间通信标志，触发服务器关闭
server_socket = None               # 服务器Socket对象，供信号处理器访问


def handle_client(client_socket, client_address):
    """
    处理单个客户端的完整请求流程
    
    【工作流程图】
    ┌─────────────────┐
    │  接收HTTP请求    │ ← client_socket.recv(BUFFER_SIZE)
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  解析HTTP请求    │ → 提取 method, path, version
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  验证请求方法    │ → 只允许GET
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  路径安全检查    │ → 防止 ../ 路径穿越
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  读取文件内容    │ → 返回 (success, content, mime_type)
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  构建HTTP响应    │ → 200 OK / 404 Not Found
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  发送响应并关闭  │ → socket.sendall() + socket.close()
    └─────────────────┘
    
    【Socket通信流程】
    1. server_socket.accept() → 返回 client_socket（客户端连接）
    2. client_socket.recv() → 接收客户端数据
    3. client_socket.sendall() → 发送响应数据
    4. client_socket.close() → 关闭连接（HTTP/1.0短连接）
    
    【为什么要设置超时？】
    - 防止恶意的半开连接占用服务器资源
    - 30秒内没有数据传输就强制断开
    
    参数：
        client_socket: 客户端Socket连接对象
                      【类型】socket.socket
                      【来源】server_socket.accept()的返回值
        client_address: 客户端地址元组 (ip, port)
                       【类型】tuple，如 ('192.168.1.100', 52341)
    """
    # 获取当前工作线程ID，用于日志追踪
    # 【为什么需要线程ID？】
    # 多线程环境下，日志需要标记是哪个线程处理的，便于调试和性能分析
    thread_id = threading.current_thread().ident
    
    # 默认状态码：万一出现未捕获的异常，至少有合理的错误码
    status_code = 500              # 默认状态码：内部服务器错误
    status_phrase = "Internal Server Error"  # 默认状态描述
    response_bytes = 0             # 响应数据字节数，用于日志记录
    
    try:
        # 【设置Socket超时】
        # 作用：防止客户端连接后不发送数据，长期占用服务器资源
        # 时间：30秒足够完成一个正常的HTTP请求
        client_socket.settimeout(30.0)
        
        # 【接收HTTP请求数据】
        # recv(BUFFER_SIZE)：从Socket接收数据，返回bytes对象
        # BUFFER_SIZE=8192：单次最多读取8KB，通常足够接收完整请求
        # 【注意】HTTP请求通常很小（几KB），不需要循环接收
        raw_data = client_socket.recv(BUFFER_SIZE)
        
        # 【判断客户端是否断开连接】
        # 如果recv()返回空bytes，说明客户端已经关闭了连接
        # 这在客户端发送请求后立即断开时会发生
        if not raw_data:
            response = build_error_response(400)  # 返回400 Bad Request
            client_socket.sendall(response)
            return
        
        # ==================== 核心处理流程 ====================
        
        # 【步骤1】解析HTTP请求
        # 调用http_parser模块的parse_request函数
        # 解析结果：HTTPRequest对象，包含method、path、version字段
        # 例如：raw_data = b"GET /index.html HTTP/1.1\r\n..."
        #       → request.method = "GET", request.path = "/index.html"
        request = parse_request(raw_data)
        
        # 【步骤2】验证请求方法
        # 本服务器是静态文件服务器，只支持GET方法
        # POST/PUT/DELETE等方法返回405 Method Not Allowed
        if request.method != 'GET':
            response = build_error_response(405)  # 返回405错误
            client_socket.sendall(response)
            status_code = 405
            status_phrase = "Method Not Allowed"
            response_bytes = len(response)
            return
        
        # 【步骤3】路径安全检查
        # 这是最重要的安全检查！防止路径穿越攻击
        # 
        # 【什么是路径穿越攻击？】
        # 恶意用户构造特殊的URL，尝试访问Web目录之外的文件：
        # - /../../etc/passwd → 尝试读取Linux密码文件
        # - /..\..\windows\system32\cmd.exe → 尝试执行Windows命令
        #
        # 【我们的防御措施】
        # 1. 规范化路径：处理..和.等特殊路径
        # 2. 真实路径解析：处理符号链接等
        # 3. 边界检查：确保最终路径在www/目录内
        #
        # 返回值：file_path（绝对路径），is_safe（是否安全）
        file_path, is_safe = resolve_path(request.path)
        
        # 如果路径不安全，拒绝访问
        if not is_safe or file_path is None:
            response = build_error_response(403)  # 返回403 Forbidden
            client_socket.sendall(response)
            status_code = 403
            status_phrase = "Forbidden"
            response_bytes = len(response)
            return
        
        # 【步骤4】读取文件内容
        # 根据file_path读取文件，返回：
        # - success: bool，文件是否存在且可读
        # - content: bytes，文件内容（二进制格式）
        # - mime_type: str，如'text/html'、'image/png'等
        success, content, mime_type = read_file(file_path)
        
        # 【步骤5】构建并发送HTTP响应
        if success and content is not None:
            # 文件存在，返回200 OK + 文件内容
            response = build_response(200, mime_type, content)
            client_socket.sendall(response)
            status_code = 200
            status_phrase = "OK"
            response_bytes = len(response)
        else:
            # 文件不存在，返回404 Not Found
            response = build_error_response(404)
            client_socket.sendall(response)
            status_code = 404
            status_phrase = "Not Found"
            response_bytes = len(response)
    
    except socket.timeout:
        # 【超时处理】
        # 客户端30秒内没有发送完整请求
        response = build_error_response(408)
        client_socket.sendall(response)
        status_code = 408
        status_phrase = "Request Timeout"
        response_bytes = len(response)
    except Exception as e:
        # 【异常处理】
        # 捕获所有未预期的异常，避免服务器崩溃
        # 返回500 Internal Server Error
        response = build_error_response(500)
        client_socket.sendall(response)
        status_code = 500
        status_phrase = "Internal Server Error"
        response_bytes = len(response)
    finally:
        # 【清理工作】
        # 无论成功还是失败，都要执行以下操作：
        
        # 1. 打印访问日志
        # 格式：[Thread-ID] GET /path → 状态码 状态短语 (字节数)
        # 示例：[Thread-1234] GET /index.html → 200 OK (1234 bytes)
        print(f"[Thread-{thread_id}] GET {request.path if 'request' in dir() else '/'} → {status_code} {status_phrase} ({response_bytes} bytes)")
        
        # 2. 关闭客户端Socket
        # 【为什么用HTTP/1.0短连接？】
        # - 简化实现，不需要管理连接状态
        # - 每个请求单独建立和关闭连接
        # - 适合静态文件服务器，资源占用少
        client_socket.close()


def worker_thread(task_queue):
    """
    工作线程主循环：从任务队列中获取客户端连接并处理
    
    【为什么需要工作线程？】
    如果每个请求都在主线程处理，服务器只能串行响应，无法并发：
    - 客户端A请求大文件 → 客户端B需要等待
    - 一个慢请求阻塞所有请求
    
    【线程池模式】
    预先创建一组工作线程，它们不断从队列获取任务：
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │  主线程     │    │  工作线程1  │    │  工作线程2  │
    │ (Accept)    │──→ │ (处理请求)  │    │ (处理请求)  │
    └─────────────┘    └─────────────┘    └─────────────┘
           ↓                  ↑                  ↑
    ┌─────────────────────────────────────────────┐
    │              任务队列 (Queue)               │
    │    [(socket1, addr1), (socket2, addr2)...]  │
    └─────────────────────────────────────────────┘
    
    【线程间通信】
    - 使用queue.Queue实现线程安全的数据交换
    - 队列满时put()阻塞，队列空时get()阻塞
    - 支持多个生产者（主线程accept）和多个消费者（工作线程）
    
    【为什么需要哨兵任务？】
    向队列发送(None, None)作为关闭信号，通知工作线程退出
    
    参数：
        task_queue: 线程安全的任务队列
                   【类型】queue.Queue
                   【内容】元素为(client_socket, client_address)元组
    """
    # 【主循环】
    # 工作线程持续运行，直到收到shutdown_flag信号
    while not shutdown_flag.is_set():
        try:
            # 【从队列获取任务】
            # get(timeout=1)：阻塞最多1秒，超时抛出queue.Empty
            # 
            # 【为什么设置超时？】
            # - 避免永久阻塞在get()上
            # - 每次超时后检查shutdown_flag，实现优雅退出
            # - 1秒的延迟对于关闭响应来说可接受
            client_socket, client_address = task_queue.get(timeout=1)
            
            # 【哨兵任务检测】
            # 收到(None, None)表示服务器正在关闭
            # 每个工作线程收到一个哨兵后退出
            if client_socket is None and client_address is None:
                break
            
            # 【处理客户端请求】
            # 这是核心操作：调用handle_client函数处理请求
            handle_client(client_socket, client_address)
            
            # 【标记任务完成】
            # 更新队列的unfinished_tasks计数器
            # 当计数器归零时，queue.join()才会返回
            task_queue.task_done()
            
        except queue.Empty:
            # 【队列为空】
            # 继续循环检查shutdown_flag
            # 这是正常情况，不需要特殊处理
            continue


def signal_handler(signum, frame):
    """
    SIGINT信号处理器：捕获Ctrl+C信号，触发优雅关闭流程
    
    【什么是信号？】
    信号是操作系统发送给进程的通知，用于异步事件：
    - SIGINT (Ctrl+C)：请求中断进程
    - SIGTERM：请求终止进程
    - SIGKILL：强制杀死进程（无法捕获）
    
    【为什么需要优雅关闭？】
    直接kill进程会导致：
    1. 正在处理的请求失败，用户收到错误
    2. 文件操作中断，可能损坏数据
    3. Socket连接未正常关闭，可能出现TIME_WAIT
    
    【优雅关闭流程】
    1. 停止接受新连接
    2. 等待已连接的请求处理完成
    3. 关闭所有Socket连接
    4. 退出所有线程
    5. 释放资源
    
    参数：
        signum: 信号编号
                【常见值】signal.SIGINT=2 (Ctrl+C)
        frame: 当前栈帧对象（未使用，仅保持函数签名兼容）
    """
    print("\n收到关闭信号，正在优雅关闭服务器...")
    
    # 【设置关闭标志】
    # 通知所有工作线程和主循环停止接受新任务
    shutdown_flag.set()
    
    # 【关闭服务器Socket】
    # 关闭后，server_socket.accept()会立即抛出OSError
    # 从而使主线程的accept循环退出
    if server_socket:
        try:
            server_socket.close()
        except Exception:
            pass


def main():
    """
    主函数：Web服务器的完整生命周期
    
    【程序入口】
    当直接运行 main.py 时（而非被导入时），执行此函数
    
    【服务器启动流程】
    ┌─────────────────────────────────────────┐
    │  1. 初始化阶段                          │
    │     - 注册信号处理器                    │
    │     - 创建任务队列                      │
    │     - 创建Server Socket                │
    │     - 绑定地址和端口                    │
    └─────────────────────────────────────────┘
                      ↓
    ┌─────────────────────────────────────────┐
    │  2. 启动阶段                            │
    │     - 创建工作线程池                    │
    │     - 线程进入主循环                    │
    └─────────────────────────────────────────┘
                      ↓
    ┌─────────────────────────────────────────┐
    │  3. 运行阶段（主循环）                   │
    │     - 接受客户端连接                    │
    │     - 将连接放入任务队列                │
    │     - 循环直到收到关闭信号              │
    └─────────────────────────────────────────┘
                      ↓
    ┌─────────────────────────────────────────┐
    │  4. 关闭阶段                            │
    │     - 发送哨兵任务                      │
    │     - 等待线程退出                      │
    │     - 清理资源                          │
    └─────────────────────────────────────────┘
    
    【Socket编程基础】
    创建TCP服务器的步骤：
    1. socket()：创建Socket对象
    2. setsockopt()：设置Socket选项（如端口复用）
    3. bind()：绑定地址和端口
    4. listen()：开始监听连接
    5. accept()：接受客户端连接（循环）
    6. recv()/send()：与客户端通信
    7. close()：关闭连接
    """
    # 【声明全局变量】
    # signal_handler需要访问server_socket来关闭它
    global server_socket
    
    # ==================== 初始化阶段 ====================
    
    # 【注册信号处理器】
    # 捕获SIGINT（Ctrl+C），调用signal_handler函数
    # 这样用户按Ctrl+C时不会强制退出，而是优雅关闭
    signal.signal(signal.SIGINT, signal_handler)
    
    # 【创建任务队列】
    # Queue是线程安全的数据结构，用于生产者-消费者模式
    # 主线程（生产者）放入连接，工作线程（消费者）取出处理
    # maxsize=QUEUE_SIZE：限制队列长度，防止内存溢出
    task_queue = queue.Queue(QUEUE_SIZE)
    
    # ==================== 创建Server Socket ====================
    
    # 【创建TCP Socket】
    # socket.AF_INET：使用IPv4协议族（地址格式：IP:Port）
    # socket.SOCK_STREAM：使用TCP协议（面向连接、可靠）
    # 
    # 【对比SOCK_DGRAM (UDP)】
    # - UDP：无连接、不可靠、效率高（用于DNS、视频流）
    # - TCP：有连接、可靠、有序（用于HTTP、邮件、文件传输）
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 【设置Socket选项】
    # SO_REUSEADDR：允许重用本地地址
    # 
    # 【为什么需要这个选项？】
    # 正常情况下，Socket关闭后会有2-4分钟的TIME_WAIT状态
    # 这期间无法绑定相同端口
    # 设置SO_REUSEADDR后，可以立即重启服务器
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # 【绑定地址和端口】
    # HOST = '0.0.0.0'：监听所有网络接口（有线、无线、localhost）
    # PORT = 8080：监听8080端口
    # 
    # 【常见的端口号】
    # - 80：HTTP标准端口
    # - 443：HTTPS标准端口
    # - 22：SSH远程登录
    # - 3306：MySQL数据库
    # - 8080：常用开发测试端口
    try:
        server_socket.bind((HOST, PORT))
    except Exception as e:
        # 绑定失败（如端口被占用），打印错误并退出
        print(f"绑定端口失败: {e}")
        sys.exit(1)
    
    # 【开始监听】
    # listen(BACKLOG)：开始监听连接，BACKLOG是全连接队列大小
    # 
    # 【TCP三次握手过程】
    # 1. 客户端发送SYN → 服务器
    # 2. 服务器返回SYN-ACK
    # 3. 客户端发送ACK
    # 三次握手完成后，连接进入"全连接队列"
    # accept()从全连接队列取出连接进行处理
    server_socket.listen(BACKLOG)
    
    # 【设置accept超时】
    # 超时1秒，使主循环能定期检查shutdown_flag
    # 如果设为None，主循环会永远阻塞在accept()
    server_socket.settimeout(1.0)
    
    # ==================== 确定文档根目录 ====================
    
    # 【计算www目录的绝对路径】
    # __file__：当前脚本的路径（D:\...\webserver\src\main.py）
    # dirname()：获取目录部分（D:\...\webserver\src）
    # join('..', 'www')：上一级目录下的www
    # abspath()：转换为绝对路径
    #
    # 最终结果：D:\develop\homework\webserver\www
    doc_root = os.path.join(os.path.dirname(__file__), '..', 'www')
    doc_root = os.path.abspath(doc_root)
    
    # 【打印启动信息】
    print(f"服务器已启动，监听 http://{HOST}:{PORT}")
    print(f"文档根目录: {doc_root}")
    print(f"工作线程数: {THREAD_POOL_SIZE}")
    print("按 Ctrl+C 停止服务器")
    
    # ==================== 启动工作线程池 ====================
    
    # 【创建工作线程】
    # 创建THREAD_POOL_SIZE个线程，每个运行worker_thread函数
    # daemon=True：设为守护线程，随主线程一起退出
    # 
    # 【守护线程 vs 用户线程】
    # - 守护线程：主线程退出时自动终止（如日志写入线程）
    # - 用户线程：必须正常结束才能退出（如数据保存线程）
    threads = []
    for _ in range(THREAD_POOL_SIZE):
        t = threading.Thread(target=worker_thread, args=(task_queue,))
        t.daemon = True  # 守护线程：主线程退出时自动终止
        t.start()        # 启动线程，开始执行worker_thread函数
        threads.append(t)
    
    # ==================== 主循环：接受客户端连接 ====================
    
    # 【循环接受连接】
    # 持续运行，直到shutdown_flag被设置
    while not shutdown_flag.is_set():
        try:
            # 【接受客户端连接】
            # 阻塞等待，直到有新连接或超时
            # 返回值：
            # - client_socket：与客户端通信的Socket对象
            # - client_address：客户端地址元组
            client_socket, client_address = server_socket.accept()
            
            # 【将连接放入任务队列】
            # put((socket, address), block=False)：
            # - 如果队列满，立即抛出queue.Full
            # - 与block=True的区别：是否阻塞等待队列空闲
            try:
                task_queue.put((client_socket, client_address), block=False)
            except queue.Full:
                # 【队列已满】
                # 说明服务器负载过高，无法处理更多请求
                # 关闭新连接，返回错误日志
                client_socket.close()
                print(f"请求队列已满，拒绝连接: {client_address}")
        
        except socket.timeout:
            # 【accept超时】
            # 1秒超时后继续循环，检查shutdown_flag
            continue
        except OSError:
            # 【Socket已关闭】
            # signal_handler中关闭了server_socket
            # 退出循环，进入关闭流程
            break
    
    # ==================== 优雅关闭 ====================
    
    print("等待工作线程完成...")
    
    # 【发送哨兵任务】
    # 向队列发送THREAD_POOL_SIZE个(None, None)
    # 每个工作线程收到一个哨兵后退出
    for _ in range(THREAD_POOL_SIZE):
        task_queue.put((None, None))
    
    # 【等待线程退出】
    # join(timeout=5)：最多等待5秒让线程结束
    # 超过5秒未结束的线程会被强制终止
    for t in threads:
        t.join(timeout=5)
    
    print("服务器已关闭")


if __name__ == '__main__':
    # 【程序入口】
    # __name__ == '__main__' 确保只有直接运行此文件时才执行
    # 如果是作为模块导入（如 from src import main），不会执行
    main()
