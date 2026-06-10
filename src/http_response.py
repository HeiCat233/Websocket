# ============================================================================
# HTTP响应生成模块
# 功能：根据处理结果构建符合HTTP/1.0规范的响应报文
# ============================================================================

# HTTP状态码与状态短语映射表
# 本服务器支持的所有HTTP状态码及其描述
STATUS_PHRASES = {
    200: "OK",                      # 请求成功
    403: "Forbidden",               # 禁止访问（路径穿越攻击被拦截）
    404: "Not Found",               # 资源未找到
    405: "Method Not Allowed",      # 方法不允许（使用了非GET方法）
    500: "Internal Server Error"    # 服务器内部错误
}


def build_response(status_code: int, content_type: str, body: bytes) -> bytes:
    """
    构建完整的HTTP响应报文
    
    HTTP响应格式：
        HTTP/1.0 200 OK\r\n
        Server: SimplePythonServer/1.0\r\n
        Content-Type: text/html; charset=utf-8\r\n
        Content-Length: 1234\r\n
        Connection: close\r\n
        \r\n
        <body内容>
    
    参数：
        status_code: HTTP状态码（如200、404）
        content_type: MIME类型（如text/html、image/png）
        body: 响应体内容（字节串）
    
    返回：
        完整的HTTP响应报文（字节串），可直接通过Socket发送
    """
    # 从字典中获取状态短语，如果不存在则返回"Unknown"
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    
    # 计算响应体长度（字节数）
    content_length = len(body)
    
    # 【重要】确保HTML内容类型包含UTF-8编码声明
    # 如果不指定charset，浏览器可能使用ISO-8859-1导致中文乱码
    if 'text/html' in content_type and 'charset' not in content_type:
        content_type = f"{content_type}; charset=utf-8"
    
    # 构建HTTP响应头（每行以\r\n结尾，空行表示头部结束）
    headers = [
        f"HTTP/1.0 {status_code} {status_phrase}",  # 状态行
        "Server: SimplePythonServer/1.0",           # 服务器标识
        f"Content-Type: {content_type}",            # 内容类型（含字符编码）
        f"Content-Length: {content_length}",        # 内容长度（字节数）
        "Connection: close",                        # 短连接（HTTP/1.0默认行为）
        ""                                          # 空行：分隔头部和主体
    ]
    
    # 将头部拼接为字符串并编码为UTF-8，然后附加响应体
    # 最终格式：b'HTTP/1.0 200 OK\r\n...\r\n\r\n<body>'
    response = '\r\n'.join(headers).encode('utf-8') + body
    return response


def build_error_response(status_code: int) -> bytes:
    """
    快捷构建HTML格式的错误响应页面
    
    为常见错误状态码生成美观的HTML页面，包含：
    - 大号状态码显示（如404）
    - 状态短语（如Not Found）
    - 错误描述（中文说明）
    - 返回首页链接
    
    参数：
        status_code: HTTP错误状态码（403/404/405/500）
    
    返回：
        完整的HTTP响应报文（包含HTML错误页面）
    """
    # 获取状态短语（如404 → "Not Found"）
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    
    # 构建美观的HTML错误页面（使用现代CSS样式）
    error_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} {status_phrase}</title>
    <style>
        /* 全局样式：渐变背景 + 居中布局 */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #fff;
        }}
        /* 错误容器：毛玻璃效果 */
        .error-container {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }}
        /* 大号状态码：120px字体 + 阴影 */
        .status-code {{
            font-size: 120px;
            font-weight: 700;
            margin: 0 0 20px 0;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}
        /* 状态短语：28px粗体 */
        .status-phrase {{
            font-size: 28px;
            font-weight: 600;
            margin: 0 0 20px 0;
        }}
        /* 错误描述：半透明白色文字 */
        .error-desc {{
            font-size: 16px;
            opacity: 0.9;
            margin: 0 0 30px 0;
        }}
        /* 返回首页按钮：半透明背景 + 悬停动画 */
        .home-link {{
            display: inline-block;
            padding: 12px 30px;
            background: rgba(255, 255, 255, 0.25);
            color: #fff;
            text-decoration: none;
            border-radius: 30px;
            font-weight: 500;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.3);
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
        <div class="error-desc">
            {get_error_description(status_code)}
        </div>
        <a href="/" class="home-link">返回首页</a>
    </div>
</body>
</html>
    """.strip()  # 去除首尾空白行
    
    # 调用build_response构建完整HTTP响应（自动添加charset=utf-8）
    return build_response(status_code, "text/html", error_html.encode('utf-8'))


def get_error_description(status_code: int) -> str:
    """
    根据状态码返回中文错误描述
    
    参数：
        status_code: HTTP错误状态码
    
    返回：
        友好的中文错误提示信息
    """
    descriptions = {
        403: "您无权访问此资源。",
        404: "抱歉，您访问的页面不存在。",
        405: "不支持此请求方法，请使用 GET 方法。",
        500: "服务器内部发生错误，请稍后重试。"
    }
    # 如果找不到对应描述，返回通用提示
    return descriptions.get(status_code, "发生未知错误。")