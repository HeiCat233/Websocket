"""
================================================================================
中间件模块
================================================================================

【模块功能】
提供请求处理的中间件机制，支持请求/响应的预处理和后处理。

【中间件概念】
中间件是一种拦截器模式，可以在请求处理流程中插入自定义逻辑：
- 请求前处理：验证、日志、认证
- 请求后处理：响应修改、日志记录

【中间件链】
请求经过多个中间件的处理，形成一个处理链：
Request → Middleware1 → Middleware2 → Handler → Response → Middleware2 → Middleware1

【设计原则】
- 单一职责：每个中间件只做一件事
- 顺序执行：按注册顺序执行
- 快速失败：验证失败时提前返回

================================================================================
"""

from typing import Callable, List, Optional, Tuple
from .request import HTTPRequest
from .response import HTTPResponse


# 中间件类型定义
Middleware = Callable[[HTTPRequest], Tuple[bool, Optional[HTTPResponse]]]


class MiddlewareChain:
    """
    中间件链管理器
    
    【职责】
    管理中间件的执行顺序和调用流程。
    
    【使用方式】
    ```python
    chain = MiddlewareChain()
    chain.use(logging_middleware)
    chain.use(auth_middleware)
    chain.use(rate_limit_middleware)
    
    # 执行链
    result = chain.execute(request)
    ```
    """
    
    def __init__(self):
        """
        初始化中间件链
        """
        self.middlewares: List[Middleware] = []
    
    def use(self, middleware: Middleware) -> None:
        """
        注册中间件
        
        参数：
            middleware: 中间件函数
        """
        self.middlewares.append(middleware)
    
    def execute(self, request: HTTPRequest) -> Tuple[bool, Optional[HTTPResponse]]:
        """
        执行中间件链
        
        参数：
            request: HTTP请求对象
        
        返回：
            元组 (should_continue, response)
            - should_continue: 是否继续处理
            - response: 如果返回了响应（短路响应）
        """
        for middleware in self.middlewares:
            should_continue, response = middleware(request)
            if not should_continue:
                return (False, response)
        return (True, None)


# ==================== 常用中间件 ====================

def logging_middleware(request: HTTPRequest) -> Tuple[bool, None]:
    """
    日志记录中间件
    
    记录请求的方法和路径。
    
    参数：
        request: HTTP请求对象
    
    返回：
        元组 (should_continue, response)
    """
    print(f"[Middleware] Processing: {request.method} {request.path}")
    return (True, None)


def method_validator_middleware(request: HTTPRequest) -> Tuple[bool, Optional[HTTPResponse]]:
    """
    方法验证中间件
    
    验证请求方法是否为GET。
    
    参数：
        request: HTTP请求对象
    
    返回：
        元组 (should_continue, response)
        - 如果方法不允许，返回(False, 405响应)
    """
    from .response import build_error_response
    
    if request.method != 'GET':
        error_response = build_error_response(405)
        return (False, error_response)
    
    return (True, None)


class RequestLogger:
    """
    请求日志记录器
    
    【职责】
    记录每个请求的处理结果。
    可以集成到中间件链中使用。
    """
    
    def __init__(self):
        """
        初始化日志记录器
        """
        self.requests = []
    
    def log(self, request: HTTPRequest, status_code: int, response_size: int) -> None:
        """
        记录请求处理结果
        
        参数：
            request: HTTP请求对象
            status_code: HTTP状态码
            response_size: 响应大小（字节）
        """
        log_entry = {
            'method': request.method,
            'path': request.path,
            'status_code': status_code,
            'size': response_size
        }
        self.requests.append(log_entry)
    
    def get_logs(self) -> List[dict]:
        """
        获取所有日志记录
        
        返回：
            日志列表
        """
        return self.requests.copy()
    
    def clear(self) -> None:
        """
        清空日志
        """
        self.requests.clear()


# 全局日志记录器实例
request_logger = RequestLogger()
