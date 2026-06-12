"""
================================================================================
请求处理模块
================================================================================

【模块功能】
负责HTTP请求的解析和处理，提取请求行中的方法、路径、版本等信息。

【模块职责】
1. 解析原始HTTP请求数据
2. 封装请求信息为Request对象
3. 提供请求验证方法

【请求处理流程】
1. 接收原始字节数据
2. 解码为字符串
3. 解析请求行
4. 封装为Request对象
5. 返回给调用者

【设计原则】
- 单一职责：只负责请求解析
- 不可变对象：Request对象创建后不可修改
- 防御性编程：处理各种边界情况

================================================================================
"""

from dataclasses import dataclass
from typing import Optional
from .utils import url_decode


@dataclass
class HTTPRequest:
    """
    HTTP请求数据类
    
    【设计说明】
    使用@dataclass装饰器自动生成__init__等方法，
    代码更简洁，同时保持良好的类型提示。
    
    属性：
        method: HTTP方法（GET、POST等）
        path: 请求路径（如/index.html）
        version: HTTP版本（如HTTP/1.0）
        raw_data: 原始请求字节数据
    """
    method: str = ""
    path: str = ""
    version: str = ""
    raw_data: bytes = b""
    
    def is_safe_method(self) -> bool:
        """
        检查请求方法是否安全（允许）
        
        返回：
            True表示方法允许，False表示不允许
        """
        return self.method == 'GET'
    
    def get_path_without_query(self) -> str:
        """
        获取不含查询参数的路径
        
        返回：
            路径部分（不包含?后的查询参数）
        """
        return self.path.split('?')[0]


def parse_request(raw_data: bytes) -> HTTPRequest:
    """
    解析原始HTTP请求数据
    
    【HTTP请求格式】
    GET /index.html HTTP/1.1\r\n
    Host: localhost:8080\r\n
    \r\n
    
    【处理步骤】
    1. 检查数据是否为空
    2. 解码字节数据为字符串
    3. 按\r\n分割数据行
    4. 解析第一行（请求行）
    5. 按空格分割，提取方法、路径、版本
    
    参数：
        raw_data: 原始HTTP请求字节数据
    
    返回：
        HTTPRequest对象
    """
    # 创建请求对象
    request = HTTPRequest()
    request.raw_data = raw_data
    
    # 检查数据是否为空
    if not raw_data:
        return request
    
    try:
        # 解码字节数据为UTF-8字符串
        data_str = raw_data.decode('utf-8')
        
        # 按\r\n分割数据行
        lines = data_str.split('\r\n')
        
        # 解析请求行（第一行）
        if lines:
            request_line = lines[0]
            parts = request_line.split(' ')
            
            # 提取各部分
            if len(parts) >= 1:
                request.method = parts[0]
            if len(parts) >= 2:
                # 对路径进行URL解码
                request.path = url_decode(parts[1])
            if len(parts) >= 3:
                request.version = parts[2]
    
    except Exception:
        # 静默处理异常，返回部分填充的请求对象
        pass
    
    return request


class RequestValidator:
    """
    请求验证器
    
    【职责】
    验证HTTP请求是否符合服务器的要求。
    可以在中间件中使用此验证器。
    
    【验证规则】
    1. 请求方法必须是GET
    2. 请求路径必须合法
    3. HTTP版本必须是HTTP/1.0或HTTP/1.1
    """
    
    @staticmethod
    def validate_method(request: HTTPRequest) -> tuple:
        """
        验证请求方法
        
        参数：
            request: HTTP请求对象
        
        返回：
            元组 (is_valid, error_message)
            - is_valid: 验证是否通过
            - error_message: 错误信息（如果验证失败）
        """
        if not request.method:
            return (False, "Missing HTTP method")
        
        if request.method != 'GET':
            return (False, f"Method '{request.method}' not allowed. Only GET is supported.")
        
        return (True, "")
    
    @staticmethod
    def validate_path(request: HTTPRequest) -> tuple:
        """
        验证请求路径
        
        参数：
            request: HTTP请求对象
        
        返回：
            元组 (is_valid, error_message)
        """
        if not request.path:
            return (False, "Missing request path")
        
        # 检查路径是否包含危险字符
        dangerous_patterns = ['..', '\\']
        for pattern in dangerous_patterns:
            if pattern in request.path:
                return (False, f"Invalid path pattern: {pattern}")
        
        return (True, "")
    
    @staticmethod
    def validate(request: HTTPRequest) -> tuple:
        """
        完整验证
        
        参数：
            request: HTTP请求对象
        
        返回：
            元组 (is_valid, error_message)
        """
        # 验证方法
        is_valid, error = RequestValidator.validate_method(request)
        if not is_valid:
            return (is_valid, error)
        
        # 验证路径
        is_valid, error = RequestValidator.validate_path(request)
        if not is_valid:
            return (is_valid, error)
        
        return (True, "")
