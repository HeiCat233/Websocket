"""
================================================================================
文件服务模块
================================================================================

【模块说明】
处理所有文件系统操作。

【服务内容】
- PathResolver 类：路径解析与安全检查
- FileService 类：文件读取服务
- get_mime_type 函数：获取MIME类型

【安全说明】
路径穿越攻击是Web服务器的主要安全威胁。
本模块实现了多层次的安全检查。

================================================================================
"""

import os
from config import settings


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
    
    def __init__(self, document_root=None):
        self.document_root = document_root or settings.get_document_root()
    
    def resolve(self, url_path):
        """
        解析URL路径
        
        参数：
            url_path: URL路径（如/index.html）
        
        返回：
            元组 (file_path, is_safe)
        """
        # 处理根路径
        if url_path == '/' or url_path == '':
            url_path = f'/{settings.DEFAULT_PAGE}'
        
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
        doc_root_real = os.path.realpath(self.document_root)
        if not real_path.startswith(doc_root_real):
            return (None, False)
        
        return (real_path, True)
    
    def is_safe_path(self, file_path):
        """检查路径是否安全"""
        real_path = os.path.realpath(file_path)
        doc_root_real = os.path.realpath(self.document_root)
        return real_path.startswith(doc_root_real)


class FileService:
    """
    文件服务
    
    【职责】
    读取服务器上的文件内容。
    
    【读取流程】
    1. 解析文件路径
    2. 检查路径安全性
    3. 读取文件内容
    4. 返回内容和MIME类型
    """
    
    def __init__(self):
        self.path_resolver = PathResolver()
    
    def read(self, url_path):
        """
        读取文件
        
        参数：
            url_path: URL路径
        
        返回：
            元组 (success, content, mime_type, status_code)
        """
        file_path, is_safe = self.path_resolver.resolve(url_path)
        
        if not is_safe or file_path is None:
            return (False, None, None, 403)
        
        return self._read_file(file_path)
    
    def _read_file(self, file_path):
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
            mime_type = get_mime_type(file_path)
            
            return (True, content, mime_type, 200)
        
        except (IOError, PermissionError):
            return (False, None, None, 500)
    
    @staticmethod
    def get_mime_type(file_path):
        """
        获取文件MIME类型
        
        参数：
            file_path: 文件路径
        
        返回：
            MIME类型字符串
        """
        _, ext = os.path.splitext(file_path)
        return MIME_TYPES.get(ext.lower(), 'application/octet-stream')


def get_mime_type(file_path):
    """
    快捷获取文件MIME类型
    
    参数：
        file_path: 文件路径
    
    返回：
        MIME类型字符串
    """
    return FileService.get_mime_type(file_path)
