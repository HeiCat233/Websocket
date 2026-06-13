"""
================================================================================
应用核心模块
================================================================================

【模块说明】
实现Web服务器的核心功能，包括Socket通信和多线程处理。

【架构设计】
采用生产者-消费者模式：
- 主线程：接收连接，生产任务
- 工作线程：处理请求，消费任务

【模块依赖】
- config: 配置管理
- routes: 路由管理
- controllers: 控制器
- services: 服务层

================================================================================
"""

import socket
import threading
import queue
import signal
import sys

from config import settings
from routes import router
from services import parse_request, RequestValidator
from services.response_service import build_error_response
from controllers.error_controller import ErrorController


class ClientHandler:
    """
    客户端处理器
    
    【职责】
    处理单个客户端的HTTP请求。
    
    【处理流程】
    1. 接收请求数据
    2. 解析请求
    3. 验证请求
    4. 路由分发
    5. 发送响应
    6. 关闭连接
    """
    
    def __init__(self):
        self.error_controller = ErrorController()
    
    def handle(self, client_socket, client_address):
        """
        处理客户端请求
        
        参数：
            client_socket: 客户端Socket对象
            client_address: 客户端地址元组
        """
        thread_id = threading.current_thread().ident
        status_code = 500
        response_bytes = 0
        request = None
        
        try:
            # 设置超时
            client_socket.settimeout(settings.CLIENT_TIMEOUT)
            
            # 接收请求数据
            raw_data = client_socket.recv(settings.BUFFER_SIZE)
            
            # 解析请求
            request = parse_request(raw_data)
            
            # 验证请求方法
            is_valid, error_msg = RequestValidator.validate_method(request)
            if not is_valid:
                response = build_error_response(405)
                response_bytes = client_socket.sendall(response)
                status_code = 405
            else:
                # 路由处理
                response_data, status_code = router.handle(raw_data)
                response_bytes = client_socket.sendall(response_data)
        
        except socket.timeout:
            status_code = 408
            response = self.error_controller.handle_408()
            try:
                client_socket.sendall(response)
            except:
                pass
        
        except Exception as e:
            status_code = 500
            response = self.error_controller.handle_500()
            try:
                client_socket.sendall(response)
            except:
                pass
        
        finally:
            # 记录日志
            path = request.path if request and request.path else 'unknown'
            print(f"[Thread-{thread_id}] GET {path} → {status_code} ({response_bytes} bytes)")
            
            # 关闭连接
            try:
                client_socket.close()
            except:
                pass


class WorkerThread(threading.Thread):
    """
    工作线程
    
    【职责】
    从任务队列获取任务并处理。
    
    【工作流程】
    1. 从队列获取任务（阻塞）
    2. 检查关闭标记
    3. 处理客户端请求
    4. 循环
    """
    
    def __init__(self, task_queue, shutdown_flag):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.shutdown_flag = shutdown_flag
        self.client_handler = ClientHandler()
    
    def run(self):
        """线程主循环"""
        while True:
            try:
                # 带超时的队列获取
                client_socket, client_address = self.task_queue.get(
                    timeout=settings.QUEUE_GET_TIMEOUT
                )
                
                # 检查关闭标记
                if client_socket is None:
                    break
                
                # 处理请求
                self.client_handler.handle(client_socket, client_address)
            
            except queue.Empty:
                # 超时，继续循环
                continue
            except Exception as e:
                print(f"[Worker] Error: {e}")
                continue


class WebServer:
    """
    Web服务器主类
    
    【职责】
    整合所有组件，提供完整的Web服务器功能。
    
    【使用方式】
    ```python
    from app import WebServer
    server = WebServer()
    server.start()
    ```
    """
    
    def __init__(self):
        self.host = settings.HOST
        self.port = settings.PORT
        self.server_socket = None
        self.task_queue = queue.Queue(settings.QUEUE_SIZE)
        self.shutdown_flag = threading.Event()
        self.workers = []
    
    def _create_socket(self):
        """创建服务器Socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(settings.BACKLOG)
        return sock
    
    def _start_worker_threads(self):
        """启动工作线程池"""
        for i in range(settings.THREAD_POOL_SIZE):
            worker = WorkerThread(self.task_queue, self.shutdown_flag)
            worker.start()
            self.workers.append(worker)
    
    def _shutdown_workers(self):
        """关闭所有工作线程"""
        # 发送关闭信号
        for _ in range(len(self.workers)):
            self.task_queue.put((None, None))
        
        # 等待线程结束
        for worker in self.workers:
            worker.join(timeout=2.0)
    
    def start(self):
        """启动服务器"""
        print(f"服务器已启动，监听 http://{self.host}:{self.port}")
        print(f"文档根目录: {settings.get_document_root()}")
        print(f"工作线程数: {settings.THREAD_POOL_SIZE}")
        print("按 Ctrl+C 停止服务器")
        
        # 创建Socket
        self.server_socket = self._create_socket()
        
        # 启动工作线程
        self._start_worker_threads()
        
        # 主循环
        try:
            while not self.shutdown_flag.is_set():
                try:
                    self.server_socket.settimeout(settings.ACCEPT_TIMEOUT)
                    client_socket, client_address = self.server_socket.accept()
                    self.task_queue.put((client_socket, client_address))
                
                except socket.timeout:
                    continue
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """关闭服务器"""
        print("\n正在关闭服务器...")
        
        self.shutdown_flag.set()
        self._shutdown_workers()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("服务器已关闭")


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到关闭信号，正在关闭服务器...")


def setup_signal_handler():
    """设置信号处理器"""
    if sys.platform != 'win32':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        signal.signal(signal.SIGINT, signal_handler)


def create_app():
    """
    创建应用实例
    
    返回：
        配置好的Web服务器实例
    """
    setup_signal_handler()
    return WebServer()
