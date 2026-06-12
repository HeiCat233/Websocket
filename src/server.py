"""
================================================================================
服务器核心模块
================================================================================

【模块功能】
实现Web服务器的核心功能，包括Socket通信、多线程处理、请求分发等。

【模块职责】
1. 创建和管理TCP Socket
2. 接收客户端连接
3. 分发请求到工作线程
4. 管理线程池
5. 处理优雅关闭

【架构设计】
采用生产者-消费者模式：
- 主线程：接收连接，生产任务
- 工作线程：处理请求，消费任务

【线程安全】
- 全局shutdown_flag：协调关闭
- 队列操作：线程安全

================================================================================
"""

import socket
import threading
import queue
import signal
import sys
from typing import Optional

from .config import config
from .request import parse_request
from .middleware import (
    MiddlewareChain,
    method_validator_middleware,
    request_logger
)
from .router import router


class ClientHandler:
    """
    客户端处理器
    
    【职责】
    处理单个客户端的HTTP请求。
    
    【处理流程】
    1. 接收请求数据
    2. 解析请求
    3. 通过中间件链
    4. 路由分发
    5. 发送响应
    6. 关闭连接
    """
    
    def __init__(self):
        """
        初始化客户端处理器
        """
        # 创建中间件链
        self.middleware_chain = MiddlewareChain()
        self.middleware_chain.use(method_validator_middleware)
    
    def handle(
        self,
        client_socket: socket.socket,
        client_address: tuple
    ) -> None:
        """
        处理客户端请求
        
        参数：
            client_socket: 客户端Socket对象
            client_address: 客户端地址元组 (host, port)
        """
        thread_id = threading.current_thread().ident
        status_code = 500
        response_bytes = 0
        
        try:
            # 设置超时
            client_socket.settimeout(config.CLIENT_TIMEOUT)
            
            # 接收请求数据
            raw_data = client_socket.recv(config.BUFFER_SIZE)
            
            # 解析请求
            request = parse_request(raw_data)
            
            # 通过中间件链
            should_continue, shortcircuit_response = self.middleware_chain.execute(request)
            
            if not should_continue:
                # 短路响应（验证失败等）
                response_bytes = client_socket.sendall(shortcircuit_response)
                status_code = 405
            else:
                # 路由处理
                response_data, status_code = router.handle(request)
                response_bytes = client_socket.sendall(response_data)
        
        except socket.timeout:
            # 超时
            status_code = 408
            error_response = self._build_timeout_response()
            try:
                client_socket.sendall(error_response)
            except:
                pass
        
        except Exception as e:
            # 内部错误
            status_code = 500
            error_response = self._build_error_response()
            try:
                client_socket.sendall(error_response)
            except:
                pass
        
        finally:
            # 记录日志
            thread_id = threading.current_thread().ident
            path = request.path if 'request' in locals() else 'unknown'
            print(f"[Thread-{thread_id}] GET {path} → {status_code} ({response_bytes} bytes)")
            
            # 关闭连接
            try:
                client_socket.close()
            except:
                pass
    
    def _build_timeout_response(self) -> bytes:
        """
        构建超时响应
        """
        from .response import build_error_response
        return build_error_response(408)
    
    def _build_error_response(self) -> bytes:
        """
        构建错误响应
        """
        from .response import build_error_response
        return build_error_response(500)


class WorkerThread(threading.Thread):
    """
    工作线程类
    
    【职责】
    从任务队列获取任务并处理。
    
    【工作流程】
    1. 从队列获取任务（阻塞）
    2. 检查关闭标记
    3. 处理客户端请求
    4. 循环
    """
    
    def __init__(self, task_queue: queue.Queue, shutdown_flag: threading.Event):
        """
        初始化工作线程
        
        参数：
            task_queue: 任务队列
            shutdown_flag: 关闭标志
        """
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.shutdown_flag = shutdown_flag
        self.client_handler = ClientHandler()
    
    def run(self) -> None:
        """
        线程主循环
        """
        while True:
            try:
                # 带超时的队列获取，允许定期检查关闭标志
                client_socket, client_address = self.task_queue.get(
                    timeout=config.QUEUE_GET_TIMEOUT
                )
                
                # 检查关闭标记
                if client_socket is None:
                    break
                
                # 处理请求
                self.client_handler.handle(client_socket, client_address)
            
            except queue.Empty:
                # 超时，继续循环检查关闭标志
                continue
            except Exception as e:
                print(f"[Worker] Error: {e}")
                continue


class WebServer:
    """
    Web服务器类
    
    【职责】
    整合所有组件，提供完整的Web服务器功能。
    
    【使用方式】
    ```python
    server = WebServer()
    server.start()
    ```
    """
    
    def __init__(self):
        """
        初始化Web服务器
        """
        self.host = config.HOST
        self.port = config.PORT
        self.server_socket: Optional[socket.socket] = None
        self.task_queue = queue.Queue(config.QUEUE_SIZE)
        self.shutdown_flag = threading.Event()
        self.workers: list = []
    
    def _create_socket(self) -> socket.socket:
        """
        创建服务器Socket
        
        返回：
            配置好的Socket对象
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(config.BACKLOG)
        return sock
    
    def _start_worker_threads(self) -> None:
        """
        启动工作线程池
        """
        for i in range(config.THREAD_POOL_SIZE):
            worker = WorkerThread(self.task_queue, self.shutdown_flag)
            worker.start()
            self.workers.append(worker)
    
    def _shutdown_workers(self) -> None:
        """
        关闭所有工作线程
        """
        # 发送关闭信号
        for _ in range(len(self.workers)):
            self.task_queue.put((None, None))
        
        # 等待线程结束
        for worker in self.workers:
            worker.join(timeout=2.0)
    
    def start(self) -> None:
        """
        启动服务器
        """
        print(f"服务器已启动，监听 http://{self.host}:{self.port}")
        print(f"文档根目录: {config.get_document_root()}")
        print(f"工作线程数: {config.THREAD_POOL_SIZE}")
        print("按 Ctrl+C 停止服务器")
        
        # 创建Socket
        self.server_socket = self._create_socket()
        
        # 启动工作线程
        self._start_worker_threads()
        
        # 主循环：接收连接
        try:
            while not self.shutdown_flag.is_set():
                try:
                    # 设置accept超时，用于定期检查关闭标志
                    self.server_socket.settimeout(config.ACCEPT_TIMEOUT)
                    client_socket, client_address = self.server_socket.accept()
                    
                    # 添加到任务队列
                    self.task_queue.put((client_socket, client_address))
                
                except socket.timeout:
                    # accept超时，继续循环检查关闭标志
                    continue
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """
        关闭服务器
        """
        print("\n正在关闭服务器...")
        
        # 设置关闭标志
        self.shutdown_flag.set()
        
        # 关闭工作线程
        self._shutdown_workers()
        
        # 关闭服务器Socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("服务器已关闭")


def signal_handler(signum, frame) -> None:
    """
    信号处理器
    
    捕获SIGINT（Ctrl+C），触发优雅关闭。
    
    参数：
        signum: 信号编号
        frame: 当前堆栈帧
    """
    print("\n收到关闭信号，正在关闭服务器...")
    # 服务器的主循环会检测shutdown_flag并退出


def setup_signal_handler(server: WebServer) -> None:
    """
    设置信号处理器
    
    参数：
        server: Web服务器实例
    """
    if sys.platform != 'win32':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        # Windows不支持SIGTERM
        signal.signal(signal.SIGINT, signal_handler)


def create_server() -> WebServer:
    """
    创建并配置Web服务器
    
    返回：
        配置好的Web服务器实例
    """
    server = WebServer()
    setup_signal_handler(server)
    return server
