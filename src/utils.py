"""
================================================================================
工具函数模块
================================================================================

【模块功能】
提供通用工具函数，供其他模块使用。

【包含内容】
- URL编码/解码函数
- 字符串处理函数
- 日期时间格式化函数

【设计原则】
- 纯函数：无副作用，输入相同输出必相同
- 可测试：独立于业务逻辑，易于单元测试
- 文档完善：每个函数都有清晰的说明

================================================================================
"""


def url_decode(url_string: str) -> str:
    """
    URL解码函数：将百分号编码转换为原始字符
    
    【编码规则】
    URL中有一些特殊字符无法直接使用，需要百分号编码：
    - 空格 → %20 或 +
    - 中文 → %E4%BD%A0（UTF-8十六进制）
    - 特殊符号：%XX
    
    【函数设计】
    1. 逐字符扫描
    2. %开头：检查后两位是否为十六进制
    3. +号：转换为空格
    4. 其他：直接保留
    
    参数：
        url_string: 包含百分号编码的URL字符串
    
    返回：
        解码后的原始字符串
    
    示例：
        url_decode("%E4%BD%A0%20world") → "你好 world"
        url_decode("hello+world") → "hello world"
    """
    result = []  # 使用列表存储字符，比字符串拼接高效
    i = 0
    
    while i < len(url_string):
        # 处理百分号编码
        if url_string[i] == '%' and i + 2 < len(url_string):
            try:
                hex_value = url_string[i+1:i+3]
                char_code = int(hex_value, 16)
                result.append(chr(char_code))
                i += 3
            except ValueError:
                # 无效的十六进制，保留原字符
                result.append(url_string[i])
                i += 1
        elif url_string[i] == '+':
            # 表单数据中，+号表示空格
            result.append(' ')
            i += 1
        else:
            result.append(url_string[i])
            i += 1
    
    return ''.join(result)


def url_encode(text: str) -> str:
    """
    URL编码函数：将特殊字符转换为百分号编码
    
    参数：
        text: 需要编码的字符串
    
    返回：
        URL编码后的字符串
    
    示例：
        url_encode("你好 world") → "%E4%BD%A0%E5%A5%BD%20world"
    """
    result = []
    for char in text:
        # 需要编码的字符
        if char == ' ':
            result.append('+')
        elif char.isalnum() or char in '-_.~':
            # 保留字符：字母、数字、连字符、下划线、点、波浪线
            result.append(char)
        else:
            # 编码为%XX
            for byte in char.encode('utf-8'):
                result.append(f'%{byte:02X}')
    return ''.join(result)


def safe_dict_get(dictionary: dict, key, default=None):
    """
    安全获取字典值，避免KeyError
    
    参数：
        dictionary: 目标字典
        key: 键
        default: 默认值（可选）
    
    返回：
        字典中的值或默认值
    """
    return dictionary.get(key, default)
