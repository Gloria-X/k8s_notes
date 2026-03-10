#!/usr/bin/env python3
# vnc-ws-proxy.py
import socket
import threading
import websocket
import sys
import os

def log(msg):
    with open(log_file, "a") as f:
        f.write(msg + "\n")

def forward_client_to_ws(client_sock, ws):
    """从 RealVNC 客户端读取数据 → 发送给 WebSocket"""
    try:
        while True:
            data = client_sock.recv(4096)
            if not data:
                break
            log(f">>> CLIENT -> WS ({len(data)} bytes): {data[:32].hex()}")
            ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY) # 转发给kubevirt
    except Exception as e:
        log(f"Client->WS error: {e}")
    finally:
        client_sock.close()
        ws.close()

def forward_ws_to_client(ws, client_sock):
    """从 WebSocket 读取数据 → 发送给 RealVNC 客户端"""
    try:
        while True:
            data = ws.recv()
            if isinstance(data, str):
                data = data.encode('utf-8', errors='ignore') # 理论上不该收到文本
            if not data:
                break
            log(f"<<< WS -> CLIENT ({len(data)} bytes): {data[:32].hex()}")
            client_sock.send(data) # 转发给realvnc
    except Exception as e:
        log(f"WS->Client error: {e}")
    finally:
        client_sock.close()
        ws.close()

def handle_client(client_sock, addr):
    log(f"New connection from {addr}")
    try:
        # 连接到 KubeVirt WebSocket
        ws_url = f"ws://{k8s_proxy_host}:{k8s_proxy_port}{vnc_ws_path}"
        ws = websocket.create_connection(ws_url, timeout=30)
        log("Connected to KubeVirt WebSocket")

        # 启动两个线程
        t1 = threading.Thread(target=forward_client_to_ws, args=(client_sock, ws))
        t2 = threading.Thread(target=forward_ws_to_client, args=(ws, client_sock))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        log(f"Proxy error: {e}")
        client_sock.close()

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", listen_port))
    server_sock.listen(5)
    log(f"VNC WebSocket proxy listening on :{listen_port}")

    try:
        while True:
            client_sock, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(client_sock, addr)).start()
    except KeyboardInterrupt:
        log("Shutting down...")
    finally:
        server_sock.close()

if __name__ == "__main__":
    listen_port = 46655
    k8s_proxy_host = "127.0.0.1"
    k8s_proxy_port = 8082
    vnc_ws_path = "/apis/subresources.kubevirt.io/v1/namespaces/ai-deliver/virtualmachineinstances/centos7/vnc"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(current_dir, "vnc-traffic.log")

    main()
