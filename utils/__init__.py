"""
================================================================================
工具函数模块
================================================================================

【模块说明】
提供通用工具函数，供其他模块使用。

【包含内容】
- URL编码/解码函数
- 字符串处理函数
- 字典安全访问函数

================================================================================
"""


def url_decode(url_string):
    """
    URL解码：将百分号编码转换为原始字符
    
    【编码规则】
    - %XX：十六进制编码的字符
    - +：空格（表单数据中常用）
    
    参数：
        url_string: 待解码的URL字符串
    
    返回：
        解码后的字符串
    
    示例：
        url_decode("%E4%BD%A0%20world") → "你好 world"
        url_decode("hello+world") → "hello world"
    """
    result = []
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


def url_encode(text):
    """
    URL编码：将特殊字符转换为百分号编码
    
    参数：
        text: 待编码的字符串
    
    返回：
        编码后的URL字符串
    """
    result = []
    for char in text:
        if char == ' ':
            result.append('+')
        elif char.isalnum() or char in '-_.~':
            # 保留字符
            result.append(char)
        else:
            # 编码为%XX
            for byte in char.encode('utf-8'):
                result.append(f'%{byte:02X}')
    return ''.join(result)


def safe_dict_get(dictionary, key, default=None):
    """
    安全获取字典值
    
    参数：
        dictionary: 目标字典
        key: 键
        default: 默认值
    
    返回：
        字典中的值或默认值
    """
    return dictionary.get(key, default)
