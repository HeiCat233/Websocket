# ============================================================================
# 文件处理模块
# 功能：处理文件系统操作，包括路径解析、安全检查、MIME类型映射、文件读取
# ============================================================================

import os

# 【确定文档根目录】
# 获取当前脚本所在目录的绝对路径（即 src/ 目录）
_current_dir = os.path.dirname(os.path.abspath(__file__))

# 拼接出 www/ 目录的绝对路径
# 例如：D:\develop\homework\webserver\www
DOC_ROOT = os.path.join(_current_dir, '..', 'www')
DOC_ROOT = os.path.abspath(DOC_ROOT)  # 转换为绝对路径，便于后续安全检查

# MIME类型映射表：根据文件扩展名返回对应的Content-Type
# 浏览器根据此头部决定如何解析和显示内容
MIME_TYPES = {
    '.html': 'text/html',                          # HTML文档
    '.htm': 'text/html',                           # HTML文档（旧式扩展名）
    '.css': 'text/css; charset=utf-8',             # CSS样式表（必须指定UTF-8）
    '.js': 'application/javascript; charset=utf-8',# JavaScript脚本（必须指定UTF-8）
    '.png': 'image/png',                           # PNG图片
    '.jpg': 'image/jpeg',                          # JPEG图片
    '.jpeg': 'image/jpeg',                         # JPEG图片（完整扩展名）
    '.gif': 'image/gif',                           # GIF图片
    '.txt': 'text/plain; charset=utf-8'            # 纯文本（必须指定UTF-8）
}


def resolve_path(url_path: str) -> tuple:
    """
    将URL路径解析为文件系统绝对路径，并进行安全检查
    
    工作流程：
    1. 处理默认首页：/ 或 空路径 → /index.html
    2. 去除开头的斜杠：/about.html → about.html
    3. 拼接完整路径：DOC_ROOT + url_path
    4. 规范化路径：处理../等特殊路径
    5. 安全检查：确保最终路径在DOC_ROOT目录下（防止路径穿越攻击）
    
    安全示例：
        /index.html → D:\...\www\index.html ✓
        /article/post1.html → D:\...\www\article\post1.html ✓
    
    危险示例（会被拦截）：
        /../../etc/passwd → 超出DOC_ROOT范围，返回(None, False) ✗
        /..\\..\\windows\system32 → 路径穿越，返回(None, False) ✗
    
    参数：
        url_path: URL中的路径部分（如/index.html、/article/post1.html）
    
    返回：
        元组 (file_path, is_safe)：
        - file_path: 文件系统绝对路径，如果不安全则为None
        - is_safe: 布尔值，表示路径是否安全
    """
    # 【步骤1】处理默认首页：访问根路径时返回index.html
    if url_path == '/' or url_path == '':
        url_path = '/index.html'
    
    # 【步骤2】去除开头的斜杠，以便与DOC_ROOT拼接
    # 例如：/about.html → about.html
    if url_path.startswith('/'):
        url_path = url_path[1:]
    
    # 【步骤3】拼接完整路径
    # 例如：DOC_ROOT="D:\...\www", url_path="about.html"
    # 结果：file_path="D:\...\www\about.html"
    file_path = os.path.join(DOC_ROOT, url_path)
    
    # 【步骤4】规范化路径：处理/../等特殊路径
    # 例如：D:\...\www\article\..\about.html → D:\...\www\about.html
    file_path = os.path.normpath(file_path)
    
    # 【步骤5】获取真实路径：解析符号链接等（Windows下通常与normpath相同）
    real_path = os.path.realpath(file_path)
    
    # 【步骤6】安全检查：确保解析后的路径仍在DOC_ROOT目录下
    # 这是防止路径穿越攻击的关键检查！
    if not real_path.startswith(DOC_ROOT):
        # 路径超出允许范围，拒绝访问
        return (None, False)
    
    # 路径安全，返回绝对路径
    return (real_path, True)


def get_mime_type(file_path: str) -> str:
    """
    根据文件扩展名返回对应的MIME类型
    
    MIME类型用于HTTP响应头的Content-Type字段，告诉浏览器如何解析内容
    
    参数：
        file_path: 文件的完整路径（如D:\...\www\style.css）
    
    返回：
        MIME类型字符串（如'text/css; charset=utf-8'）
        如果扩展名未知，返回'application/octet-stream'（二进制流）
    """
    # 分离文件名和扩展名，提取扩展名（含点号）
    # 例如：style.css → ('style', '.css')
    _, ext = os.path.splitext(file_path)
    
    # 从字典中查找MIME类型，找不到则返回默认值
    # .lower()确保大小写不敏感（.CSS和.css都能匹配）
    return MIME_TYPES.get(ext.lower(), 'application/octet-stream')


def read_file(file_path: str) -> tuple:
    """
    读取文件内容并返回MIME类型
    
    参数：
        file_path: 要读取的文件绝对路径
    
    返回：
        元组 (success, content, mime_type)：
        - success: 布尔值，表示读取是否成功
        - content: 文件内容（字节串），失败时为None
        - mime_type: MIME类型字符串，失败时为None
    """
    try:
        # 【检查1】验证文件是否存在
        if not os.path.exists(file_path):
            return (False, None, None)
        
        # 【检查2】验证是否为普通文件（而非目录）
        if not os.path.isfile(file_path):
            return (False, None, None)
        
        # 【读取文件】以二进制模式读取全部内容
        # 使用'rb'模式：
        # - 避免文本模式下的编码转换问题
        # - 支持所有文件类型（HTML/CSS/图片等）
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 根据文件扩展名获取MIME类型
        mime_type = get_mime_type(file_path)
        
        # 返回成功标志、文件内容和MIME类型
        return (True, content, mime_type)
    
    except (IOError, PermissionError):
        # 捕获IO错误（如磁盘故障、权限不足）
        # 返回失败标志，调用方会返回404或500错误
        return (False, None, None)