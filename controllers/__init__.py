"""
================================================================================
控制器模块
================================================================================

【模块说明】
控制器负责处理HTTP请求并返回响应。

【控制器列表】
- StaticFileController: 静态文件控制器
- ErrorController: 错误处理控制器

================================================================================
"""

from controllers.static_controller import StaticFileController
from controllers.error_controller import ErrorController

__all__ = ['StaticFileController', 'ErrorController']
