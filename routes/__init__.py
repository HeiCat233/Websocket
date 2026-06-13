"""
================================================================================
路由模块
================================================================================

【模块说明】
管理请求路由，将URL路径映射到对应的控制器。

【路由概念】
路由是URL路径和处理函数之间的映射关系：
- / → StaticFileController
- 其他 → StaticFileController（默认）

【设计原则】
- 简洁：默认所有请求都走静态文件服务
- 可扩展：支持添加自定义路由

================================================================================
"""

from controllers.static_controller import StaticFileController


class Route:
    """
    路由类
    
    【属性】
        path: URL路径
        handler: 处理函数
    """
    
    def __init__(self, path, handler):
        self.path = path
        self.handler = handler


class Router:
    """
    路由管理器
    
    【职责】
    管理路由注册和请求分发。
    
    【处理流程】
    1. 接收HTTP请求数据
    2. 解析请求路径
    3. 查找对应处理器
    4. 返回响应
    """
    
    def __init__(self):
        self.routes = []
        self.static_controller = StaticFileController()
    
    def add_route(self, path, handler):
        """
        注册路由
        
        参数：
            path: URL路径
            handler: 处理函数
        """
        route = Route(path, handler)
        self.routes.append(route)
    
    def route(self, path):
        """
        路由装饰器
        
        用法：
            @router.route('/api/data')
            def data_handler(request):
                return response
        """
        def decorator(func):
            self.add_route(path, func)
            return func
        return decorator
    
    def handle(self, raw_data):
        """
        处理请求
        
        参数：
            raw_data: 原始HTTP请求数据
        
        返回：
            元组 (response_bytes, status_code)
        """
        # 默认使用静态文件控制器
        return self.static_controller.handle(raw_data)
    
    def list_routes(self):
        """
        列出所有注册的路由
        
        返回：
            路由列表
        """
        return [(route.path, route.handler.__name__) for route in self.routes]


# 全局路由实例
router = Router()
