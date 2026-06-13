"""
================================================================================
静态文件控制器
================================================================================

【模块说明】
处理静态文件的HTTP请求。

【控制器职责】
- 接收HTTP请求
- 调用文件服务读取文件
- 返回HTTP响应

================================================================================
"""

from services.file_service import FileService
from services.response_service import build_response, build_error_response
from services import parse_request


class StaticFileController:
    """
    静态文件控制器
    
    【职责】
    处理静态文件的请求，将URL路径映射到实际文件。
    """
    
    def __init__(self):
        self.file_service = FileService()
    
    def handle(self, raw_data):
        """
        处理静态文件请求
        
        参数：
            raw_data: 原始HTTP请求数据
        
        返回：
            元组 (response_bytes, status_code)
        """
        # 解析请求
        request = parse_request(raw_data)
        
        # 获取请求路径
        url_path = request.get_path_without_query()
        
        # 读取文件
        success, content, mime_type, status_code = self.file_service.read(url_path)
        
        if success:
            response = build_response(200, mime_type, content)
            return (response, 200)
        else:
            error_response = build_error_response(status_code)
            return (error_response, status_code)
