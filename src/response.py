"""
================================================================================
响应处理模块
================================================================================

【模块功能】
负责HTTP响应的生成，构造符合HTTP协议的响应报文。

【模块职责】
1. 构建完整的HTTP响应报文
2. 生成错误页面
3. 处理MIME类型和字符编码

【响应格式】
HTTP/1.0 200 OK\r\n
Server: SimplePythonServer/1.0\r\n
Content-Type: text/html; charset=utf-8\r\n
Content-Length: 1234\r\n
Connection: close\r\n
\r\n
<响应体>

【设计原则】
- 单一职责：只负责响应生成
- 格式化响应：响应格式符合HTTP规范
- 错误处理：为各种错误情况提供默认响应

================================================================================
"""

from typing import Optional

# HTTP状态码与状态短语映射
STATUS_PHRASES = {
    200: "OK",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    408: "Request Timeout",
    500: "Internal Server Error"
}


class HTTPResponse:
    """
    HTTP响应类
    
    【设计说明】
    封装HTTP响应的所有信息，包括状态码、内容、头部等。
    
    【属性】
        status_code: HTTP状态码
        content_type: MIME类型
        body: 响应体内容（字节）
        headers: 额外的响应头
    """
    
    def __init__(
        self,
        status_code: int = 200,
        content_type: str = "text/html",
        body: bytes = b"",
        headers: Optional[dict] = None
    ):
        self.status_code = status_code
        self.content_type = content_type
        self.body = body
        self.headers = headers or {}
    
    def to_bytes(self, server_name: str = "SimplePythonServer/1.0") -> bytes:
        """
        将响应对象转换为HTTP响应字节数据
        
        参数：
            server_name: 服务器标识
        
        返回：
            完整的HTTP响应字节数据
        """
        # 获取状态短语
        status_phrase = STATUS_PHRASES.get(self.status_code, "Unknown")
        
        # 处理字符编码
        content_type = self.content_type
        if 'text/html' in content_type and 'charset' not in content_type:
            content_type = f"{content_type}; charset=utf-8"
        
        # 构建响应头
        response_headers = [
            f"HTTP/1.0 {self.status_code} {status_phrase}",
            f"Server: {server_name}",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(self.body)}",
            "Connection: close",
            "Cache-Control: public, max-age=86400",
            "Expires: Wed, 31 Dec 2025 23:59:59 GMT"
        ]
        
        # 添加自定义头部
        for key, value in self.headers.items():
            response_headers.append(f"{key}: {value}")
        
        # 空行分隔头部和主体
        response_headers.append("")
        
        # 组装完整响应
        return '\r\n'.join(response_headers).encode('utf-8') + self.body


def build_response(
    status_code: int,
    content_type: str,
    body: bytes
) -> bytes:
    """
    快捷构建HTTP响应
    
    参数：
        status_code: HTTP状态码
        content_type: MIME类型
        body: 响应体内容
    
    返回：
        完整的HTTP响应字节数据
    """
    response = HTTPResponse(status_code, content_type, body)
    return response.to_bytes()


def build_error_response(status_code: int) -> bytes:
    """
    构建错误响应页面
    
    【设计说明】
    为常见错误生成美观的HTML错误页面。
    页面使用内联CSS，无需额外请求。
    
    参数：
        status_code: HTTP错误状态码
    
    返回：
        包含HTML错误页面的HTTP响应
    """
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    error_description = get_error_description(status_code)
    
    # 构建HTML错误页面
    error_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} {status_phrase}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .error-container {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }}
        .status-code {{
            font-size: 120px;
            font-weight: 700;
            margin: 0 0 20px 0;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}
        .status-phrase {{
            font-size: 28px;
            font-weight: 600;
            margin: 0 0 20px 0;
        }}
        .error-desc {{
            font-size: 16px;
            opacity: 0.9;
            margin: 0 0 30px 0;
        }}
        .home-link {{
            display: inline-block;
            padding: 12px 30px;
            background: rgba(255, 255, 255, 0.25);
            color: #fff;
            text-decoration: none;
            border-radius: 30px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        .home-link:hover {{
            background: rgba(255, 255, 255, 0.35);
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="status-code">{status_code}</div>
        <div class="status-phrase">{status_phrase}</div>
        <div class="error-desc">{error_description}</div>
        <a href="/" class="home-link">返回首页</a>
    </div>
</body>
</html>""".strip()
    
    return build_response(status_code, "text/html", error_html.encode('utf-8'))


def get_error_description(status_code: int) -> str:
    """
    获取错误描述
    
    参数：
        status_code: HTTP错误状态码
    
    返回：
        中文错误描述
    """
    descriptions = {
        403: "您无权访问此资源。",
        404: "抱歉，您访问的页面不存在。",
        405: "不支持此请求方法，请使用 GET 方法。",
        500: "服务器内部发生错误，请稍后重试。"
    }
    return descriptions.get(status_code, "发生未知错误。")
