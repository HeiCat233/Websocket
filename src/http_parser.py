class HTTPRequest:
    def __init__(self):
        self.method = ""
        self.path = ""
        self.version = ""
        self.raw_data = b""


def url_decode(url_string: str) -> str:
    result = []
    i = 0
    while i < len(url_string):
        if url_string[i] == '%' and i + 2 < len(url_string):
            try:
                hex_value = url_string[i+1:i+3]
                result.append(chr(int(hex_value, 16)))
                i += 3
            except ValueError:
                result.append(url_string[i])
                i += 1
        elif url_string[i] == '+':
            result.append(' ')
            i += 1
        else:
            result.append(url_string[i])
            i += 1
    return ''.join(result)


def parse_request(raw_data: bytes) -> HTTPRequest:
    request = HTTPRequest()
    request.raw_data = raw_data
    
    if not raw_data:
        return request
    
    try:
        data_str = raw_data.decode('utf-8')
        lines = data_str.split('\r\n')
        
        if lines:
            request_line = lines[0]
            parts = request_line.split(' ')
            
            if len(parts) >= 1:
                request.method = parts[0]
            if len(parts) >= 2:
                request.path = url_decode(parts[1])
            if len(parts) >= 3:
                request.version = parts[2]
    
    except Exception:
        pass
    
    return request