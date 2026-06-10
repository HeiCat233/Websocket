# ============================================================================
# HTTP请求解析模块
# 功能：解析客户端发来的原始HTTP请求报文，提取请求行信息
# ============================================================================

class HTTPRequest:
    """
    HTTP请求数据封装类
    
    属性：
        method: HTTP方法（GET、POST等），本服务器仅支持GET
        path: 请求路径（如/index.html、/article/post1.html）
        version: HTTP版本（如HTTP/1.0、HTTP/1.1）
        raw_data: 原始请求字节数据，用于调试或扩展功能
    """
    def __init__(self):
        self.method = ""      # 初始化HTTP方法为空字符串
        self.path = ""        # 初始化请求路径为空字符串
        self.version = ""     # 初始化HTTP版本为空字符串
        self.raw_data = b""   # 初始化原始数据为空字节串


def url_decode(url_string: str) -> str:
    """
    URL解码函数：将百分号编码转换为原始字符
    
    示例：
        "%20" → 空格
        "%E4%BD%A0" → "你"（UTF-8编码的中文）
        "+" → 空格（表单数据中的特殊规则）
    
    参数：
        url_string: 包含百分号编码的URL字符串
    
    返回：
        解码后的原始字符串
    """
    result = []  # 使用列表存储字符，比字符串拼接更高效
    i = 0
    while i < len(url_string):
        # 检测百分号编码：%XX（XX为两位十六进制数）
        if url_string[i] == '%' and i + 2 < len(url_string):
            try:
                # 提取两位十六进制数并转换为对应字符
                hex_value = url_string[i+1:i+3]
                result.append(chr(int(hex_value, 16)))  # int(,16)表示十六进制
                i += 3  # 跳过已处理的3个字符（%XX）
            except ValueError:
                # 如果转换失败（如%GH不是合法十六进制），保留原字符
                result.append(url_string[i])
                i += 1
        elif url_string[i] == '+':
            # 表单数据中，+号表示空格
            result.append(' ')
            i += 1
        else:
            # 普通字符直接保留
            result.append(url_string[i])
            i += 1
    return ''.join(result)  # 将字符列表拼接为完整字符串


def parse_request(raw_data: bytes) -> HTTPRequest:
    """
    解析原始HTTP请求数据，提取请求行信息
    
    HTTP请求格式示例：
        GET /index.html HTTP/1.1\r\n
        Host: localhost:8080\r\n
        User-Agent: Mozilla/5.0\r\n
        \r\n
    
    本函数仅解析第一行（请求行），忽略请求头
    
    参数：
        raw_data: 客户端发送的原始HTTP请求字节数据
    
    返回：
        HTTPRequest对象，包含method、path、version字段
    """
    request = HTTPRequest()  # 创建空的HTTPRequest对象
    request.raw_data = raw_data  # 保存原始数据供后续使用
    
    # 如果数据为空，直接返回空对象
    if not raw_data:
        return request
    
    try:
        # 【步骤1】将字节数据解码为UTF-8字符串
        # HTTP协议文本部分使用ASCII/UTF-8编码
        data_str = raw_data.decode('utf-8')
        
        # 【步骤2】按\r\n分割数据行（HTTP协议规定使用CRLF作为换行符）
        lines = data_str.split('\r\n')
        
        # 【步骤3】解析请求行（第一行）
        if lines:
            request_line = lines[0]  # 例如："GET /index.html HTTP/1.1"
            parts = request_line.split(' ')  # 按空格分割为三部分
            
            # 提取各部分（检查数组长度避免索引越界）
            if len(parts) >= 1:
                request.method = parts[0]      # GET
            if len(parts) >= 2:
                request.path = url_decode(parts[1])  # /index.html（进行URL解码）
            if len(parts) >= 3:
                request.version = parts[2]     # HTTP/1.1
    
    except Exception:
        # 如果解析过程中发生任何异常（如编码错误、索引越界）
        # 静默处理，返回部分填充的HTTPRequest对象
        pass
    
    return request