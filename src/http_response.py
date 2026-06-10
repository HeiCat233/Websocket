STATUS_PHRASES = {
    200: "OK",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error"
}


def build_response(status_code: int, content_type: str, body: bytes) -> bytes:
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    content_length = len(body)
    
    # 确保HTML内容类型包含UTF-8编码声明
    if 'text/html' in content_type and 'charset' not in content_type:
        content_type = f"{content_type}; charset=utf-8"
    
    headers = [
        f"HTTP/1.0 {status_code} {status_phrase}",
        "Server: SimplePythonServer/1.0",
        f"Content-Type: {content_type}",
        f"Content-Length: {content_length}",
        "Connection: close",
        ""
    ]
    
    response = '\r\n'.join(headers).encode('utf-8') + body
    return response


def build_error_response(status_code: int) -> bytes:
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    
    error_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} {status_phrase}</title>
    <style>
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
    """.strip()
    
    return build_response(status_code, "text/html", error_html.encode('utf-8'))


def get_error_description(status_code: int) -> str:
    descriptions = {
        403: "您无权访问此资源。",
        404: "抱歉，您访问的页面不存在。",
        405: "不支持此请求方法，请使用 GET 方法。",
        500: "服务器内部发生错误，请稍后重试。"
    }
    return descriptions.get(status_code, "发生未知错误。")