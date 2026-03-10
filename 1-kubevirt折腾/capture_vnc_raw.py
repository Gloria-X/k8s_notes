# python3 capture_vnc_raw.py > vnc.raw
import websocket
import sys

def on_message(ws, data):
    if isinstance(data, bytes):
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
    else:
        print("Received text (unexpected):", data)

ws = websocket.WebSocketApp(
    "ws://localhost:8082/apis/subresources.kubevirt.io/v1/namespaces/ai-deliver/virtualmachineinstances/centos7/vnc",
    on_message=on_message
)
ws.run_forever()
