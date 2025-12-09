import socket
import json

HOST = '127.0.0.1'  # MCP server address
PORT = 9876         # MCP server port

# Example MCP command to add a cube at the center
command = {
    "command": "add_cube",
    "location": [0, 0, 0],
    "size": 2  # Default Blender cube size
}

# Connect to MCP server and send command
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall((json.dumps(command) + '\n').encode('utf-8'))
    # Receive response (optional, depends on MCP server implementation)
    response = s.recv(4096)
    print('Received:', response.decode('utf-8'))
