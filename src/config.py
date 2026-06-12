"""
================================================================================
配置管理模块
================================================================================

【模块功能】
集中管理Web服务器的所有配置参数，包括服务器设置、路径配置、超时设置等。

【设计原则】
- 单一数据源：所有配置集中在一个地方，便于维护
- 运行时可修改：支持从配置文件或环境变量加载
- 类型安全：使用明确的类型定义
- 默认值：合理的默认值，减少配置负担

【配置来源优先级】
1. 环境变量（最优先）
2. 配置文件（可选）
3. 代码默认值（兜底）

【配置分类】
- 服务器配置：HOST、PORT等
- 路径配置：文档根目录等
- 性能配置：线程数、队列大小等
- 超时配置：连接超时、读取超时等

================================================================================
"""

import os
from typing import Optional


class ServerConfig:
    """
    服务器配置类
    
    【设计说明】
    使用类封装配置，提供默认值和类型检查。
    支持从环境变量覆盖配置，实现配置与代码分离。
    
    【使用方式】
    ```python
    config = ServerConfig()
    print(config.HOST, config.PORT)
    ```
    """
    
    def __init__(self):
        """
        初始化配置
        """
        # ==================== 服务器基础配置 ====================
        
        # 【监听地址】
        # '0.0.0.0'：监听所有网络接口（有线、无线、localhost）
        # '127.0.0.1'：仅监听本机
        # 环境变量：SERVER_HOST
        self.HOST: str = self._get_env('SERVER_HOST', '0.0.0.0')
        
        # 【监听端口】
        # 常用端口：80(HTTP)、443(HTTPS)、8080(开发测试)
        # 环境变量：SERVER_PORT
        self.PORT: int = int(self._get_env('SERVER_PORT', '8080'))
        
        # 【文档根目录】
        # Web资源的根目录，URL路径从这里开始解析
        # 环境变量：DOCUMENT_ROOT
        self.DOCUMENT_ROOT: str = self._get_env(
            'DOCUMENT_ROOT',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'www')
        )
        
        # ==================== 并发处理配置 ====================
        
        # 【TCP连接队列大小】
        # listen()函数的全连接队列长度
        # 超过此数量的连接会被客户端重试
        # 环境变量：BACKLOG
        self.BACKLOG: int = int(self._get_env('BACKLOG', '10'))
        
        # 【工作线程数量】
        # 同时处理请求的线程数
        # IO密集型：4-8个；CPU密集型：2-4个
        # 环境变量：THREAD_POOL_SIZE
        self.THREAD_POOL_SIZE: int = int(self._get_env('THREAD_POOL_SIZE', '4'))
        
        # 【任务队列容量】
        # 等待处理的请求队列最大长度
        # 超过此数量会拒绝新连接
        # 环境变量：QUEUE_SIZE
        self.QUEUE_SIZE: int = int(self._get_env('QUEUE_SIZE', '128'))
        
        # ==================== 超时配置 ====================
        
        # 【接收缓冲区大小】
        # 单次recv()最多读取的字节数
        # 对于普通HTTP请求，8KB足够
        # 环境变量：BUFFER_SIZE
        self.BUFFER_SIZE: int = int(self._get_env('BUFFER_SIZE', '8192'))
        
        # 【客户端连接超时】
        # 客户端无数据传输的最大等待时间
        # 环境变量：CLIENT_TIMEOUT
        self.CLIENT_TIMEOUT: float = float(self._get_env('CLIENT_TIMEOUT', '30.0'))
        
        # 【Accept超时】
        # server_socket.accept()的超时时间
        # 用于定期检查关闭标志
        # 环境变量：ACCEPT_TIMEOUT
        self.ACCEPT_TIMEOUT: float = float(self._get_env('ACCEPT_TIMEOUT', '1.0'))
        
        # 【工作线程获取任务超时】
        # 队列为空时的阻塞时间
        # 环境变量：QUEUE_GET_TIMEOUT
        self.QUEUE_GET_TIMEOUT: float = float(self._get_env('QUEUE_GET_TIMEOUT', '1.0'))
        
        # ==================== 其他配置 ====================
        
        # 【服务器标识】
        # HTTP响应头中的Server字段
        self.SERVER_NAME: str = 'SimplePythonServer/1.0'
        
        # 【默认首页】
        # 访问根路径时返回的文件
        self.DEFAULT_PAGE: str = 'index.html'
        
        # 【缓存配置】
        # 缓存控制：max-age秒数
        self.CACHE_MAX_AGE: int = int(self._get_env('CACHE_MAX_AGE', '86400'))
    
    @staticmethod
    def _get_env(key: str, default: str) -> str:
        """
        获取环境变量，失败时返回默认值
        
        参数：
            key: 环境变量名
            default: 默认值
        
        返回：
            环境变量值或默认值
        """
        return os.environ.get(key, default)
    
    def get_document_root(self) -> str:
        """
        获取文档根目录的绝对路径
        
        返回：
            规范化的文档根目录路径
        """
        return os.path.abspath(self.DOCUMENT_ROOT)


# 【全局配置实例】
# 单例模式，全局共享配置
config = ServerConfig()
