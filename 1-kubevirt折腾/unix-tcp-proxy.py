#!/usr/bin/env python3
"""
Unix Socket ↔ TCP 双向代理 + 流量记录
用法:
    python3 unix-tcp-proxy.py --tcp-port 8083 --unix-sock /var/run/docker.sock --log-file docker-traffic.log
"""

import socket
import threading
import argparse
import os
import sys
from datetime import datetime

def log_message(log_file, direction, data):
    """记录一条消息到日志（带时间戳和方向）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    hex_data = data.hex()
    # 截断太长的数据
    if len(hex_data) > 256:
        hex_data = hex_data[:256] + "..."
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {direction} ({len(data)} bytes): {hex_data}\n")

def forward_tcp_to_unix(tcp_conn, unix_sock, log_file):
    """从 TCP 客户端读取 → 写入 Unix Socket"""
    try:
        while True:
            data = tcp_conn.recv(4096)
            if not data:
                break
            log_message(log_file, ">>> TCP -> UNIX", data)
            unix_sock.sendall(data)
    except Exception as e:
        pass  # 连接已断开是正常的
    finally:
        tcp_conn.close()
        unix_sock.close()

def forward_unix_to_tcp(unix_sock, tcp_conn, log_file):
    """从 Unix Socket 读取 → 写入 TCP 客户端"""
    try:
        while True:
            data = unix_sock.recv(4096)
            if not data:
                break
            log_message(log_file, "<<< UNIX -> TCP", data)
            tcp_conn.sendall(data)
    except Exception as e:
        pass
    finally:
        tcp_conn.close()
        unix_sock.close()

def handle_client(tcp_conn, client_addr, unix_socket_path, log_file):
    """处理一个 TCP 客户端连接"""
    try:
        # 连接到 Unix Socket
        unix_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        unix_sock.connect(unix_socket_path)

        # 启动两个线程进行双向转发
        t1 = threading.Thread(
            target=forward_tcp_to_unix,
            args=(tcp_conn, unix_sock, log_file),
            daemon=True
        )
        t2 = threading.Thread(
            target=forward_unix_to_tcp,
            args=(unix_sock, tcp_conn, log_file),
            daemon=True
        )
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        tcp_conn.close()

def main():
    parser = argparse.ArgumentParser(description="TCP ↔ Unix Socket 代理 + 抓包")
    parser.add_argument("--tcp-port", type=int, required=True, help="监听的 TCP 端口")
    parser.add_argument("--unix-sock", required=True, help="目标 Unix Socket 路径")
    parser.add_argument("--log-file", default="traffic.log", help="日志文件路径 (默认: traffic.log)")

    args = parser.parse_args()

    # 检查 Unix Socket 是否存在
    if not os.path.exists(args.unix_sock):
        print(f"❌ 错误: Unix Socket 不存在: {args.unix_sock}")
        sys.exit(1)
    if not os.access(args.unix_sock, os.R_OK | os.W_OK):
        print(f"❌ 错误: 没有权限访问: {args.unix_sock}（尝试加 sudo）")
        sys.exit(1)

    # 创建 TCP 服务器
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # server_sock.bind(("127.0.0.1", args.tcp_port))
    server_sock.bind(("0.0.0.0", args.tcp_port))
    server_sock.listen(5)

    print(f"✅ 代理启动成功!")
    print(f"   TCP 监听: 0.0.0.0:{args.tcp_port}")
    print(f"   Unix Socket: {args.unix_sock}")
    print(f"   日志文件: {os.path.abspath(args.log_file)}")
    print(f"   按 Ctrl+C 停止\n")

    try:
        while True:
            tcp_conn, addr = server_sock.accept()
            threading.Thread(
                target=handle_client,
                args=(tcp_conn, addr, args.unix_sock, args.log_file),
                daemon=True
            ).start()
    except KeyboardInterrupt:
        print("\n⏹️  正在关闭代理...")
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()