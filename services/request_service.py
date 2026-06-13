"""
================================================================================
请求服务模块
================================================================================

【模块说明】
负责HTTP请求的解析和处理。

【服务内容】
- HTTPRequest 数据类：封装请求信息
- parse_request 函数：解析原始请求数据
- RequestValidator 类：请求验证器

================================================================================
"""

from dataclasses import dataclass
from utils import url_decode


@dataclass
class HTTPRequest:
    """
    HTTP请求数据类
    
    属性：
        method: HTTP方法（GET、POST等）
        path: 请求路径
        version: HTTP版本
        raw_data: 原始请求字节数据
    """
    method: str = ""
    path: str = ""
    version: str = ""
    raw_data: bytes = b""
    
    def is_safe_method(self):
        """检查是否为安全的请求方法"""
        return self.method == 'GET'
    
    def get_path_without_query(self):
        """获取不含查询参数的路径"""
        return self.path.split('?')[0]


def parse_request(raw_data):
    """
    解析原始HTTP请求数据
    
    【HTTP请求格式】
    GET /index.html HTTP/1.1\r\n
    Host: localhost:8080\r\n
    \r\n
    
    参数：
        raw_data: 原始HTTP请求字节数据
    
    返回：
        HTTPRequest对象
    """
    request = HTTPRequest()
    request.raw_data = raw_data
    
    if not raw_data:
        return request
    
    try:
        data_str = raw_data.decode('utf-8')
        lines = data_str.split('\r\n')
        
        if lines:
            request_line = lines[0]
            parts = request_line.split(' ')
            
            if len(parts) >= 1:
                request.method = parts[0]
            if len(parts) >= 2:
                request.path = url_decode(parts[1])
            if len(parts) >= 3:
                request.version = parts[2]
    
    except Exception:
        pass
    
    return request


class RequestValidator:
    """
    请求验证器
    
    【验证规则】
    - 请求方法必须是GET
    - 请求路径必须合法
    """
    
    @staticmethod
    def validate_method(request):
        """验证请求方法"""
        if not request.method:
            return (False, "Missing HTTP method")
        
        if request.method != 'GET':
            return (False, f"Method '{request.method}' not allowed")
        
        return (True, "")
    
    @staticmethod
    def validate_path(request):
        """验证请求路径"""
        if not request.path:
            return (False, "Missing request path")
        
        dangerous_patterns = ['..', '\\']
        for pattern in dangerous_patterns:
            if pattern in request.path:
                return (False, f"Invalid path pattern: {pattern}")
        
        return (True, "")
    
    @staticmethod
    def validate(request):
        """完整验证"""
        is_valid, error = RequestValidator.validate_method(request)
        if not is_valid:
            return (is_valid, error)
        
        is_valid, error = RequestValidator.validate_path(request)
        return (is_valid, error)
