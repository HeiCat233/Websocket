"""
================================================================================
配置模块
================================================================================

【模块说明】
集中管理Web服务器的所有配置参数。

【配置来源】
- 环境变量（最高优先级）
- 配置文件（可选）
- 代码默认值（兜底）

================================================================================
"""

import os


class Settings:
    """
    服务器配置类
    
    【设计说明】
    集中管理所有配置项，支持环境变量覆盖。
    配置分类：服务器基础、并发处理、超时设置、其他。
    """
    
    def __init__(self):
        # ==================== 服务器基础配置 ====================
        
        # 监听地址：'0.0.0.0' 监听所有接口，'127.0.0.1' 仅监听本机
        self.HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
        
        # 监听端口：80(HTTP标准)、443(HTTPS)、8080(开发测试)
        self.PORT = int(os.environ.get('SERVER_PORT', '8080'))
        
        # 文档根目录：Web资源的根路径
        _default_root = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            '..', 
            'www'
        )
        self.DOCUMENT_ROOT = os.environ.get('DOCUMENT_ROOT', _default_root)
        
        # ==================== 并发处理配置 ====================
        
        # TCP连接队列大小
        self.BACKLOG = int(os.environ.get('BACKLOG', '10'))
        
        # 工作线程数量：IO密集型建议4-8，CPU密集型建议2-4
        self.THREAD_POOL_SIZE = int(os.environ.get('THREAD_POOL_SIZE', '4'))
        
        # 任务队列最大容量
        self.QUEUE_SIZE = int(os.environ.get('QUEUE_SIZE', '128'))
        
        # ==================== 超时配置 ====================
        
        # 接收缓冲区大小（字节）
        self.BUFFER_SIZE = int(os.environ.get('BUFFER_SIZE', '8192'))
        
        # 客户端连接超时（秒）
        self.CLIENT_TIMEOUT = float(os.environ.get('CLIENT_TIMEOUT', '30.0'))
        
        # Accept超时（秒）
        self.ACCEPT_TIMEOUT = float(os.environ.get('ACCEPT_TIMEOUT', '1.0'))
        
        # 队列获取任务超时（秒）
        self.QUEUE_GET_TIMEOUT = float(os.environ.get('QUEUE_GET_TIMEOUT', '1.0'))
        
        # ==================== 其他配置 ====================
        
        # 服务器标识
        self.SERVER_NAME = 'SimplePythonServer/1.0'
        
        # 默认首页
        self.DEFAULT_PAGE = 'index.html'
        
        # 缓存max-age
        self.CACHE_MAX_AGE = int(os.environ.get('CACHE_MAX_AGE', '86400'))
    
    def get_document_root(self):
        """获取文档根目录的绝对路径"""
        return os.path.abspath(self.DOCUMENT_ROOT)


# 全局配置单例
settings = Settings()
