"""
================================================================================
错误处理控制器
================================================================================

【模块说明】
处理各种HTTP错误响应。

【控制器职责】
- 生成统一的错误页面
- 返回正确的HTTP状态码

================================================================================
"""

from services.response_service import build_error_response


class ErrorController:
    """
    错误处理控制器
    
    【职责】
    生成统一的错误响应页面。
    """
    
    @staticmethod
    def handle_403():
        """
        处理403禁止访问错误
        
        返回：
            HTTP错误响应字节数据
        """
        return build_error_response(403)
    
    @staticmethod
    def handle_404():
        """
        处理404页面未找到错误
        
        返回：
            HTTP错误响应字节数据
        """
        return build_error_response(404)
    
    @staticmethod
    def handle_405():
        """
        处理405方法不允许错误
        
        返回：
            HTTP错误响应字节数据
        """
        return build_error_response(405)
    
    @staticmethod
    def handle_408():
        """
        处理408请求超时错误
        
        返回：
            HTTP错误响应字节数据
        """
        return build_error_response(408)
    
    @staticmethod
    def handle_500():
        """
        处理500服务器内部错误
        
        返回：
            HTTP错误响应字节数据
        """
        return build_error_response(500)
