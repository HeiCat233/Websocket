"""
================================================================================
HTTP请求解析模块
================================================================================

【模块功能】
本模块负责解析客户端发来的原始HTTP请求报文，提取请求行中的关键信息。

【HTTP协议基础】
HTTP（HyperText Transfer Protocol）是Web通信的基础协议，采用请求-响应模型：
- 客户端发送HTTP请求（Request）
- 服务器返回HTTP响应（Response）

【HTTP请求报文格式】
    GET /index.html HTTP/1.1\r\n       ← 请求行：方法 路径 HTTP版本
    Host: localhost:8080\r\n           ← 请求头（可以有多个）
    User-Agent: Mozilla/5.0\r\n
    \r\n                               ← 空行，标识头部结束
    [请求体（GET请求通常为空）]

【什么是URL编码】
URL中某些字符无法直接使用（如空格、中文、特殊符号），需要百分号编码：
- 空格 → %20 或 +
- 中文"你" → %E4%BD%A0（UTF-8编码的十六进制表示）
- 斜杠/ → %2F

================================================================================
"""

# 【类定义】
# Python中使用class关键字定义类
# 类是面向对象编程的核心概念，将数据和操作封装在一起
class HTTPRequest:
    """
    HTTP请求数据封装类
    
    【什么是封装？】
    封装是将数据和操作数据的方法组织在一起的形式。
    这样可以将请求的所有相关信息（method、path等）组织在一起，
    方便在函数之间传递，而不需要使用多个独立的变量。
    
    【为什么需要这个类？】
    解析HTTP请求后，会得到多个相关信息：
    - 请求方法（GET、POST等）
    - 请求路径（/index.html）
    - HTTP版本（HTTP/1.0）
    - 原始数据（用于调试）
    
    使用类可以将这些相关数据组织在一起，作为整体传递。
    
    【类的属性】
    属性是类中的变量，存储对象的状态。
    例如：一个HTTPRequest对象代表一次具体的请求，
    它的method属性存储该请求的方法（如"GET"）。
    
    属性：
        method: HTTP方法（GET、POST等），本服务器仅支持GET
               【示例】"GET", "POST", "PUT", "DELETE"
               【默认值】空字符串""
        path: 请求路径（如/index.html、/article/post1.html）
             【示例】"/index.html", "/article/post2.html"
             【默认值】空字符串""
        version: HTTP版本（如HTTP/1.0、HTTP/1.1）
                【示例】"HTTP/1.0", "HTTP/1.1"
                【默认值】空字符串""
        raw_data: 原始请求字节数据，用于调试或扩展功能
                 【示例】b"GET /index.html HTTP/1.1\r\nHost: ..."
                 【默认值】空字节串b""
    """
    
    def __init__(self):
        """
        构造函数：创建HTTPRequest对象时自动调用的初始化方法
        
        【什么是__init__？】
        __init__是Python类的构造函数（初始化方法）。
        当使用HTTPRequest()创建对象时，会自动调用这个方法。
        我们在这里初始化所有属性，设置默认值。
        
        【self参数】
        self是一个特殊参数，指向当前创建的对象实例。
        通过self，我们可以访问和修改对象的属性。
        
        注意：self不是关键字，可以换成其他名字，但约定俗成用self。
        """
        self.method = ""      # 初始化HTTP方法为空字符串
        self.path = ""        # 初始化请求路径为空字符串
        self.version = ""     # 初始化HTTP版本为空字符串
        self.raw_data = b""   # 初始化原始数据为空字节串
                               # b""表示字节串（bytes），而非普通字符串（str）
                               # Socket通信中使用字节串，因为网络传输的是字节


def url_decode(url_string: str) -> str:
    """
    URL解码函数：将百分号编码转换为原始字符
    
    【为什么需要URL解码？】
    URL中有一些特殊字符无法直接使用：
    - 空格：URL中不能直接有空格（会被解析为分隔符）
    - 中文：URL只支持ASCII字符，中文需要编码
    - 特殊符号：如#、?、&等有特殊含义，需要编码
    
    【编码规则】
    将字符转换为UTF-8字节序列，然后用%XX的十六进制形式表示。
    例如：
    - 空格（ASCII 32）→ %20
    - 中文"你"（UTF-8: E4 BD A0）→ %E4%BD%A0
    
    【表单数据的特殊情况】
    在HTML表单中，空格可以用+号表示，这是历史遗留的规则。
    例如：name=hello+world 等价于 name=hello world
    
    【函数设计思路】
    1. 逐字符扫描URL字符串
    2. 发现%开头，检查后面两位是否是十六进制数
    3. 如果是，转换为对应字符；如果不是，保留原字符
    4. 发现+号，转换为空格
    5. 其他字符直接保留
    
    参数：
        url_string: 包含百分号编码的URL字符串
                   【类型】str（普通字符串）
                   【示例】"%E4%BD%A0%20world", "hello+world"
    
    返回：
        解码后的原始字符串
        【类型】str
        【示例】"你好 world", "hello world"
    """
    result = []  # 使用列表存储字符
                  # 【为什么用列表而不是字符串？】
                  # 字符串是不可变类型，每次拼接都会创建新字符串
                  # 列表是可变类型，append操作更高效
                  # 最后用''.join()一次性拼接所有字符
    
    i = 0  # 字符串索引，指向当前处理的字符位置
    while i < len(url_string):
        # 【处理百分号编码】
        # 检查当前字符是否是%且后面还有至少2个字符
        if url_string[i] == '%' and i + 2 < len(url_string):
            try:
                # 提取%后面的两位十六进制数
                # 例如：%E4 → 提取"E4"
                hex_value = url_string[i+1:i+3]
                
                # 将十六进制字符串转换为整数
                # int(hex_value, 16)表示将hex_value作为16进制数解析
                # 16进制使用0-9和A-F（或a-f），基数是16
                # 例如：int("E4", 16) = 14*16 + 4 = 228
                char_code = int(hex_value, 16)
                
                # 将数字转换为对应的字符
                # chr()函数将Unicode码点转换为字符
                # 例如：chr(228) = "ä"（拉丁字符）
                #       chr(0x4E00) = "一"（中文）
                result.append(chr(char_code))
                
                # 跳过已处理的3个字符（%XX）
                # i += 3 使得下一次循环从下一个字符开始
                i += 3
            except ValueError:
                # 【异常处理】
                # ValueError发生在int()无法将字符串转换为整数时
                # 例如：int("GH", 16) 会抛出ValueError
                # 
                # 遇到无效的十六进制数，保留原字符%，不跳过
                result.append(url_string[i])
                i += 1
        elif url_string[i] == '+':
            # 【处理+号】
            # 在表单数据中，+号表示空格
            result.append(' ')
            i += 1
        else:
            # 【普通字符】
            # 直接保留，不做任何处理
            result.append(url_string[i])
            i += 1
    
    # 【将字符列表拼接为字符串】
    # ''.join(result)：用空字符串连接列表中的所有字符
    # 相当于 '' + result[0] + result[1] + ...
    return ''.join(result)


def parse_request(raw_data: bytes) -> HTTPRequest:
    """
    解析原始HTTP请求数据，提取请求行信息
    
    【HTTP请求行结构】
    HTTP请求的第一行叫做"请求行"（Request Line），
    格式为：方法 路径 HTTP版本
    
    例如：
        GET /index.html HTTP/1.1
        POST /submit HTTP/1.0
        DELETE /user/123 HTTP/1.1
    
    【为什么只解析请求行？】
    对于静态文件服务器，我们只需要知道：
    1. 请求方法是什么（GET还是POST）
    2. 请求的路径是什么（/index.html）
    
    请求头（如Host、User-Agent等）对于文件服务没有实际用途，
    因此我们只解析第一行，忽略其他内容。
    
    【处理流程】
    1. 检查数据是否为空
    2. 将字节数据解码为字符串
    3. 按\r\n分割成行
    4. 提取第一行作为请求行
    5. 按空格分割请求行
    6. 提取方法、路径、版本
    7. 对路径进行URL解码
    
    参数：
        raw_data: 客户端发送的原始HTTP请求字节数据
                  【类型】bytes（字节串）
                  【示例】b"GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
    
    返回：
        HTTPRequest对象，包含method、path、version字段
        【类型】HTTPRequest
    """
    # 创建空的HTTPRequest对象
    # 此时对象的四个属性都是初始值（空字符串或空字节串）
    request = HTTPRequest()
    
    # 保存原始数据到对象中
    # 这样后续如果需要调试或分析原始请求，可以访问raw_data
    request.raw_data = raw_data
    
    # 【检查数据是否为空】
    # 如果客户端发送了空数据（如立即断开连接），直接返回空对象
    if not raw_data:
        return request
    
    try:
        # ==================== 步骤1：解码字节数据 ====================
        
        # 【字节与字符串的转换】
        # 网络传输使用字节（bytes），但我们处理文本用字符串（str）
        # decode('utf-8')：将字节序列转换为UTF-8字符串
        # 
        # 【为什么用UTF-8？】
        # UTF-8是现代Web的标准编码：
        # - ASCII字符（英文、数字、符号）用1字节表示
        # - 中文等字符用3-4字节表示
        # - 兼容ASCII编码
        # 
        # 【可能的问题】
        # 如果数据不是有效的UTF-8序列（如二进制文件），decode()会抛出UnicodeDecodeError
        # 我们用try-except捕获这个异常
        data_str = raw_data.decode('utf-8')
        
        # ==================== 步骤2：分割数据行 ====================
        
        # 【HTTP协议的换行符】
        # HTTP/1.1规范规定使用CRLF（\r\n）作为行结束符
        # 这是历史遗留，来自早期的打字机通信
        # \r：回车（Carriage Return），回到行首
        # \n：换行（Line Feed），移到下一行
        # 
        # 【split('\r\n')的作用】
        # 将字符串按\r\n分割成列表
        # 例如："GET /a\r\nHost: b\r\n\r\n" → ["GET /a", "Host: b", "", ""]
        lines = data_str.split('\r\n')
        
        # ==================== 步骤3：解析请求行 ====================
        
        if lines:
            # 提取第一行（请求行）
            # HTTP请求至少有请求行，即使没有请求头
            request_line = lines[0]  # 例如："GET /index.html HTTP/1.1"
            
            # 【按空格分割请求行】
            # HTTP规范使用单个空格分隔各部分
            # 注意：路径中可能包含空格（URL编码为%20或+），但不会影响分割
            # 因为URL编码的空格不是真正的空格字符
            parts = request_line.split(' ')
            
            # 【安全地提取各部分】
            # 使用len()检查数组长度，避免索引越界
            # HTTP规范规定请求行必须有3部分，但某些客户端可能发送不完整的请求
            
            if len(parts) >= 1:
                # 提取HTTP方法
                # 常见方法：GET、POST、PUT、DELETE、HEAD、OPTIONS
                request.method = parts[0]      # 例如："GET"
            
            if len(parts) >= 2:
                # 提取请求路径
                # 需要进行URL解码，因为路径中可能有编码字符
                # 例如："%E4%B8%AD%E6%96%87" → "中文"
                request.path = url_decode(parts[1])  # 例如："index.html"
            
            if len(parts) >= 3:
                # 提取HTTP版本
                # 常见版本：HTTP/1.0、HTTP/1.1
                request.version = parts[2]     # 例如："HTTP/1.1"
    
    except Exception:
        # 【异常处理】
        # 可能发生的异常：
        # 1. UnicodeDecodeError：数据不是有效的UTF-8
        # 2. IndexError：请求行格式异常，parts数组长度不足
        # 3. 其他未知异常
        #
        # 【处理策略】
        # 静默处理，返回部分填充的HTTPRequest对象
        # 这样服务器可以尽可能处理请求，即使请求格式不标准
        pass
    
    # 返回填充好的HTTPRequest对象
    # 调用者可以通过request.method、request.path等访问解析结果
    return request
