import socket
import threading
import queue
import os
import sys
import signal

from http_parser import parse_request
from http_response import build_response, build_error_response
from file_handler import resolve_path, read_file

HOST = '0.0.0.0'
PORT = 8080
BACKLOG = 10
THREAD_POOL_SIZE = 4
QUEUE_SIZE = 128
BUFFER_SIZE = 8192

shutdown_flag = threading.Event()
server_socket = None


def handle_client(client_socket, client_address):
    thread_id = threading.current_thread().ident
    status_code = 500
    status_phrase = "Internal Server Error"
    response_bytes = 0
    
    try:
        client_socket.settimeout(30.0)
        raw_data = client_socket.recv(BUFFER_SIZE)
        
        if not raw_data:
            response = build_error_response(400)
            client_socket.sendall(response)
            return
        
        request = parse_request(raw_data)
        
        if request.method != 'GET':
            response = build_error_response(405)
            client_socket.sendall(response)
            status_code = 405
            status_phrase = "Method Not Allowed"
            response_bytes = len(response)
            return
        
        file_path, is_safe = resolve_path(request.path)
        
        if not is_safe or file_path is None:
            response = build_error_response(403)
            client_socket.sendall(response)
            status_code = 403
            status_phrase = "Forbidden"
            response_bytes = len(response)
            return
        
        success, content, mime_type = read_file(file_path)
        
        if success and content is not None:
            response = build_response(200, mime_type, content)
            client_socket.sendall(response)
            status_code = 200
            status_phrase = "OK"
            response_bytes = len(response)
        else:
            response = build_error_response(404)
            client_socket.sendall(response)
            status_code = 404
            status_phrase = "Not Found"
            response_bytes = len(response)
    
    except socket.timeout:
        response = build_error_response(408)
        client_socket.sendall(response)
        status_code = 408
        status_phrase = "Request Timeout"
        response_bytes = len(response)
    except Exception as e:
        response = build_error_response(500)
        client_socket.sendall(response)
        status_code = 500
        status_phrase = "Internal Server Error"
        response_bytes = len(response)
    finally:
        print(f"[Thread-{thread_id}] GET {request.path if 'request' in dir() else '/'} → {status_code} {status_phrase} ({response_bytes} bytes)")
        client_socket.close()


def worker_thread(task_queue):
    while not shutdown_flag.is_set():
        try:
            client_socket, client_address = task_queue.get(timeout=1)
            
            if client_socket is None and client_address is None:
                break
            
            handle_client(client_socket, client_address)
            task_queue.task_done()
        except queue.Empty:
            continue


def signal_handler(signum, frame):
    print("\n收到关闭信号，正在优雅关闭服务器...")
    shutdown_flag.set()
    
    if server_socket:
        try:
            server_socket.close()
        except Exception:
            pass


def main():
    global server_socket
    
    signal.signal(signal.SIGINT, signal_handler)
    
    task_queue = queue.Queue(QUEUE_SIZE)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
    except Exception as e:
        print(f"绑定端口失败: {e}")
        sys.exit(1)
    
    server_socket.listen(BACKLOG)
    server_socket.settimeout(1.0)
    
    doc_root = os.path.join(os.path.dirname(__file__), '..', 'www')
    doc_root = os.path.abspath(doc_root)
    
    print(f"服务器已启动，监听 http://{HOST}:{PORT}")
    print(f"文档根目录: {doc_root}")
    print(f"工作线程数: {THREAD_POOL_SIZE}")
    print("按 Ctrl+C 停止服务器")
    
    threads = []
    for _ in range(THREAD_POOL_SIZE):
        t = threading.Thread(target=worker_thread, args=(task_queue,))
        t.daemon = True
        t.start()
        threads.append(t)
    
    while not shutdown_flag.is_set():
        try:
            client_socket, client_address = server_socket.accept()
            
            try:
                task_queue.put((client_socket, client_address), block=False)
            except queue.Full:
                client_socket.close()
                print(f"请求队列已满，拒绝连接: {client_address}")
        
        except socket.timeout:
            continue
        except OSError:
            break
    
    print("等待工作线程完成...")
    for _ in range(THREAD_POOL_SIZE):
        task_queue.put((None, None))
    
    for t in threads:
        t.join(timeout=5)
    
    print("服务器已关闭")


if __name__ == '__main__':
    main()