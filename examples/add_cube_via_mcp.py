import socket
import json

HOST = '127.0.0.1'  # MCP server address
PORT = 9876         # MCP server port

# Command to execute Python code in Blender to add a cube at the center
command = {
    "type": "execute_code",
    "params": {
        "code": "bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))"
    }
}

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(json.dumps(command).encode('utf-8'))
    response = s.recv(4096)
    print('Received:', response.decode('utf-8'))
