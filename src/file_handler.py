import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
DOC_ROOT = os.path.join(_current_dir, '..', 'www')
DOC_ROOT = os.path.abspath(DOC_ROOT)

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


def resolve_path(url_path: str) -> tuple:
    if url_path == '/' or url_path == '':
        url_path = '/index.html'
    
    if url_path.startswith('/'):
        url_path = url_path[1:]
    
    file_path = os.path.join(DOC_ROOT, url_path)
    file_path = os.path.normpath(file_path)
    real_path = os.path.realpath(file_path)
    
    if not real_path.startswith(DOC_ROOT):
        return (None, False)
    
    return (real_path, True)


def get_mime_type(file_path: str) -> str:
    _, ext = os.path.splitext(file_path)
    return MIME_TYPES.get(ext.lower(), 'application/octet-stream')


def read_file(file_path: str) -> tuple:
    try:
        if not os.path.exists(file_path):
            return (False, None, None)
        
        if not os.path.isfile(file_path):
            return (False, None, None)
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mime_type = get_mime_type(file_path)
        return (True, content, mime_type)
    
    except (IOError, PermissionError):
        return (False, None, None)