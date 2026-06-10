"""
================================================================================
文件处理模块
================================================================================

【模块功能】
本模块负责处理所有文件系统操作，包括：
1. 路径解析：将URL路径转换为文件系统路径
2. 安全检查：防止路径穿越攻击
3. MIME类型映射：根据文件扩展名返回正确的Content-Type
4. 文件读取：安全地读取文件内容

【什么是路径穿越攻击？】
路径穿越（Path Traversal）是一种安全漏洞，
攻击者通过构造特殊的URL，试图访问Web目录之外的文件。

例如：
- 正常请求：GET /index.html → 读取 www/index.html
- 攻击请求：GET /../../etc/passwd → 尝试读取系统密码文件

防御措施：
1. 规范化路径：处理.和..等特殊路径
2. 验证路径边界：确保最终路径在允许的目录内
3. 使用realpath()解析真实路径

================================================================================
"""

# 【导入os模块】
# os模块提供了与操作系统交互的接口
# 在Web服务器中主要用于：
# - 文件路径操作（join、dirname、abspath）
# - 文件属性检查（exists、isfile）
# - 文件读取（open）
import os

# ==================== 文档根目录配置 ====================

# 【确定Web资源的根目录】
# 所有URL路径都相对于这个目录解析
# 这是一个安全措施：用户只能访问这个目录下的文件

# 【获取当前脚本的目录】
# __file__是Python内置变量，存储当前文件的路径
# 例如：D:\develop\homework\webserver\src\file_handler.py
_current_dir = os.path.dirname(os.path.abspath(__file__))

# 【拼接出www目录的路径】
# os.path.join()：正确地拼接路径（自动处理不同操作系统的斜杠）
# '..'表示上级目录
# 最终结果：D:\develop\homework\webserver\www
DOC_ROOT = os.path.join(_current_dir, '..', 'www')

# 【转换为绝对路径】
# os.path.abspath()：将相对路径转换为绝对路径
# 处理.和..等特殊路径
DOC_ROOT = os.path.abspath(DOC_ROOT)


# ==================== MIME类型映射表 ====================

# 【MIME类型定义】
# MIME（Multipurpose Internet Mail Extensions）用于标识文件类型
# HTTP响应头中的Content-Type字段使用MIME类型

# 【为什么需要MIME类型？】
# 浏览器根据Content-Type决定如何处理响应：
# - text/html：渲染为HTML页面
# - text/css：加载为样式表
# - image/png：显示为图片
# - application/octet-stream：下载为文件

# 【为什么CSS和JS也要指定编码？】
# 虽然它们不是传统意义上的"文本"，但包含的字符需要正确解析
# CSS中的中文字体名、JS中的中文注释都需要UTF-8编码

MIME_TYPES = {
    # HTML文档
    # 【注意】.htm是旧式扩展名，某些旧系统使用
    '.html': 'text/html',                          # HTML文档
    '.htm': 'text/html',                           # HTML文档（旧式扩展名）
    
    # CSS样式表
    # 【charset=utf-8】确保CSS中的中文字符正确解析
    '.css': 'text/css; charset=utf-8',             # CSS样式表
    
    # JavaScript脚本
    # 【application/javascript】是标准MIME类型
    # 【charset=utf-8】确保JS中的中文注释正确解析
    '.js': 'application/javascript; charset=utf-8',# JavaScript脚本
    
    # 图片格式
    # 【PNG】无损压缩，支持透明，广泛用于图标和UI元素
    '.png': 'image/png',                           # PNG图片
    # 【JPEG】有损压缩，适合照片，压缩率高
    '.jpg': 'image/jpeg',                          # JPEG图片
    '.jpeg': 'image/jpeg',                         # JPEG图片（完整扩展名）
    # 【GIF】支持动画，但颜色有限（256色）
    '.gif': 'image/gif',                           # GIF图片
    
    # 纯文本
    # 【charset=utf-8】确保纯文本中的中文正确显示
    '.txt': 'text/plain; charset=utf-8'            # 纯文本
}


def resolve_path(url_path: str) -> tuple:
    """
    将URL路径解析为文件系统绝对路径，并进行安全检查
    
    【函数职责】
    这是Web服务器最重要的安全函数之一。
    它将用户请求的URL路径转换为实际的文件系统路径，
    同时检查是否存在路径穿越攻击的风险。
    
    【处理流程图】
    ┌─────────────────┐
    │  原始URL路径    │ 例如：/article/post1.html
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  处理根路径     │ / → /index.html
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  去除前导斜杠    │ /about.html → about.html
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  拼接文档根目录  │ DOC_ROOT + path
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  规范化路径     │ 处理..和.等
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  解析真实路径    │ realpath()
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  安全边界检查    │ 是否在DOC_ROOT内？
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  返回结果       │ (path, is_safe)
    └─────────────────┘
    
    【什么是URL路径规范化？】
    URL路径中可能包含特殊字符：
    - /./ → 表示当前目录，可忽略
    - /../ → 表示上级目录，需要处理
    - 连续斜杠// → 可简化为单个斜杠/
    
    例如：
    - /www/article/../about.html → /www/about.html
    - /www//article//post.html → /www/article/post.html
    
    【什么是路径穿越攻击？】
    恶意用户可能构造这样的URL：
    - /../../etc/passwd → 尝试读取Linux密码文件
    - /..\\..\\windows\\system32 → 尝试访问Windows系统目录
    
    我们的防御措施是：
    1. 使用os.path.normpath()规范化路径
    2. 使用os.path.realpath()获取真实路径
    3. 检查真实路径是否以DOC_ROOT开头
    
    参数：
        url_path: URL中的路径部分
                 【类型】str
                 【示例】"/index.html", "/article/post1.html"
    
    返回：
        元组 (file_path, is_safe)
        【类型】tuple
        【说明】
        - file_path: 文件系统绝对路径，如果不安全则为None
        - is_safe: 布尔值，表示路径是否安全
    """
    # 【步骤1】处理根路径
    # 当用户访问 http://localhost:8080/ 时
    # URL路径是"/"，我们需要映射到index.html
    if url_path == '/' or url_path == '':
        url_path = '/index.html'
    
    # 【步骤2】去除前导斜杠
    # URL路径以/开头（如/index.html）
    # 但文件系统路径不需要前导斜杠
    # 所以要去掉：/about.html → about.html
    if url_path.startswith('/'):
        url_path = url_path[1:]
    
    # 【步骤3】拼接文档根目录
    # 将DOC_ROOT和URL路径拼接成完整路径
    # 例如：
    # - DOC_ROOT = D:\develop\homework\webserver\www
    # - url_path = about.html
    # - 结果：D:\develop\homework\webserver\www\about.html
    file_path = os.path.join(DOC_ROOT, url_path)
    
    # 【步骤4】规范化路径
    # os.path.normpath()处理路径中的特殊成分：
    # - ..：上级目录
    # - .：当前目录
    # - 连续斜杠：合并为一个
    # 
    # 例如：
    # D:\www\article\..\about.html → D:\www\about.html
    # D:\www\.\about.html → D:\www\about.html
    file_path = os.path.normpath(file_path)
    
    # 【步骤5】解析真实路径
    # os.path.realpath()解析符号链接、快捷方式等
    # 在Windows下，这也会解析短文件名（如PROGRA~1）为长文件名
    # 在Linux下，这会解析符号链接指向的真实位置
    real_path = os.path.realpath(file_path)
    
    # 【步骤6】安全边界检查
    # 这是最关键的安全检查！
    # 确保解析后的路径仍然在DOC_ROOT目录下
    # 
    # 【startswith()方法】
    # 检查字符串是否以指定前缀开头
    # 例如："D:\www\about.html".startswith("D:\www") → True
    #      "/etc/passwd".startswith("D:\www") → False
    if not real_path.startswith(DOC_ROOT):
        # 【路径穿越攻击检测】
        # 如果真实路径不在DOC_ROOT内，说明有路径穿越企图
        # 返回(None, False)，拒绝访问
        return (None, False)
    
    # 【安全路径】
    # 所有检查通过，返回真实路径和安全标志
    return (real_path, True)


def get_mime_type(file_path: str) -> str:
    """
    根据文件扩展名返回对应的MIME类型
    
    【MIME类型的作用】
    HTTP响应头的Content-Type字段告诉浏览器如何处理响应内容。
    如果MIME类型不正确：
    - 浏览器可能无法正确显示内容
    - CSS文件不会被应用为样式表
    - 图片可能无法显示
    - 浏览器可能尝试下载而不是显示
    
    【为什么用扩展名而不是文件头？】
    - 简单快速，不需要读取文件内容
    - URL中通常包含文件扩展名
    - 适用于所有文件类型
    
    【os.path.splitext()函数】
    分离文件名和扩展名：
    - splitext("style.css") → ("style", ".css")
    - splitext("/path/to/image.png") → ("/path/to/image", ".png")
    - splitext("archive.tar.gz") → ("archive.tar", ".gz")
    
    【为什么需要.lower()？】
    操作系统对扩展名大小写不敏感：
    - Windows文件系统不区分大小写：.PNG 和 .png 相同
    - 但URL可能是任意大小写
    - .lower()统一转为小写，确保匹配
    
    参数：
        file_path: 文件的完整路径
                  【类型】str
                  【示例】D:\www\style.css
    
    返回：
        MIME类型字符串
        【类型】str
        【示例】text/css; charset=utf-8
        【说明】如果扩展名未知，返回application/octet-stream（二进制流）
    """
    # 【分离文件名和扩展名】
    # 返回元组：(不含扩展名的文件名, 扩展名)
    # 扩展名包含点号，如".html", ".css"
    _, ext = os.path.splitext(file_path)
    
    # 【查找MIME类型】
    # 从字典中查找扩展名对应的MIME类型
    # .lower()确保大小写不敏感
    # 如果找不到，使用默认值'application/octet-stream'
    # 
    # 【application/octet-stream】
    # 通用二进制流类型，浏览器通常会下载而不是显示
    # 这是合理的安全策略：不确定的文件类型就下载
    return MIME_TYPES.get(ext.lower(), 'application/octet-stream')


def read_file(file_path: str) -> tuple:
    """
    读取文件内容并返回MIME类型
    
    【函数职责】
    安全地读取服务器上的文件内容：
    1. 检查文件是否存在
    2. 检查是否为普通文件（不是目录）
    3. 以二进制模式读取内容
    4. 返回读取结果和MIME类型
    
    【为什么使用二进制模式'rb'？】
    - 网络传输使用字节，不是字符
    - 图片、压缩包等二进制文件必须用二进制模式
    - 即使是文本文件，二进制模式也避免编码问题
    
    【异常处理考虑】
    可能发生的错误：
    - FileNotFoundError：文件不存在
    - IsADirectoryError：路径是目录而非文件
    - PermissionError：没有读取权限
    - OSError：其他系统级错误
    
    【返回值设计】
    返回元组(success, content, mime_type)：
    - success：读取是否成功
    - content：文件内容（失败时为None）
    - mime_type：MIME类型（失败时为None）
    
    这种设计让调用者可以明确知道失败原因。
    
    参数：
        file_path: 要读取的文件绝对路径
                  【类型】str
                  【示例】D:\www\index.html
    
    返回：
        元组 (success, content, mime_type)
        【类型】tuple
        【说明】
        - success: 布尔值，表示读取是否成功
        - content: bytes，文件内容，失败时为None
        - mime_type: str，MIME类型，失败时为None
    """
    try:
        # 【检查1：文件是否存在】
        # os.path.exists()检查路径是否存在
        # 可以是文件或目录
        if not os.path.exists(file_path):
            # 文件不存在，返回失败
            return (False, None, None)
        
        # 【检查2：是否为普通文件】
        # os.path.isfile()检查是否为普通文件
        # 目录、符号链接、设备文件都不是普通文件
        # 请求目录时应该返回404，而不是目录列表（我们没有实现目录列表功能）
        if not os.path.isfile(file_path):
            # 路径存在但不是文件，返回失败
            return (False, None, None)
        
        # 【读取文件内容】
        # open(file_path, 'rb')：
        # - 'r'：读取模式
        # - 'b'：二进制模式（必须，用于网络传输）
        # with语句确保文件正确关闭，即使发生异常
        with open(file_path, 'rb') as f:
            # f.read()：读取整个文件内容
            # 返回bytes对象（字节串）
            content = f.read()
        
        # 【获取MIME类型】
        # 根据文件扩展名确定Content-Type
        mime_type = get_mime_type(file_path)
        
        # 【返回成功结果】
        # 所有检查通过，文件成功读取
        return (True, content, mime_type)
    
    except (IOError, PermissionError):
        # 【异常处理】
        # IOError：输入输出错误，如磁盘读取失败
        # PermissionError：权限不足，无法读取文件
        # 
        # 【处理策略】
        # 返回失败标志，让调用者决定如何响应
        # 通常会返回404或500错误页面
        return (False, None, None)
