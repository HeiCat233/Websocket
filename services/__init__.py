"""
================================================================================
服务模块
================================================================================

【模块说明】
服务层负责处理核心业务逻辑。

【服务列表】
- request_service: 请求解析服务
- response_service: 响应生成服务
- file_service: 文件处理服务

================================================================================
"""

# 请求服务
from services.request_service import parse_request, HTTPRequest, RequestValidator

# 响应服务
from services.response_service import (
    HTTPResponse,
    build_response,
    build_error_response,
    get_error_description,
    STATUS_PHRASES
)

# 文件服务
from services.file_service import FileService, PathResolver, get_mime_type

__all__ = [
    'parse_request',
    'HTTPRequest',
    'RequestValidator',
    'HTTPResponse',
    'build_response',
    'build_error_response',
    'get_error_description',
    'STATUS_PHRASES',
    'FileService',
    'PathResolver',
    'get_mime_type'
]
