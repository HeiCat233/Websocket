"""
================================================================================
数据访问模块
================================================================================

【模块功能】
处理所有文件系统操作，包括路径解析、安全检查、文件读取等。

【模块职责】
1. 路径解析和规范化
2. 安全检查（防止路径穿越）
3. MIME类型映射
4. 文件读取

【设计原则】
- 数据访问分离：只负责数据读写，不处理业务逻辑
- 安全第一：严格的路径安全检查
- 防御性编程：处理各种异常情况

【安全说明】
路径穿越攻击是Web服务器的主要安全威胁。
攻击者通过构造特殊的URL访问Web目录之外的文件。
本模块实现了多层次的安全检查。

================================================================================
"""

import os
from typing import Optional, Tuple
from .config import config


# MIME类型映射表
MIME_TYPES = {
    '.html': 'text/html',
    '.htm': 'text/html',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.txt': 'text/plain; charset=utf-8'
}


class PathResolver:
    """
    路径解析器
    
    【职责】
    将URL路径转换为文件系统路径，并进行安全检查。
    
    【处理流程】
    1. 处理默认首页
    2. 去除前导斜杠
    3. 拼接文档根目录
    4. 规范化路径
    5. 安全边界检查
    """
    
    def __init__(self, document_root: Optional[str] = None):
        """
        初始化路径解析器
        
        参数：
            document_root: 文档根目录（可选，默认使用配置中的）
        """
        self.document_root = document_root or config.get_document_root()
    
    def resolve(self, url_path: str) -> Tuple[str, bool]:
        """
        解析URL路径
        
        参数：
            url_path: URL路径（如/index.html）
        
        返回：
            元组 (file_path, is_safe)
            - file_path: 文件系统绝对路径，不安全则为None
            - is_safe: 是否安全
        """
        # 处理根路径
        if url_path == '/' or url_path == '':
            url_path = f'/{config.DEFAULT_PAGE}'
        
        # 去除前导斜杠
        if url_path.startswith('/'):
            url_path = url_path[1:]
        
        # 拼接完整路径
        file_path = os.path.join(self.document_root, url_path)
        
        # 规范化路径
        file_path = os.path.normpath(file_path)
        
        # 解析真实路径
        real_path = os.path.realpath(file_path)
        
        # 安全边界检查
        if not real_path.startswith(os.path.realpath(self.document_root)):
            return (None, False)
        
        return (real_path, True)
    
    def is_safe_path(self, file_path: str) -> bool:
        """
        检查路径是否安全
        
        参数：
            file_path: 文件系统路径
        
        返回：
            True表示安全，False表示不安全
        """
        real_path = os.path.realpath(file_path)
        return real_path.startswith(os.path.realpath(self.document_root))


class FileHandler:
    """
    文件处理器
    
    【职责】
    读取服务器上的文件内容。
    
    【文件读取流程】
    1. 检查文件是否存在
    2. 检查是否为普通文件
    3. 读取文件内容
    4. 返回内容和MIME类型
    """
    
    def __init__(self):
        """
        初始化文件处理器
        """
        self.path_resolver = PathResolver()
    
    def read(self, url_path: str) -> Tuple[bool, bytes, str, int]:
        """
        读取文件
        
        参数：
            url_path: URL路径
        
        返回：
            元组 (success, content, mime_type, status_code)
            - success: 是否成功
            - content: 文件内容（失败为None）
            - mime_type: MIME类型
            - status_code: HTTP状态码
        """
        # 解析路径
        file_path, is_safe = self.path_resolver.resolve(url_path)
        
        # 检查安全性
        if not is_safe or file_path is None:
            return (False, None, None, 403)
        
        # 读取文件
        return self._read_file(file_path)
    
    def _read_file(self, file_path: str) -> Tuple[bool, bytes, str, int]:
        """
        内部方法：读取文件
        
        参数：
            file_path: 文件系统路径
        
        返回：
            元组 (success, content, mime_type, status_code)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return (False, None, None, 404)
            
            # 检查是否为普通文件
            if not os.path.isfile(file_path):
                return (False, None, None, 404)
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 获取MIME类型
            mime_type = self.get_mime_type(file_path)
            
            return (True, content, mime_type, 200)
        
        except (IOError, PermissionError):
            return (False, None, None, 500)
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """
        获取文件MIME类型
        
        参数：
            file_path: 文件路径
        
        返回：
            MIME类型字符串
        """
        _, ext = os.path.splitext(file_path)
        return MIME_TYPES.get(ext.lower(), 'application/octet-stream')


def get_mime_type(file_path: str) -> str:
    """
    快捷获取文件MIME类型
    
    参数：
        file_path: 文件路径
    
    返回：
        MIME类型字符串
    """
    return FileHandler.get_mime_type(file_path)
