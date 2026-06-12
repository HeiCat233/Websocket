"""
================================================================================
Web服务器包初始化模块
================================================================================

【包说明】
本包包含Python Web服务器的完整实现。

【模块结构】
- config: 配置管理
- utils: 工具函数
- request: 请求处理
- response: 响应生成
- storage: 文件处理（数据访问）
- middleware: 中间件
- router: 路由管理
- server: 服务器核心
- main: 程序入口

【使用示例】
```python
from src.server import create_server

server = create_server()
server.start()
```
"""

from .config import config
from .server import WebServer, create_server

__all__ = ['config', 'WebServer', 'create_server']
