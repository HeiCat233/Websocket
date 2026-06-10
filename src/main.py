# ============================================================================
# 主程序模块：Web服务器核心
# 功能：整合所有模块，实现Socket通信、多线程并发和请求路由
# ============================================================================

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
HOST = '0.0.0.0'           # 监听地址：'0.0.0.0'表示接受所有网络接口的连接
PORT = 8080                # 监听端口号：客户端通过此端口访问服务器
BACKLOG = 10               # TCP连接队列最大长度：等待处理的连接数上限
THREAD_POOL_SIZE = 4       # 工作线程数量：同时处理4个客户端请求
QUEUE_SIZE = 128           # 任务队列容量：最多缓存128个待处理请求
BUFFER_SIZE = 8192         # 接收缓冲区大小：单次recv()最多读取8KB数据

# 全局变量：用于优雅关闭机制
shutdown_flag = threading.Event()  # 线程间通信标志，触发服务器关闭
server_socket = None               # 服务器Socket对象，供信号处理器访问


def handle_client(client_socket, client_address):
    """
    处理单个客户端的完整请求流程
    
    工作流程：
    1. 接收HTTP请求数据
    2. 解析请求行（方法、路径、版本）
    3. 验证请求方法（仅支持GET）
    4. 安全检查URL路径（防止路径穿越攻击）
    5. 读取请求的文件内容
    6. 构建并发送HTTP响应
    7. 记录访问日志
    
    参数：
        client_socket: 客户端Socket连接对象
        client_address: 客户端地址元组 (ip, port)
    """
    thread_id = threading.current_thread().ident  # 获取当前工作线程ID，用于日志追踪
    status_code = 500              # 默认状态码：内部服务器错误
    status_phrase = "Internal Server Error"  # 默认状态描述
    response_bytes = 0             # 响应数据字节数，用于日志记录
    
    try:
        # 设置30秒超时，防止客户端连接长时间无数据导致资源占用
        client_socket.settimeout(30.0)
        
        # 从Socket接收原始HTTP请求数据（二进制格式）
        raw_data = client_socket.recv(BUFFER_SIZE)
        
        # 如果接收到空数据，说明客户端已断开连接
        if not raw_data:
            response = build_error_response(400)  # 返回400 Bad Request
            client_socket.sendall(response)
            return
        
        # 【步骤1】解析HTTP请求：提取方法(GET)、路径(/index.html)、版本(HTTP/1.0)
        request = parse_request(raw_data)
        
        # 【步骤2】验证请求方法：本服务器仅支持GET请求（静态文件服务）
        if request.method != 'GET':
            response = build_error_response(405)  # 返回405 Method Not Allowed
            client_socket.sendall(response)
            status_code = 405
            status_phrase = "Method Not Allowed"
            response_bytes = len(response)
            return
        
        # 【步骤3】路径安全检查：将URL路径映射为文件系统绝对路径
        # 例如：/article/post1.html → D:\develop\homework\webserver\www\article\post1.html
        file_path, is_safe = resolve_path(request.path)
        
        # 如果路径不安全（如尝试访问../../etc/passwd），拒绝请求
        if not is_safe or file_path is None:
            response = build_error_response(403)  # 返回403 Forbidden
            client_socket.sendall(response)
            status_code = 403
            status_phrase = "Forbidden"
            response_bytes = len(response)
            return
        
        # 【步骤4】读取文件内容：根据文件扩展名自动识别MIME类型
        # 返回值：(成功标志, 文件内容bytes, MIME类型如'text/html')
        success, content, mime_type = read_file(file_path)
        
        # 【步骤5】构建并发送HTTP响应
        if success and content is not None:
            # 文件存在：返回200 OK + 文件内容
            response = build_response(200, mime_type, content)
            client_socket.sendall(response)
            status_code = 200
            status_phrase = "OK"
            response_bytes = len(response)
        else:
            # 文件不存在：返回404 Not Found错误页面
            response = build_error_response(404)
            client_socket.sendall(response)
            status_code = 404
            status_phrase = "Not Found"
            response_bytes = len(response)
    
    except socket.timeout:
        # 客户端30秒内未发送数据，返回408 Request Timeout
        response = build_error_response(408)
        client_socket.sendall(response)
        status_code = 408
        status_phrase = "Request Timeout"
        response_bytes = len(response)
    except Exception as e:
        # 捕获所有未预期的异常，返回500 Internal Server Error
        response = build_error_response(500)
        client_socket.sendall(response)
        status_code = 500
        status_phrase = "Internal Server Error"
        response_bytes = len(response)
    finally:
        # 无论成功或失败，都执行以下操作：
        # 1. 打印访问日志（线程ID、请求路径、状态码、响应大小）
        # 2. 关闭客户端Socket连接（HTTP/1.0短连接特性）
        print(f"[Thread-{thread_id}] GET {request.path if 'request' in dir() else '/'} → {status_code} {status_phrase} ({response_bytes} bytes)")
        client_socket.close()


def worker_thread(task_queue):
    """
    工作线程主循环：从任务队列中获取客户端连接并处理
    
    工作机制：
    - 每个工作线程持续运行，直到收到关闭信号
    - 从队列中阻塞式获取任务（超时1秒避免永久阻塞）
    - 收到(None, None)哨兵任务时退出线程
    
    参数：
        task_queue: 线程安全的任务队列，存放待处理的(client_socket, client_address)
    """
    while not shutdown_flag.is_set():  # 检查是否收到关闭信号
        try:
            # 从队列获取任务，超时1秒后抛出queue.Empty异常
            # 这样可以定期检查shutdown_flag，实现优雅关闭
            client_socket, client_address = task_queue.get(timeout=1)
            
            # 哨兵任务检测：收到(None, None)表示服务器正在关闭
            if client_socket is None and client_address is None:
                break
            
            # 调用handle_client处理客户端请求
            handle_client(client_socket, client_address)
            task_queue.task_done()  # 标记任务完成，更新队列计数器
        except queue.Empty:
            # 队列为空，继续循环检查关闭信号
            continue


def signal_handler(signum, frame):
    """
    SIGINT信号处理器：捕获Ctrl+C信号，触发优雅关闭流程
    
    优雅关闭的含义：
    - 不再接受新连接
    - 等待已连接的客户端处理完成
    - 等待工作线程正常退出
    - 避免强制终止导致的数据丢失或资源泄漏
    
    参数：
        signum: 信号编号（signal.SIGINT）
        frame: 当前栈帧（未使用）
    """
    print("\n收到关闭信号，正在优雅关闭服务器...")
    shutdown_flag.set()  # 设置关闭标志，通知所有工作线程停止
    
    # 关闭服务器Socket，使accept()立即返回OSError异常
    if server_socket:
        try:
            server_socket.close()
        except Exception:
            pass


def main():
    """
    主函数：Web服务器的完整生命周期
    
    启动流程：
    1. 注册信号处理器
    2. 创建任务队列
    3. 创建并绑定Server Socket
    4. 启动工作线程池
    5. 进入Accept循环，接受客户端连接
    6. 收到关闭信号后，优雅关闭所有资源
    """
    global server_socket  # 声明为全局变量，供信号处理器访问
    
    # 【初始化阶段】注册SIGINT信号处理器（Ctrl+C）
    signal.signal(signal.SIGINT, signal_handler)
    
    # 创建线程安全的任务队列，最大容量QUEUE_SIZE=128
    task_queue = queue.Queue(QUEUE_SIZE)
    
    # 【创建Server Socket】
    # AF_INET: 使用IPv4协议族
    # SOCK_STREAM: 使用TCP协议（可靠、面向连接）
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 设置SO_REUSEADDR选项：允许重启服务器时立即绑定相同端口
    # 否则会出现"Address already in use"错误，需要等待2-3分钟
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # 绑定Socket到指定地址和端口
    try:
        server_socket.bind((HOST, PORT))
    except Exception as e:
        print(f"绑定端口失败: {e}")
        sys.exit(1)  # 绑定失败，直接退出程序
    
    # 开始监听：BACKLOG=10表示最多允许10个连接在队列中等待accept()
    server_socket.listen(BACKLOG)
    
    # 设置accept()超时时间为1秒，使其能定期检查shutdown_flag
    server_socket.settimeout(1.0)
    
    # 【确定文档根目录】
    # 计算www/目录的绝对路径，作为Web资源的根目录
    # 例如：D:\develop\homework\webserver\www
    doc_root = os.path.join(os.path.dirname(__file__), '..', 'www')
    doc_root = os.path.abspath(doc_root)
    
    # 打印服务器启动信息
    print(f"服务器已启动，监听 http://{HOST}:{PORT}")
    print(f"文档根目录: {doc_root}")
    print(f"工作线程数: {THREAD_POOL_SIZE}")
    print("按 Ctrl+C 停止服务器")
    
    # 【启动工作线程池】
    # 创建THREAD_POOL_SIZE=4个守护线程，它们会自动从task_queue获取任务
    threads = []
    for _ in range(THREAD_POOL_SIZE):
        t = threading.Thread(target=worker_thread, args=(task_queue,))
        t.daemon = True  # 设置为守护线程：主线程退出时自动终止
        t.start()
        threads.append(t)
    
    # 【主循环：接受客户端连接】
    # 持续接受新连接，直到收到关闭信号
    while not shutdown_flag.is_set():
        try:
            # 阻塞等待客户端连接，超时1秒后继续循环检查shutdown_flag
            client_socket, client_address = server_socket.accept()
            
            # 将新连接放入任务队列，由工作线程处理
            # block=False：如果队列已满，立即抛出queue.Full异常
            try:
                task_queue.put((client_socket, client_address), block=False)
            except queue.Full:
                # 队列已满（128个任务都在等待），拒绝新连接
                client_socket.close()
                print(f"请求队列已满，拒绝连接: {client_address}")
        
        except socket.timeout:
            # accept()超时，继续循环检查shutdown_flag
            continue
        except OSError:
            # 服务器Socket被关闭（signal_handler中执行），退出循环
            break
    
    # 【优雅关闭流程】
    print("等待工作线程完成...")
    
    # 向队列中发送THREAD_POOL_SIZE个哨兵任务(None, None)
    # 每个工作线程收到一个哨兵任务后会退出
    for _ in range(THREAD_POOL_SIZE):
        task_queue.put((None, None))
    
    # 等待所有工作线程正常退出（最多等待5秒）
    for t in threads:
        t.join(timeout=5)
    
    print("服务器已关闭")


if __name__ == '__main__':
    main()