"""
================================================================================
HTTP响应生成模块
================================================================================

【模块功能】
本模块负责根据处理结果生成符合HTTP/1.0规范的响应报文。

【HTTP响应基础】
服务器收到客户端请求后，需要返回HTTP响应，格式为：
    状态行 + 响应头 + 空行 + 响应体

【什么是MIME类型？】
MIME（Multipurpose Internet Mail Extensions）是一种标准，
用于标识文件类型。浏览器根据Content-Type决定如何处理响应内容。

常见MIME类型：
- text/html：HTML文档
- text/css：CSS样式表
- text/plain：纯文本
- image/png：PNG图片
- image/jpeg：JPEG图片
- application/javascript：JavaScript

================================================================================
"""

# 【字典定义】
# Python中使用{}创建字典，用于存储键值对映射
# 字典的查找效率是O(1)，比列表的O(n)快很多
STATUS_PHRASES = {
    # 键：HTTP状态码（整数）
    # 值：状态短语（字符串）
    
    200: "OK",                      # 请求成功，资源已找到
                                     # 【常见场景】请求的文件存在且可读
    
    403: "Forbidden",               # 禁止访问，服务器拒绝提供资源
                                     # 【常见场景】路径穿越攻击被拦截
                                     # 【注意】不同于401 Unauthorized，后者需要认证
    
    404: "Not Found",              # 未找到，请求的资源不存在
                                     # 【常见场景】请求的文件在服务器上不存在
                                     # 【返回内容】通常包含友好的错误页面
    
    405: "Method Not Allowed",      # 方法不允许，该HTTP方法不被支持
                                     # 【常见场景】使用了POST/PUT/DELETE等方法
                                     # 【说明】我们只支持GET方法
    
    500: "Internal Server Error"    # 服务器内部错误，处理请求时发生异常
                                     # 【常见场景】代码bug、文件读取失败等
                                     # 【注意】这是最后的保障，不应该经常出现
}


def build_response(status_code: int, content_type: str, body: bytes) -> bytes:
    """
    构建完整的HTTP响应报文
    
    【HTTP响应格式】
    HTTP响应由三部分组成：
    
    1. 状态行（Status Line）
       格式：HTTP版本 状态码 状态短语
       示例：HTTP/1.0 200 OK
       
    2. 响应头（Response Headers）
       格式：Header-Name: Header-Value
       每个头占一行，以\r\n结尾
       空行（\r\n）标识头部结束
       
    3. 响应体（Response Body）
       实际的内容，如HTML页面、图片等
    
    【完整的响应示例】
    HTTP/1.0 200 OK\r\n
    Server: SimplePythonServer/1.0\r\n
    Content-Type: text/html; charset=utf-8\r\n
    Content-Length: 1234\r\n
    Connection: close\r\n
    \r\n
    <html>...<html>
    
    【为什么要设置Content-Type？】
    浏览器需要知道如何处理响应内容：
    - text/html：浏览器渲染为HTML页面
    - image/png：浏览器显示为图片
    - text/css：浏览器加载为样式表
    
    【为什么要设置Content-Length？】
    告诉浏览器响应体的字节数：
    - 浏览器可以显示下载进度
    - 浏览器知道何时下载完成
    - 某些情况需要知道内容长度才能处理
    
    参数：
        status_code: HTTP状态码
                    【类型】int
                    【常见值】200（成功）、404（未找到）
        content_type: MIME类型
                     【类型】str
                     【示例】"text/html", "image/png", "text/css"
        body: 响应体内容
              【类型】bytes（字节串）
              【说明】必须传入字节串，因为网络传输使用字节
    
    返回：
        完整的HTTP响应报文（字节串）
        【类型】bytes
        【说明】可以直接通过socket.sendall()发送
    """
    # 【获取状态短语】
    # 从字典中查找状态码对应的短语
    # 如果找不到，使用"Unknown"作为默认值
    # get(key, default)是字典的安全访问方式，避免KeyError
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    
    # 【计算响应体长度】
    # len()返回字节数，而不是字符数
    # 对于纯ASCII文本，字节数=字符数
    # 对于包含中文的文本，字节数 > 字符数（UTF-8编码）
    content_length = len(body)
    
    # 【处理字符编码】
    # 对于HTML内容，我们需要确保指定UTF-8编码
    # 否则浏览器可能使用ISO-8859-1（Latin-1）编码，导致中文乱码
    # 
    # 【检查逻辑】
    # 1. 如果是text/html类型
    # 2. 且还没有指定charset
    # 3. 则添加"; charset=utf-8"
    if 'text/html' in content_type and 'charset' not in content_type:
        content_type = f"{content_type}; charset=utf-8"
    
    # 【构建响应头列表】
    # 每个HTTP头占一行，格式为"名字: 值"
    # \r\n是HTTP协议规定的行结束符
    headers = [
        # 状态行：包含HTTP版本、状态码、状态短语
        # 【注意】HTTP/1.0和HTTP/1.1的区别：
        # - HTTP/1.0：默认短连接，需要显式设置Connection: keep-alive
        # - HTTP/1.1：默认长连接，需要显式设置Connection: close
        f"HTTP/1.0 {status_code} {status_phrase}",
        
        # Server：服务器标识，便于调试和统计
        "Server: SimplePythonServer/1.0",
        
        # Content-Type：告诉浏览器内容类型和字符编码
        f"Content-Type: {content_type}",
        
        # Content-Length：响应体字节数
        f"Content-Length: {content_length}",
        
        # Connection：连接管理
        # "close"表示处理完请求后关闭连接（短连接）
        # 这是HTTP/1.0的默认行为
        "Connection: close",
        
        # Cache-Control：缓存控制指令
        # "public"：响应可以被任何缓存存储
        # "max-age=86400"：缓存有效期为86400秒（24小时）
        "Cache-Control: public, max-age=86400",
        
        # Expires：缓存过期时间（HTTP/1.0兼容）
        "Expires: Wed, 31 Dec 2025 23:59:59 GMT",
        
        # 空行：分隔头部和主体，这是HTTP协议的规定
        ""
    ]
    
    # 【组装完整响应】
    # 1. 用\r\n连接所有头部行
    # 2. 将字符串编码为UTF-8字节
    # 3. 附加响应体（已经是字节）
    # 
    # 【字符串编码】
    # 网络传输需要字节，但头部我们是字符串格式
    # 所以需要encode('utf-8')将字符串转为字节
    response = '\r\n'.join(headers).encode('utf-8') + body
    
    return response


def build_error_response(status_code: int) -> bytes:
    """
    快捷构建HTML格式的错误响应页面
    
    【为什么需要自定义错误页面？】
    1. 提供更好的用户体验，而不是浏览器默认的简陋页面
    2. 可以包含网站的导航链接，引导用户访问其他页面
    3. 保持网站风格的一致性
    4. 可以显示中文错误信息，更易理解
    
    【设计考虑】
    - 使用内联CSS，无需额外请求
    - 简洁美观，使用现代设计风格
    - 包含返回首页的链接
    - 响应式设计，适配不同屏幕
    
    【为什么使用渐变背景？】
    渐变背景比纯色更有视觉吸引力
    linear-gradient()从一种颜色平滑过渡到另一种颜色
    135deg表示从左下角到右上角的角度
    
    参数：
        status_code: HTTP错误状态码
                    【类型】int
                    【常见值】403、404、405、500
    
    返回：
        完整的HTTP响应报文（包含HTML错误页面）
        【类型】bytes
    """
    # 【获取状态短语】
    # 例如：404 → "Not Found"
    status_phrase = STATUS_PHRASES.get(status_code, "Unknown")
    
    # 【获取中文错误描述】
    # 为用户提供友好的中文提示
    error_description = get_error_description(status_code)
    
    # 【构建HTML错误页面】
    # 使用三引号"""定义多行字符串
    # f-string（格式化字符串）在{...}中插入变量值
    # 
    # 【HTML结构】
    # - DOCTYPE声明：告诉浏览器使用HTML5标准
    # - html标签：HTML文档的根元素
    # - head标签：元信息和资源引用
    # - body标签：页面的可见内容
    # 
    # 【CSS样式说明】
    # - font-family：字体栈，按顺序尝试使用可用字体
    # - text-align: center：内容居中
    # - background: linear-gradient：渐变背景
    # - border-radius：圆角效果
    # - box-shadow：阴影效果
    # - backdrop-filter: blur：毛玻璃效果（现代浏览器支持）
    # 
    # 【响应式设计】
    # - max-width: 600px：最大宽度600px
    # - margin: 0 auto：水平居中
    # - padding: 40px 20px：内边距
    # - min-height: 100vh：最小高度为视口高度
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
            {error_description}
        </div>
        <a href="/" class="home-link">返回首页</a>
    </div>
</body>
</html>
    """.strip()  # 去除首尾空白行，使HTML更整洁
    
    # 【构建HTTP响应】
    # 1. 将HTML字符串编码为UTF-8字节
    # 2. 调用build_response生成完整的HTTP响应
    # 【注意】build_response会自动添加charset=utf-8
    return build_response(status_code, "text/html", error_html.encode('utf-8'))


def get_error_description(status_code: int) -> str:
    """
    根据状态码返回中文错误描述
    
    【为什么需要这个函数？】
    不同的错误需要不同的提示信息：
    - 404：告诉用户页面不存在
    - 403：告诉用户无权访问
    - 405：告诉用户方法不支持
    
    【设计考虑】
    - 使用简洁易懂的中文
    - 提供解决问题的建议
    - 语气友好，不显得责备用户
    
    参数：
        status_code: HTTP错误状态码
                    【类型】int
    
    返回：
        友好的中文错误提示
        【类型】str
    """
    # 【字典定义错误描述】
    # 每个错误码对应一条中文提示
    descriptions = {
        # 403：通常是被安全机制拦截
        403: "您无权访问此资源。",
        
        # 404：最常见的错误，页面确实不存在
        404: "抱歉，您访问的页面不存在。",
        
        # 405：用户使用了错误的方法
        405: "不支持此请求方法，请使用 GET 方法。",
        
        # 500：服务器内部错误，通常是代码bug
        500: "服务器内部发生错误，请稍后重试。"
    }
    
    # 【返回对应描述或默认提示】
    # get()方法：如果键不存在，返回默认值
    return descriptions.get(status_code, "发生未知错误。")
