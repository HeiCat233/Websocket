"""
================================================================================
路由处理模块
================================================================================

【模块功能】
管理请求路由，将URL路径映射到对应的处理函数。

【路由概念】
路由是URL路径和处理函数之间的映射关系：
- / → index_handler
- /about → about_handler
- /article/:id → article_handler

【路由匹配】
支持静态路由和动态路由：
- 静态路由：精确匹配 /about
- 动态路由：模式匹配 /article/:id

【设计原则】
- RESTful风格：遵循REST设计原则
- 清晰映射：URL语义明确
- 可扩展：支持自定义处理函数

================================================================================
"""

from typing import Callable, Dict, Optional, Tuple
from .request import HTTPRequest
from .response import HTTPResponse, build_response, build_error_response
from .storage import FileHandler
from .config import config


# 路由处理函数类型
RouteHandler = Callable[[HTTPRequest], HTTPResponse]


class Route:
    """
    路由类
    
    【属性】
        path: URL路径
        handler: 处理函数
        name: 路由名称（可选）
    """
    
    def __init__(
        self,
        path: str,
        handler: RouteHandler,
        name: Optional[str] = None
    ):
        self.path = path
        self.handler = handler
        self.name = name or path


class StaticFileHandler:
    """
    静态文件处理器
    
    【职责】
    处理静态文件的请求。
    
    【处理流程】
    1. 解析文件路径
    2. 检查路径安全性
    3. 读取文件内容
    4. 返回响应
    """
    
    def __init__(self):
        """
        初始化静态文件处理器
        """
        self.file_handler = FileHandler()
    
    def handle(self, request: HTTPRequest) -> Tuple[bytes, int]:
        """
        处理静态文件请求
        
        参数：
            request: HTTP请求对象
        
        返回：
            元组 (response_bytes, status_code)
        """
        # 获取请求路径
        url_path = request.get_path_without_query()
        
        # 读取文件
        success, content, mime_type, status_code = self.file_handler.read(url_path)
        
        # 构建响应
        if success:
            response = build_response(200, mime_type, content)
            return (response, 200)
        else:
            # 返回错误响应
            error_response = build_error_response(status_code)
            return (error_response, status_code)


class Router:
    """
    路由管理器
    
    【职责】
    管理所有路由，处理请求的分发。
    
    【路由注册】
    支持静态路由和动态路由：
    - add_route('/', index_handler)
    - add_route('/about', about_handler)
    
    【默认处理】
    如果没有匹配的路由，使用静态文件处理器。
    """
    
    def __init__(self):
        """
        初始化路由管理器
        """
        self.routes: Dict[str, Route] = {}
        self.static_handler = StaticFileHandler()
    
    def add_route(
        self,
        path: str,
        handler: RouteHandler,
        name: Optional[str] = None
    ) -> None:
        """
        注册路由
        
        参数：
            path: URL路径
            handler: 处理函数
            name: 路由名称（可选）
        """
        route = Route(path, handler, name)
        self.routes[path] = route
    
    def route(self, path: str) -> Callable:
        """
        路由装饰器
        
        【使用方式】
        ```python
        @router.route('/about')
        def about_page(request):
            return HTTPResponse(...)
        ```
        
        参数：
            path: URL路径
        
        返回：
            装饰器函数
        """
        def decorator(func: RouteHandler) -> RouteHandler:
            self.add_route(path, func, func.__name__)
            return func
        return decorator
    
    def get_handler(self, path: str) -> Optional[RouteHandler]:
        """
        获取路由处理函数
        
        参数：
            path: URL路径
        
        返回：
            处理函数，如果未找到则返回None
        """
        route = self.routes.get(path)
        return route.handler if route else None
    
    def handle(self, request: HTTPRequest) -> Tuple[bytes, int]:
        """
        处理请求
        
        参数：
            request: HTTP请求对象
        
        返回：
            元组 (response_bytes, status_code)
        """
        url_path = request.get_path_without_query()
        
        # 查找自定义路由
        handler = self.get_handler(url_path)
        
        if handler:
            try:
                # 调用处理函数
                response_obj = handler(request)
                if isinstance(response_obj, HTTPResponse):
                    return (response_obj.to_bytes(), 200)
                elif isinstance(response_obj, bytes):
                    return (response_obj, 200)
            except Exception as e:
                # 处理函数出错
                error_response = build_error_response(500)
                return (error_response, 500)
        
        # 使用静态文件处理器
        return self.static_handler.handle(request)
    
    def list_routes(self) -> Dict[str, str]:
        """
        列出所有注册的路由
        
        返回：
            字典 {path: handler_name}
        """
        return {
            path: route.name or route.handler.__name__
            for path, route in self.routes.items()
        }


# ==================== 默认路由处理函数 ====================

def default_index_handler(request: HTTPRequest) -> bytes:
    """
    默认首页处理器
    """
    from .storage import FileHandler
    
    file_handler = FileHandler()
    success, content, mime_type, status_code = file_handler.read('/index.html')
    
    if success:
        return build_response(200, mime_type, content)
    else:
        return build_error_response(404)


def create_about_handler(content: bytes, mime_type: str) -> RouteHandler:
    """
    创建关于页面处理器（工厂函数）
    
    参数：
        content: 页面内容
        mime_type: MIME类型
    
    返回：
        处理函数
    """
    def handler(request: HTTPRequest) -> bytes:
        return build_response(200, mime_type, content)
    return handler


# 全局路由实例
router = Router()
