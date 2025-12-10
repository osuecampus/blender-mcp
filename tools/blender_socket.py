"""
Blender Socket - Minimal Socket Communication Utility

A standalone utility for communicating with the BlenderMCP addon via socket.
This module has NO dependencies on other tools modules, making it resilient
to import failures elsewhere in the package.

Usage:
    from tools.blender_socket import send_code, send_command, get_scene_info
    
    # Execute Python code in Blender
    result = send_code('''
        import bpy
        bpy.ops.mesh.primitive_cube_add()
        print("Cube created!")
    ''')
    
    # Send a specific command
    result = send_command('get_scene_info')
    
    # Convenience function for scene info
    info = get_scene_info()
"""

import socket
import json
from typing import Any, Dict, Optional

# Default connection settings
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 30


def _send_message(message: dict, host: str = DEFAULT_HOST, 
                  port: int = DEFAULT_PORT, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Send a message to Blender and return the response.
    
    Args:
        message: Dictionary to send as JSON
        host: Blender addon host (default: localhost)
        port: Blender addon port (default: 9876)
        timeout: Socket timeout in seconds (default: 30)
    
    Returns:
        Response dictionary from Blender
    
    Raises:
        ConnectionRefusedError: If Blender addon is not running
        TimeoutError: If response takes too long
        json.JSONDecodeError: If response is not valid JSON
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((host, port))
        sock.sendall(json.dumps(message).encode('utf-8'))
        
        # Accumulate response chunks until valid JSON
        response = b''
        while True:
            try:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                response += chunk
                # Try to parse - if successful, we have complete response
                try:
                    return json.loads(response.decode('utf-8'))
                except json.JSONDecodeError:
                    continue  # Wait for more data
            except socket.timeout:
                raise TimeoutError(f"Blender response timeout after {timeout}s")
    finally:
        sock.close()
    
    # If we exit the loop without returning, try to parse what we have
    if response:
        return json.loads(response.decode('utf-8'))
    raise ConnectionError("No response received from Blender")


def send_code(code: str, host: str = DEFAULT_HOST, 
              port: int = DEFAULT_PORT, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Execute Python code in Blender.
    
    Args:
        code: Python code to execute in Blender
        host: Blender addon host
        port: Blender addon port
        timeout: Socket timeout in seconds
    
    Returns:
        Response dict with 'status' ('success' or 'error') and 'result' or 'message'
    
    Example:
        result = send_code('''
            import bpy
            obj = bpy.context.active_object
            print(f"Active: {obj.name if obj else 'None'}")
        ''')
        print(result['result'])
    """
    message = {
        'type': 'execute_code',
        'params': {'code': code}
    }
    return _send_message(message, host, port, timeout)


def send_command(command_type: str, params: Optional[Dict[str, Any]] = None,
                 host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Send a command to Blender.
    
    Args:
        command_type: The command type (e.g., 'get_scene_info', 'get_object_info')
        params: Optional parameters for the command
        host: Blender addon host
        port: Blender addon port
        timeout: Socket timeout in seconds
    
    Returns:
        Response dict with 'status' and 'result' or 'message'
    
    Available command types:
        Scene: get_scene_info, get_object_info, get_selection, set_selection
        Materials: list_materials, get_material_nodes
        Geometry Nodes: get_node_details, get_node_links, set_geonode_parameter,
                       create_geonode_node, create_geonode_link, etc.
        Assets: search_polyhaven_assets, search_sketchfab_models (if enabled)
    
    Example:
        result = send_command('get_object_info', {'name': 'Cube'})
        print(result['result'])
    """
    message = {
        'type': command_type,
        'params': params or {}
    }
    return _send_message(message, host, port, timeout)


def get_scene_info(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict:
    """
    Convenience function to get scene information.
    
    Returns:
        Scene info dict with 'name', 'object_count', 'objects', etc.
    """
    result = send_command('get_scene_info', host=host, port=port)
    if result.get('status') == 'success':
        return result['result']
    raise RuntimeError(result.get('message', 'Failed to get scene info'))


def list_materials(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict:
    """
    Convenience function to list all materials.
    
    Returns:
        Materials dict with 'material_count' and 'materials' list
    """
    result = send_command('list_materials', host=host, port=port)
    if result.get('status') == 'success':
        return result['result']
    raise RuntimeError(result.get('message', 'Failed to list materials'))


def is_blender_connected(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """
    Check if Blender addon is running and accepting connections.
    
    Returns:
        True if connected, False otherwise
    """
    try:
        get_scene_info(host, port)
        return True
    except (ConnectionRefusedError, ConnectionError, TimeoutError):
        return False


# Quick test when run directly
if __name__ == '__main__':
    print("Testing Blender socket connection...")
    
    if is_blender_connected():
        print("✓ Connected to Blender")
        
        info = get_scene_info()
        print(f"  Scene: {info.get('name')}")
        print(f"  Objects: {info.get('object_count')}")
        
        mats = list_materials()
        print(f"  Materials: {mats.get('material_count')}")
    else:
        print("✗ Cannot connect to Blender")
        print("  Make sure the BlenderMCP addon is running on port 9876")
