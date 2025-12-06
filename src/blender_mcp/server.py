# blender_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import socket
import json
import asyncio
import logging
import tempfile
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
import os
from pathlib import Path
import base64
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlenderMCPServer")

# Default configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876

@dataclass
class BlenderConnection:
    host: str
    port: int
    sock: socket.socket = None  # Changed from 'socket' to 'sock' to avoid naming conflict
    
    def connect(self) -> bool:
        """Connect to the Blender addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Blender at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blender: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Blender addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Blender: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        # Use a consistent timeout value that matches the addon's timeout
        sock.settimeout(15.0)  # Match the addon's timeout
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        # If we get an empty chunk, the connection might be closed
                        if not chunks:  # If we haven't received anything yet, this is an error
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        # If we get here, it parsed successfully
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    # If we hit a timeout during receiving, break the loop and try to use what we have
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise  # Re-raise to be handled by the caller
        except socket.timeout:
            logger.warning("Socket timeout during chunked receive")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        # Try to use what we have
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                # Try to parse what we have
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                # If we can't parse it, it's incomplete
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Blender and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Blender")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # Log the command being sent
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # Set a timeout for receiving - use the same timeout as in receive_full_response
            self.sock.settimeout(15.0)  # Match the addon's timeout
            
            # Receive the response using the improved receive_full_response method
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Blender error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Blender"))
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Blender")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            # Just invalidate the current socket so it will be recreated next time
            self.sock = None
            raise Exception("Timeout waiting for Blender response - try simplifying your request")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Blender lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Blender: {str(e)}")
            # Try to log what was received
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            raise Exception(f"Invalid response from Blender: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Blender: {str(e)}")
            # Don't try to reconnect here - let the get_blender_connection handle reconnection
            self.sock = None
            raise Exception(f"Communication error with Blender: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    # We don't need to create a connection here since we're using the global connection
    # for resources and tools
    
    try:
        # Just log that we're starting up
        logger.info("BlenderMCP server starting up")
        
        # Try to connect to Blender on startup to verify it's available
        try:
            # This will initialize the global connection if needed
            blender = get_blender_connection()
            logger.info("Successfully connected to Blender on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Blender on startup: {str(e)}")
            logger.warning("Make sure the Blender addon is running before using Blender resources or tools")
        
        # Return an empty context - we're using the global connection
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _blender_connection
        if _blender_connection:
            logger.info("Disconnecting from Blender on shutdown")
            _blender_connection.disconnect()
            _blender_connection = None
        logger.info("BlenderMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "BlenderMCP",
    lifespan=server_lifespan
)

# Resource endpoints

# Global connection for resources (since resources can't access context)
_blender_connection = None
_polyhaven_enabled = False  # Add this global variable

def get_blender_connection():
    """Get or create a persistent Blender connection"""
    global _blender_connection, _polyhaven_enabled  # Add _polyhaven_enabled to globals
    
    # If we have an existing connection, check if it's still valid
    if _blender_connection is not None:
        try:
            # First check if PolyHaven is enabled by sending a ping command
            result = _blender_connection.send_command("get_polyhaven_status")
            # Store the PolyHaven status globally
            _polyhaven_enabled = result.get("enabled", False)
            return _blender_connection
        except Exception as e:
            # Connection is dead, close it and create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _blender_connection.disconnect()
            except:
                pass
            _blender_connection = None
    
    # Create a new connection if needed
    if _blender_connection is None:
        host = os.getenv("BLENDER_HOST", DEFAULT_HOST)
        port = int(os.getenv("BLENDER_PORT", DEFAULT_PORT))
        _blender_connection = BlenderConnection(host=host, port=port)
        if not _blender_connection.connect():
            logger.error("Failed to connect to Blender")
            _blender_connection = None
            raise Exception("Could not connect to Blender. Make sure the Blender addon is running.")
        logger.info("Created new persistent connection to Blender")
    
    return _blender_connection


@mcp.tool()
def get_scene_info(ctx: Context) -> str:
    """Get detailed information about the current Blender scene"""
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_scene_info")
        
        # Just return the JSON representation of what Blender sent us
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene info from Blender: {str(e)}")
        return f"Error getting scene info: {str(e)}"

@mcp.tool()
def get_object_info(ctx: Context, object_name: str) -> str:
    """
    Get detailed information about a specific object in the Blender scene.
    
    Parameters:
    - object_name: The name of the object to get information about
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_object_info", {"name": object_name})
        
        # Just return the JSON representation of what Blender sent us
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting object info from Blender: {str(e)}")
        return f"Error getting object info: {str(e)}"

@mcp.tool()
def get_viewport_screenshot(ctx: Context, max_size: int = 800) -> Image:
    """
    Capture a screenshot of the current Blender 3D viewport.
    
    Parameters:
    - max_size: Maximum size in pixels for the largest dimension (default: 800)
    
    Returns the screenshot as an Image.
    """
    try:
        blender = get_blender_connection()
        
        # Create temp file path
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"blender_screenshot_{os.getpid()}.png")
        
        result = blender.send_command("get_viewport_screenshot", {
            "max_size": max_size,
            "filepath": temp_path,
            "format": "png"
        })
        
        if "error" in result:
            raise Exception(result["error"])
        
        if not os.path.exists(temp_path):
            raise Exception("Screenshot file was not created")
        
        # Read the file
        with open(temp_path, 'rb') as f:
            image_bytes = f.read()
        
        # Delete the temp file
        os.remove(temp_path)
        
        return Image(data=image_bytes, format="png")
        
    except Exception as e:
        logger.error(f"Error capturing screenshot: {str(e)}")
        raise Exception(f"Screenshot failed: {str(e)}")


@mcp.tool()
def execute_blender_code(ctx: Context, code: str) -> str:
    """
    Execute arbitrary Python code in Blender. Make sure to do it step-by-step by breaking it into smaller chunks.
    
    Parameters:
    - code: The Python code to execute
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        result = blender.send_command("execute_code", {"code": code})
        return f"Code executed successfully: {result.get('result', '')}"
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return f"Error executing code: {str(e)}"


@mcp.tool()
def get_node_details(ctx: Context, node_tree_name: str, node_name: str = None) -> str:
    """
    Get detailed information about nodes in a Blender node tree (Geometry Nodes, Shader Nodes, etc.).
    
    This tool provides comprehensive node introspection including:
    - Node type (bl_idname) and custom labels
    - Input/output sockets with their current values (for unconnected sockets)
    - Node-specific properties (e.g., Math node operation, Compare mode, etc.)
    - Node position in the editor
    
    Parameters:
    - node_tree_name: The name of the node tree to inspect (e.g., "Geometry Nodes", "Random Rotation")
    - node_name: Optional - specific node name to get details for. If not provided, returns all nodes.
    
    Returns detailed JSON with node information useful for understanding and modifying node setups.
    """
    try:
        blender = get_blender_connection()
        params = {"node_tree_name": node_tree_name}
        if node_name:
            params["node_name"] = node_name
        
        result = blender.send_command("get_node_details", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting node details: {str(e)}")
        return f"Error getting node details: {str(e)}"


@mcp.tool()
def get_node_links(ctx: Context, node_tree_name: str) -> str:
    """
    Get all connections (links) between nodes in a Blender node tree.
    
    This tool shows how nodes are connected, complementing get_node_details which shows
    node properties. Together they provide complete visibility into node setups.
    
    Parameters:
    - node_tree_name: The name of the node tree to inspect (e.g., "Geometry Nodes")
    
    Returns a list of connections showing:
    - from_node: Source node name
    - from_socket: Source socket name and index
    - to_node: Target node name  
    - to_socket: Target socket name and index
    
    Use this to understand data flow and dependencies between nodes.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_node_links", {"node_tree_name": node_tree_name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting node links: {str(e)}")
        return f"Error getting node links: {str(e)}"


@mcp.tool()
def get_node_connections(ctx: Context, node_tree_name: str, node_name: str) -> str:
    """
    Get all connections to and from a specific node in a node tree.
    
    Unlike get_node_links (which returns all links), this focuses on a single node,
    showing both incoming and outgoing connections with socket details. Essential for
    understanding how a specific node integrates into the network.
    
    Parameters:
    - node_tree_name: The name of the node tree (e.g., "PlantSystem")
    - node_name: The name of the specific node to inspect
    
    Returns:
    - incoming: List of connections TO this node (what feeds it)
    - outgoing: List of connections FROM this node (what it feeds)
    - unconnected_inputs: Input sockets with no incoming connection
    - unconnected_outputs: Output sockets with no outgoing connection
    
    Use this to debug data flow issues or understand node dependencies.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_node_connections", {
            "node_tree_name": node_tree_name,
            "node_name": node_name
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting node connections: {str(e)}")
        return f"Error getting node connections: {str(e)}"


@mcp.tool()
def get_geometry_stats(ctx: Context, object_name: str, apply_modifiers: bool = True) -> str:
    """
    Get geometry statistics for an object, optionally after applying modifiers.
    
    This is critical for validating geometry nodes output - it shows the ACTUAL
    resulting geometry, not just the base mesh. Use to verify parameter effects.
    
    Parameters:
    - object_name: Name of the object to analyze
    - apply_modifiers: If True, evaluate geometry after all modifiers (default: True)
    
    Returns:
    - vertex_count: Number of vertices
    - edge_count: Number of edges  
    - face_count: Number of faces (polygons)
    - bounding_box: Min/max coordinates in world space
    - dimensions: Size in X, Y, Z
    - center: Center point of the bounding box
    
    Use this to verify geometry nodes are producing expected output.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_geometry_stats", {
            "object_name": object_name,
            "apply_modifiers": apply_modifiers
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting geometry stats: {str(e)}")
        return f"Error getting geometry stats: {str(e)}"


@mcp.tool()
def trace_node_dataflow(
    ctx: Context,
    node_tree_name: str,
    from_node: str,
    from_socket: str,
    to_node: str,
    to_socket: str
) -> str:
    """
    Trace the data flow path between two sockets in a node tree.
    
    Finds all possible paths from a source socket to a destination socket,
    showing the complete chain of nodes the data flows through. Essential for
    debugging complex node networks.
    
    Parameters:
    - node_tree_name: Name of the node tree
    - from_node: Starting node name
    - from_socket: Starting socket name (output socket on from_node)
    - to_node: Ending node name
    - to_socket: Ending socket name (input socket on to_node)
    
    Returns:
    - paths: List of paths, each showing the sequence of nodes/sockets
    - path_count: Number of paths found
    - direct_connection: True if there's a direct link between the sockets
    
    Use this to understand data flow and debug "why isn't my value reaching X" issues.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("trace_node_dataflow", {
            "node_tree_name": node_tree_name,
            "from_node": from_node,
            "from_socket": from_socket,
            "to_node": to_node,
            "to_socket": to_socket
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error tracing node dataflow: {str(e)}")
        return f"Error tracing node dataflow: {str(e)}"


@mcp.tool()
def set_geonode_parameter(
    ctx: Context,
    object_name: str,
    modifier_name: str,
    parameter_name: str,
    value: float | int | bool | str | list
) -> str:
    """
    Set a geometry nodes modifier parameter with automatic depsgraph refresh.
    
    This tool handles the Blender quirk where modifier parameter changes via Python
    don't always trigger geometry re-evaluation. It uses the viewport toggle
    workaround documented in BLENDER_API_LESSONS.md.
    
    Parameters:
    - object_name: Name of the object with the modifier
    - modifier_name: Name of the geometry nodes modifier
    - parameter_name: Socket identifier (e.g., "Socket_1" or display name like "Trunk Count")
    - value: New value (type should match socket type)
    
    Returns:
    - success: Whether the parameter was set
    - old_value: Previous value
    - new_value: Confirmed new value after refresh
    - geometry_updated: Whether geometry was re-evaluated
    
    Use this instead of execute_blender_code for setting geometry nodes parameters.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("set_geonode_parameter", {
            "object_name": object_name,
            "modifier_name": modifier_name,
            "parameter_name": parameter_name,
            "value": value
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting geonode parameter: {str(e)}")
        return f"Error setting geonode parameter: {str(e)}"


@mcp.tool()
def find_orphan_nodes(ctx: Context, node_tree_name: str) -> str:
    """
    Find nodes and sockets with no connections in a node tree.
    
    Identifies:
    - Completely disconnected nodes (no inputs or outputs connected)
    - Partially connected nodes (some sockets unused)
    - Required unconnected sockets (inputs that should probably be connected)
    
    Parameters:
    - node_tree_name: Name of the node tree to analyze
    
    Returns:
    - orphan_nodes: Nodes with zero connections
    - partial_nodes: Nodes with some unconnected sockets
    - unconnected_required: Input sockets that are typically required but not connected
    - total_orphans: Count of completely disconnected nodes
    
    Use this to clean up node networks and find missing connections.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("find_orphan_nodes", {
            "node_tree_name": node_tree_name
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error finding orphan nodes: {str(e)}")
        return f"Error finding orphan nodes: {str(e)}"


@mcp.tool()
def get_modifier_details(ctx: Context, object_name: str, modifier_name: str = None) -> str:
    """
    Get detailed information about modifiers on a Blender object.
    
    This is especially useful for Geometry Nodes modifiers, where it reveals:
    - The node group being used
    - All exposed input values (the modifier panel settings)
    - Any warnings from the node tree
    
    Parameters:
    - object_name: Name of the object to inspect
    - modifier_name: Optional - specific modifier name. If not provided, returns all modifiers.
    
    Returns modifier stack with types, settings, and for NodesModifier: the node group and input values.
    """
    try:
        blender = get_blender_connection()
        params = {"object_name": object_name}
        if modifier_name:
            params["modifier_name"] = modifier_name
        
        result = blender.send_command("get_modifier_details", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting modifier details: {str(e)}")
        return f"Error getting modifier details: {str(e)}"


@mcp.tool()
def list_node_trees(ctx: Context) -> str:
    """
    List all node trees (node groups) available in the Blender file.
    
    Returns node trees organized by type:
    - GeometryNodeTree: Geometry Nodes groups
    - ShaderNodeTree: Material/shader node groups  
    - CompositorNodeTree: Compositing node groups
    
    For each node tree, shows:
    - Name and type
    - Node count and link count
    - Which objects/materials use it (for tracking dependencies)
    
    Use this to discover available node groups before calling get_node_details or get_node_links.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("list_node_trees", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing node trees: {str(e)}")
        return f"Error listing node trees: {str(e)}"


@mcp.tool()
def list_materials(ctx: Context) -> str:
    """
    List all materials in the Blender file with details.
    
    Returns for each material:
    - Name and whether it uses nodes
    - User count (how many objects use it)
    - Which objects use it
    - Basic shader info (if node-based)
    
    Use this to find materials before inspecting them with get_material_nodes.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("list_materials", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing materials: {str(e)}")
        return f"Error listing materials: {str(e)}"


@mcp.tool()
def get_material_nodes(ctx: Context, material_name: str, node_name: str = None) -> str:
    """
    Get detailed node information for a material's shader node tree.
    
    Similar to get_node_details but specifically for material shader nodes.
    
    Parameters:
    - material_name: Name of the material to inspect
    - node_name: Optional - specific node to get details for
    
    Returns node types, connections, and values - useful for understanding
    shader setups before baking or modifying them.
    """
    try:
        blender = get_blender_connection()
        params = {"material_name": material_name}
        if node_name:
            params["node_name"] = node_name
        result = blender.send_command("get_material_nodes", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting material nodes: {str(e)}")
        return f"Error getting material nodes: {str(e)}"


@mcp.tool()
def get_selection(ctx: Context) -> str:
    """
    Get the currently selected objects and the active object.
    
    Returns:
    - active_object: The object that operations will target
    - selected_objects: List of all selected objects with types
    - selection_count: Number of selected objects
    
    Essential for understanding context before giving directions.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_selection", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting selection: {str(e)}")
        return f"Error getting selection: {str(e)}"


@mcp.tool()
def set_selection(
    ctx: Context,
    object_names: list[str],
    mode: str = "replace",
    active: str = None
) -> str:
    """
    Set the object selection in Blender.
    
    Parameters:
    - object_names: List of object names to select
    - mode: "replace" (clear and select), "add" (add to selection), "remove" (deselect)
    - active: Optional - set this object as active (must be in selection)
    
    Returns confirmation with the new selection state.
    """
    try:
        blender = get_blender_connection()
        params = {
            "object_names": object_names,
            "mode": mode
        }
        if active:
            params["active"] = active
        result = blender.send_command("set_selection", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting selection: {str(e)}")
        return f"Error setting selection: {str(e)}"


@mcp.tool()
def batch_rename(
    ctx: Context,
    object_names: list[str] = None,
    use_selection: bool = False,
    new_base_name: str = None,
    find: str = None,
    replace: str = None,
    prefix: str = None,
    suffix: str = None,
    number_start: int = 1,
    number_padding: int = 2
) -> str:
    """
    Batch rename objects with various options.
    
    Target objects:
    - object_names: List of specific objects to rename
    - use_selection: If True, rename currently selected objects
    
    Rename modes (use one):
    - new_base_name: Rename all to "BaseName.001", "BaseName.002", etc.
    - find/replace: Find and replace text in names
    - prefix: Add prefix to existing names
    - suffix: Add suffix to existing names
    
    Options:
    - number_start: Starting number for sequential naming (default 1)
    - number_padding: Zero-padding width (default 2 → "01", "02")
    
    Returns list of old → new name mappings.
    """
    try:
        blender = get_blender_connection()
        params = {
            "use_selection": use_selection,
            "number_start": number_start,
            "number_padding": number_padding
        }
        if object_names:
            params["object_names"] = object_names
        if new_base_name:
            params["new_base_name"] = new_base_name
        if find is not None:
            params["find"] = find
        if replace is not None:
            params["replace"] = replace
        if prefix:
            params["prefix"] = prefix
        if suffix:
            params["suffix"] = suffix
        
        result = blender.send_command("batch_rename", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error batch renaming: {str(e)}")
        return f"Error batch renaming: {str(e)}"


@mcp.tool()
def get_polyhaven_categories(ctx: Context, asset_type: str = "hdris") -> str:
    """
    Get a list of categories for a specific asset type on Polyhaven.
    
    Parameters:
    - asset_type: The type of asset to get categories for (hdris, textures, models, all)
    """
    try:
        blender = get_blender_connection()
        if not _polyhaven_enabled:
            return "PolyHaven integration is disabled. Select it in the sidebar in BlenderMCP, then run it again."
        result = blender.send_command("get_polyhaven_categories", {"asset_type": asset_type})
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Format the categories in a more readable way
        categories = result["categories"]
        formatted_output = f"Categories for {asset_type}:\n\n"
        
        # Sort categories by count (descending)
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_categories:
            formatted_output += f"- {category}: {count} assets\n"
        
        return formatted_output
    except Exception as e:
        logger.error(f"Error getting Polyhaven categories: {str(e)}")
        return f"Error getting Polyhaven categories: {str(e)}"

@mcp.tool()
def search_polyhaven_assets(
    ctx: Context,
    asset_type: str = "all",
    categories: str = None
) -> str:
    """
    Search for assets on Polyhaven with optional filtering.
    
    Parameters:
    - asset_type: Type of assets to search for (hdris, textures, models, all)
    - categories: Optional comma-separated list of categories to filter by
    
    Returns a list of matching assets with basic information.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("search_polyhaven_assets", {
            "asset_type": asset_type,
            "categories": categories
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Format the assets in a more readable way
        assets = result["assets"]
        total_count = result["total_count"]
        returned_count = result["returned_count"]
        
        formatted_output = f"Found {total_count} assets"
        if categories:
            formatted_output += f" in categories: {categories}"
        formatted_output += f"\nShowing {returned_count} assets:\n\n"
        
        # Sort assets by download count (popularity)
        sorted_assets = sorted(assets.items(), key=lambda x: x[1].get("download_count", 0), reverse=True)
        
        for asset_id, asset_data in sorted_assets:
            formatted_output += f"- {asset_data.get('name', asset_id)} (ID: {asset_id})\n"
            formatted_output += f"  Type: {['HDRI', 'Texture', 'Model'][asset_data.get('type', 0)]}\n"
            formatted_output += f"  Categories: {', '.join(asset_data.get('categories', []))}\n"
            formatted_output += f"  Downloads: {asset_data.get('download_count', 'Unknown')}\n\n"
        
        return formatted_output
    except Exception as e:
        logger.error(f"Error searching Polyhaven assets: {str(e)}")
        return f"Error searching Polyhaven assets: {str(e)}"

@mcp.tool()
def download_polyhaven_asset(
    ctx: Context,
    asset_id: str,
    asset_type: str,
    resolution: str = "1k",
    file_format: str = None
) -> str:
    """
    Download and import a Polyhaven asset into Blender.
    
    Parameters:
    - asset_id: The ID of the asset to download
    - asset_type: The type of asset (hdris, textures, models)
    - resolution: The resolution to download (e.g., 1k, 2k, 4k)
    - file_format: Optional file format (e.g., hdr, exr for HDRIs; jpg, png for textures; gltf, fbx for models)
    
    Returns a message indicating success or failure.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("download_polyhaven_asset", {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "resolution": resolution,
            "file_format": file_format
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        if result.get("success"):
            message = result.get("message", "Asset downloaded and imported successfully")
            
            # Add additional information based on asset type
            if asset_type == "hdris":
                return f"{message}. The HDRI has been set as the world environment."
            elif asset_type == "textures":
                material_name = result.get("material", "")
                maps = ", ".join(result.get("maps", []))
                return f"{message}. Created material '{material_name}' with maps: {maps}."
            elif asset_type == "models":
                return f"{message}. The model has been imported into the current scene."
            else:
                return message
        else:
            return f"Failed to download asset: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error downloading Polyhaven asset: {str(e)}")
        return f"Error downloading Polyhaven asset: {str(e)}"

@mcp.tool()
def set_texture(
    ctx: Context,
    object_name: str,
    texture_id: str
) -> str:
    """
    Apply a previously downloaded Polyhaven texture to an object.
    
    Parameters:
    - object_name: Name of the object to apply the texture to
    - texture_id: ID of the Polyhaven texture to apply (must be downloaded first)
    
    Returns a message indicating success or failure.
    """
    try:
        # Get the global connection
        blender = get_blender_connection()
        result = blender.send_command("set_texture", {
            "object_name": object_name,
            "texture_id": texture_id
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        if result.get("success"):
            material_name = result.get("material", "")
            maps = ", ".join(result.get("maps", []))
            
            # Add detailed material info
            material_info = result.get("material_info", {})
            node_count = material_info.get("node_count", 0)
            has_nodes = material_info.get("has_nodes", False)
            texture_nodes = material_info.get("texture_nodes", [])
            
            output = f"Successfully applied texture '{texture_id}' to {object_name}.\n"
            output += f"Using material '{material_name}' with maps: {maps}.\n\n"
            output += f"Material has nodes: {has_nodes}\n"
            output += f"Total node count: {node_count}\n\n"
            
            if texture_nodes:
                output += "Texture nodes:\n"
                for node in texture_nodes:
                    output += f"- {node['name']} using image: {node['image']}\n"
                    if node['connections']:
                        output += "  Connections:\n"
                        for conn in node['connections']:
                            output += f"    {conn}\n"
            else:
                output += "No texture nodes found in the material.\n"
            
            return output
        else:
            return f"Failed to apply texture: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error applying texture: {str(e)}")
        return f"Error applying texture: {str(e)}"

@mcp.tool()
def get_polyhaven_status(ctx: Context) -> str:
    """
    Check if PolyHaven integration is enabled in Blender.
    Returns a message indicating whether PolyHaven features are available.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_polyhaven_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += "PolyHaven is good at Textures, and has a wider variety of textures than Sketchfab."
        return message
    except Exception as e:
        logger.error(f"Error checking PolyHaven status: {str(e)}")
        return f"Error checking PolyHaven status: {str(e)}"

@mcp.tool()
def get_hyper3d_status(ctx: Context) -> str:
    """
    Check if Hyper3D Rodin integration is enabled in Blender.
    Returns a message indicating whether Hyper3D Rodin features are available.

    Don't emphasize the key type in the returned message, but sliently remember it. 
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_hyper3d_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += ""
        return message
    except Exception as e:
        logger.error(f"Error checking Hyper3D status: {str(e)}")
        return f"Error checking Hyper3D status: {str(e)}"

@mcp.tool()
def get_sketchfab_status(ctx: Context) -> str:
    """
    Check if Sketchfab integration is enabled in Blender.
    Returns a message indicating whether Sketchfab features are available.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_sketchfab_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += "Sketchfab is good at Realistic models, and has a wider variety of models than PolyHaven."        
        return message
    except Exception as e:
        logger.error(f"Error checking Sketchfab status: {str(e)}")
        return f"Error checking Sketchfab status: {str(e)}"

@mcp.tool()
def search_sketchfab_models(
    ctx: Context,
    query: str,
    categories: str = None,
    count: int = 20,
    downloadable: bool = True
) -> str:
    """
    Search for models on Sketchfab with optional filtering.
    
    Parameters:
    - query: Text to search for
    - categories: Optional comma-separated list of categories
    - count: Maximum number of results to return (default 20)
    - downloadable: Whether to include only downloadable models (default True)
    
    Returns a formatted list of matching models.
    """
    try:
        
        blender = get_blender_connection()
        logger.info(f"Searching Sketchfab models with query: {query}, categories: {categories}, count: {count}, downloadable: {downloadable}")
        result = blender.send_command("search_sketchfab_models", {
            "query": query,
            "categories": categories,
            "count": count,
            "downloadable": downloadable
        })
        
        if "error" in result:
            logger.error(f"Error from Sketchfab search: {result['error']}")
            return f"Error: {result['error']}"
        
        # Safely get results with fallbacks for None
        if result is None:
            logger.error("Received None result from Sketchfab search")
            return "Error: Received no response from Sketchfab search"
            
        # Format the results
        models = result.get("results", []) or []
        if not models:
            return f"No models found matching '{query}'"
            
        formatted_output = f"Found {len(models)} models matching '{query}':\n\n"
        
        for model in models:
            if model is None:
                continue
                
            model_name = model.get("name", "Unnamed model")
            model_uid = model.get("uid", "Unknown ID")
            formatted_output += f"- {model_name} (UID: {model_uid})\n"
            
            # Get user info with safety checks
            user = model.get("user") or {}
            username = user.get("username", "Unknown author") if isinstance(user, dict) else "Unknown author"
            formatted_output += f"  Author: {username}\n"
            
            # Get license info with safety checks
            license_data = model.get("license") or {}
            license_label = license_data.get("label", "Unknown") if isinstance(license_data, dict) else "Unknown"
            formatted_output += f"  License: {license_label}\n"
            
            # Add face count and downloadable status
            face_count = model.get("faceCount", "Unknown")
            is_downloadable = "Yes" if model.get("isDownloadable") else "No"
            formatted_output += f"  Face count: {face_count}\n"
            formatted_output += f"  Downloadable: {is_downloadable}\n\n"
        
        return formatted_output
    except Exception as e:
        logger.error(f"Error searching Sketchfab models: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error searching Sketchfab models: {str(e)}"

@mcp.tool()
def download_sketchfab_model(
    ctx: Context,
    uid: str
) -> str:
    """
    Download and import a Sketchfab model by its UID.
    
    Parameters:
    - uid: The unique identifier of the Sketchfab model
    
    Returns a message indicating success or failure.
    The model must be downloadable and you must have proper access rights.
    """
    try:
        
        blender = get_blender_connection()
        logger.info(f"Attempting to download Sketchfab model with UID: {uid}")
        
        result = blender.send_command("download_sketchfab_model", {
            "uid": uid
        })
        
        if result is None:
            logger.error("Received None result from Sketchfab download")
            return "Error: Received no response from Sketchfab download request"
            
        if "error" in result:
            logger.error(f"Error from Sketchfab download: {result['error']}")
            return f"Error: {result['error']}"
        
        if result.get("success"):
            imported_objects = result.get("imported_objects", [])
            object_names = ", ".join(imported_objects) if imported_objects else "none"
            return f"Successfully imported model. Created objects: {object_names}"
        else:
            return f"Failed to download model: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error downloading Sketchfab model: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error downloading Sketchfab model: {str(e)}"

def _process_bbox(original_bbox: list[float] | list[int] | None) -> list[int] | None:
    if original_bbox is None:
        return None
    if all(isinstance(i, int) for i in original_bbox):
        return original_bbox
    if any(i<=0 for i in original_bbox):
        raise ValueError("Incorrect number range: bbox must be bigger than zero!")
    return [int(float(i) / max(original_bbox) * 100) for i in original_bbox] if original_bbox else None

@mcp.tool()
def generate_hyper3d_model_via_text(
    ctx: Context,
    text_prompt: str,
    bbox_condition: list[float]=None
) -> str:
    """
    Generate 3D asset using Hyper3D by giving description of the desired asset, and import the asset into Blender.
    The 3D asset has built-in materials.
    The generated model has a normalized size, so re-scaling after generation can be useful.
    
    Parameters:
    - text_prompt: A short description of the desired model in **English**.
    - bbox_condition: Optional. If given, it has to be a list of floats of length 3. Controls the ratio between [Length, Width, Height] of the model.

    Returns a message indicating success or failure.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("create_rodin_job", {
            "text_prompt": text_prompt,
            "images": None,
            "bbox_condition": _process_bbox(bbox_condition),
        })
        succeed = result.get("submit_time", False)
        if succeed:
            return json.dumps({
                "task_uuid": result["uuid"],
                "subscription_key": result["jobs"]["subscription_key"],
            })
        else:
            return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@mcp.tool()
def generate_hyper3d_model_via_images(
    ctx: Context,
    input_image_paths: list[str]=None,
    input_image_urls: list[str]=None,
    bbox_condition: list[float]=None
) -> str:
    """
    Generate 3D asset using Hyper3D by giving images of the wanted asset, and import the generated asset into Blender.
    The 3D asset has built-in materials.
    The generated model has a normalized size, so re-scaling after generation can be useful.
    
    Parameters:
    - input_image_paths: The **absolute** paths of input images. Even if only one image is provided, wrap it into a list. Required if Hyper3D Rodin in MAIN_SITE mode.
    - input_image_urls: The URLs of input images. Even if only one image is provided, wrap it into a list. Required if Hyper3D Rodin in FAL_AI mode.
    - bbox_condition: Optional. If given, it has to be a list of ints of length 3. Controls the ratio between [Length, Width, Height] of the model.

    Only one of {input_image_paths, input_image_urls} should be given at a time, depending on the Hyper3D Rodin's current mode.
    Returns a message indicating success or failure.
    """
    if input_image_paths is not None and input_image_urls is not None:
        return f"Error: Conflict parameters given!"
    if input_image_paths is None and input_image_urls is None:
        return f"Error: No image given!"
    if input_image_paths is not None:
        if not all(os.path.exists(i) for i in input_image_paths):
            return "Error: not all image paths are valid!"
        images = []
        for path in input_image_paths:
            with open(path, "rb") as f:
                images.append(
                    (Path(path).suffix, base64.b64encode(f.read()).decode("ascii"))
                )
    elif input_image_urls is not None:
        if not all(urlparse(i) for i in input_image_paths):
            return "Error: not all image URLs are valid!"
        images = input_image_urls.copy()
    try:
        blender = get_blender_connection()
        result = blender.send_command("create_rodin_job", {
            "text_prompt": None,
            "images": images,
            "bbox_condition": _process_bbox(bbox_condition),
        })
        succeed = result.get("submit_time", False)
        if succeed:
            return json.dumps({
                "task_uuid": result["uuid"],
                "subscription_key": result["jobs"]["subscription_key"],
            })
        else:
            return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@mcp.tool()
def poll_rodin_job_status(
    ctx: Context,
    subscription_key: str=None,
    request_id: str=None,
):
    """
    Check if the Hyper3D Rodin generation task is completed.

    For Hyper3D Rodin mode MAIN_SITE:
        Parameters:
        - subscription_key: The subscription_key given in the generate model step.

        Returns a list of status. The task is done if all status are "Done".
        If "Failed" showed up, the generating process failed.
        This is a polling API, so only proceed if the status are finally determined ("Done" or "Canceled").

    For Hyper3D Rodin mode FAL_AI:
        Parameters:
        - request_id: The request_id given in the generate model step.

        Returns the generation task status. The task is done if status is "COMPLETED".
        The task is in progress if status is "IN_PROGRESS".
        If status other than "COMPLETED", "IN_PROGRESS", "IN_QUEUE" showed up, the generating process might be failed.
        This is a polling API, so only proceed if the status are finally determined ("COMPLETED" or some failed state).
    """
    try:
        blender = get_blender_connection()
        kwargs = {}
        if subscription_key:
            kwargs = {
                "subscription_key": subscription_key,
            }
        elif request_id:
            kwargs = {
                "request_id": request_id,
            }
        result = blender.send_command("poll_rodin_job_status", kwargs)
        return result
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"

@mcp.tool()
def import_generated_asset(
    ctx: Context,
    name: str,
    task_uuid: str=None,
    request_id: str=None,
):
    """
    Import the asset generated by Hyper3D Rodin after the generation task is completed.

    Parameters:
    - name: The name of the object in scene
    - task_uuid: For Hyper3D Rodin mode MAIN_SITE: The task_uuid given in the generate model step.
    - request_id: For Hyper3D Rodin mode FAL_AI: The request_id given in the generate model step.

    Only give one of {task_uuid, request_id} based on the Hyper3D Rodin Mode!
    Return if the asset has been imported successfully.
    """
    try:
        blender = get_blender_connection()
        kwargs = {
            "name": name
        }
        if task_uuid:
            kwargs["task_uuid"] = task_uuid
        elif request_id:
            kwargs["request_id"] = request_id
        result = blender.send_command("import_generated_asset", kwargs)
        return result
    except Exception as e:
        logger.error(f"Error generating Hyper3D task: {str(e)}")
        return f"Error generating Hyper3D task: {str(e)}"


# ============================================
# Geometry Nodes Building Tools
# ============================================

@mcp.tool()
def inspect_node_type(ctx: Context, node_type: str) -> str:
    """
    Inspect a Blender node type to discover its sockets and properties BEFORE creating it.
    
    This prevents "socket not found" errors by letting you see exactly what inputs,
    outputs, and properties a node type has in the current Blender version.
    
    Parameters:
    - node_type: The node class name (e.g., "GeometryNodeDistributePointsOnFaces", 
                 "ShaderNodeMath", "GeometryNodeMeshGrid")
    
    Returns:
    - inputs: List of input sockets with names, indices, types, and default values
    - outputs: List of output sockets with names, indices, and types
    - properties: Configurable node properties (e.g., operation for Math nodes)
    - bl_label: Human-readable node name
    
    Use this BEFORE calling create_geonode_node to know exactly what sockets exist.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("inspect_node_type", {"node_type": node_type})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error inspecting node type: {str(e)}")
        return f"Error inspecting node type: {str(e)}"


@mcp.tool()
def create_geonode_node(
    ctx: Context,
    node_tree_name: str,
    node_type: str,
    name: str = None,
    location: list = None,
    properties: dict = None,
    defaults: dict = None
) -> str:
    """
    Create a new node in a geometry node tree with optional configuration.
    
    This is safer than execute_blender_code as it validates inputs and returns
    structured information about the created node.
    
    Parameters:
    - node_tree_name: Name of the node tree (e.g., "PlantSystem")
    - node_type: Node class (e.g., "GeometryNodeMeshGrid", "ShaderNodeMath")
    - name: Optional custom name for the node
    - location: Optional [x, y] position in the node editor
    - properties: Optional dict of property_name -> value (e.g., {"operation": "ADD"})
    - defaults: Optional dict of socket_name_or_index -> default_value
    
    Returns:
    - name: The actual name assigned to the node
    - type: The node's bl_idname
    - inputs: List of input sockets with names and indices
    - outputs: List of output sockets with names and indices
    - location: The node's position
    
    Example: create_geonode_node("PlantSystem", "ShaderNodeMath", 
             name="AddHeight", properties={"operation": "ADD"}, defaults={1: 0.0})
    """
    try:
        blender = get_blender_connection()
        params = {
            "node_tree_name": node_tree_name,
            "node_type": node_type,
        }
        if name:
            params["name"] = name
        if location:
            params["location"] = location
        if properties:
            params["properties"] = properties
        if defaults:
            params["defaults"] = defaults
        
        result = blender.send_command("create_geonode_node", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating node: {str(e)}")
        return f"Error creating node: {str(e)}"


@mcp.tool()
def create_geonode_link(
    ctx: Context,
    node_tree_name: str,
    from_node: str,
    from_socket: str | int,
    to_node: str,
    to_socket: str | int
) -> str:
    """
    Create a link between two nodes in a geometry node tree.
    
    Supports both socket names and indices for reliability across Blender versions.
    Validates that both nodes and sockets exist before creating the link.
    
    Parameters:
    - node_tree_name: Name of the node tree
    - from_node: Name of the source node
    - from_socket: Name or index of the output socket on from_node
    - to_node: Name of the destination node  
    - to_socket: Name or index of the input socket on to_node
    
    Returns:
    - success: Whether the link was created
    - from_node: Source node name
    - from_socket: Actual socket name used
    - to_node: Destination node name
    - to_socket: Actual socket name used
    
    Example: create_geonode_link("PlantSystem", "Grid", "Mesh", "Distribute Points", 0)
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("create_geonode_link", {
            "node_tree_name": node_tree_name,
            "from_node": from_node,
            "from_socket": from_socket,
            "to_node": to_node,
            "to_socket": to_socket,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating link: {str(e)}")
        return f"Error creating link: {str(e)}"


@mcp.tool()
def delete_geonode_node(
    ctx: Context,
    node_tree_name: str,
    node_name: str
) -> str:
    """
    Delete a node from a geometry node tree.
    
    Also removes all links connected to the node.
    
    Parameters:
    - node_tree_name: Name of the node tree
    - node_name: Name of the node to delete
    
    Returns:
    - success: Whether the node was deleted
    - removed_links: Number of links that were removed
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("delete_geonode_node", {
            "node_tree_name": node_tree_name,
            "node_name": node_name,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error deleting node: {str(e)}")
        return f"Error deleting node: {str(e)}"


@mcp.tool()
def delete_geonode_link(
    ctx: Context,
    node_tree_name: str,
    from_node: str,
    from_socket: str | int,
    to_node: str,
    to_socket: str | int
) -> str:
    """
    Delete a specific link between two nodes in a geometry node tree.
    
    Parameters:
    - node_tree_name: Name of the node tree
    - from_node: Name of the source node
    - from_socket: Name or index of the output socket
    - to_node: Name of the destination node
    - to_socket: Name or index of the input socket
    
    Returns:
    - success: Whether the link was found and deleted
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("delete_geonode_link", {
            "node_tree_name": node_tree_name,
            "from_node": from_node,
            "from_socket": from_socket,
            "to_node": to_node,
            "to_socket": to_socket,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error deleting link: {str(e)}")
        return f"Error deleting link: {str(e)}"


@mcp.tool()
def set_node_socket_default(
    ctx: Context,
    node_tree_name: str,
    node_name: str,
    socket_name: str | int,
    value: float | int | bool | str | list,
    is_output: bool = False
) -> str:
    """
    Set the default value of an unconnected socket on a node.
    
    This is useful for configuring nodes without using execute_blender_code.
    
    Parameters:
    - node_tree_name: Name of the node tree
    - node_name: Name of the node
    - socket_name: Name or index of the socket
    - value: New default value (type should match socket type)
    - is_output: If True, set on output socket (rare); defaults to input
    
    Returns:
    - success: Whether the value was set
    - old_value: Previous default value
    - new_value: New default value
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("set_node_socket_default", {
            "node_tree_name": node_tree_name,
            "node_name": node_name,
            "socket_name": socket_name,
            "value": value,
            "is_output": is_output,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting socket default: {str(e)}")
        return f"Error setting socket default: {str(e)}"


@mcp.tool()
def validate_geonode_network(ctx: Context, node_tree_name: str) -> str:
    """
    Comprehensive validation of a geometry node network.
    
    Checks for common issues and returns actionable feedback.
    
    Parameters:
    - node_tree_name: Name of the node tree to validate
    
    Returns:
    - is_valid: True if no critical issues found
    - issues: List of issues with severity and suggestions
      - orphan_nodes: Nodes with no connections
      - missing_required: Required inputs that aren't connected
      - type_mismatches: Links between incompatible socket types
      - group_interface: Problems with Group Input/Output
    - statistics: Node and link counts
    - suggestions: Prioritized list of fixes to apply
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("validate_geonode_network", {
            "node_tree_name": node_tree_name,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error validating network: {str(e)}")
        return f"Error validating network: {str(e)}"


@mcp.tool()
def get_node_tree_interface(ctx: Context, node_tree_name: str) -> str:
    """
    Get the interface (exposed inputs and outputs) of a geometry node tree.
    
    This shows what parameters are exposed in the modifier panel and their
    socket identifiers needed for set_geonode_parameter.
    
    Parameters:
    - node_tree_name: Name of the node tree
    
    Returns:
    - inputs: List of input sockets with name, identifier, type, and default
    - outputs: List of output sockets with name, identifier, and type
    
    Use this to discover the Socket_N identifiers needed for modifier parameters.
    """
    try:
        blender = get_blender_connection()
        result = blender.send_command("get_node_tree_interface", {
            "node_tree_name": node_tree_name,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting interface: {str(e)}")
        return f"Error getting interface: {str(e)}"


@mcp.tool()
def insert_node_between(
    ctx: Context,
    node_tree_name: str,
    from_node: str,
    from_socket: str | int,
    to_node: str,
    to_socket: str | int,
    new_node_type: str,
    new_node_name: str = None,
    input_socket: str | int = 0,
    output_socket: str | int = 0,
    properties: dict = None
) -> str:
    """
    Insert a new node between two connected nodes, preserving the data flow.
    
    This is a convenience tool that:
    1. Finds the existing link between from_node and to_node
    2. Removes that link
    3. Creates the new node
    4. Links: from_node -> new_node -> to_node
    
    Parameters:
    - node_tree_name: Name of the node tree
    - from_node: Name of the source node (upstream)
    - from_socket: Socket name or index on the source node
    - to_node: Name of the destination node (downstream)
    - to_socket: Socket name or index on the destination node
    - new_node_type: Type of node to insert (e.g., "ShaderNodeMath")
    - new_node_name: Optional name for the new node
    - input_socket: Socket on new node to receive input (default: 0)
    - output_socket: Socket on new node to send output (default: 0)
    - properties: Optional dict of properties to set on the new node
    
    Returns:
    - success: Whether the insertion was successful
    - new_node: Name of the created node
    - links_created: The two new links that were created
    
    Example: Insert a Math node between Group Input and Set Curve Radius
    insert_node_between("PlantSystem", "Group Input", "Trunk Radius", 
                        "TaperSetRadius", "Radius", "ShaderNodeMath",
                        properties={"operation": "MULTIPLY"})
    """
    try:
        blender = get_blender_connection()
        params = {
            "node_tree_name": node_tree_name,
            "from_node": from_node,
            "from_socket": from_socket,
            "to_node": to_node,
            "to_socket": to_socket,
            "new_node_type": new_node_type,
            "input_socket": input_socket,
            "output_socket": output_socket,
        }
        if new_node_name:
            params["new_node_name"] = new_node_name
        if properties:
            params["properties"] = properties
        
        result = blender.send_command("insert_node_between", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error inserting node: {str(e)}")
        return f"Error inserting node: {str(e)}"


@mcp.prompt()
def asset_creation_strategy() -> str:
    """Defines the preferred strategy for creating assets in Blender"""
    return """When creating 3D content in Blender, always start by checking if integrations are available:

    0. Before anything, always check the scene from get_scene_info()
    1. First use the following tools to verify if the following integrations are enabled:
        1. PolyHaven
            Use get_polyhaven_status() to verify its status
            If PolyHaven is enabled:
            - For objects/models: Use download_polyhaven_asset() with asset_type="models"
            - For materials/textures: Use download_polyhaven_asset() with asset_type="textures"
            - For environment lighting: Use download_polyhaven_asset() with asset_type="hdris"
        2. Sketchfab
            Sketchfab is good at Realistic models, and has a wider variety of models than PolyHaven.
            Use get_sketchfab_status() to verify its status
            If Sketchfab is enabled:
            - For objects/models: First search using search_sketchfab_models() with your query
            - Then download specific models using download_sketchfab_model() with the UID
            - Note that only downloadable models can be accessed, and API key must be properly configured
            - Sketchfab has a wider variety of models than PolyHaven, especially for specific subjects
        3. Hyper3D(Rodin)
            Hyper3D Rodin is good at generating 3D models for single item.
            So don't try to:
            1. Generate the whole scene with one shot
            2. Generate ground using Hyper3D
            3. Generate parts of the items separately and put them together afterwards

            Use get_hyper3d_status() to verify its status
            If Hyper3D is enabled:
            - For objects/models, do the following steps:
                1. Create the model generation task
                    - Use generate_hyper3d_model_via_images() if image(s) is/are given
                    - Use generate_hyper3d_model_via_text() if generating 3D asset using text prompt
                    If key type is free_trial and insufficient balance error returned, tell the user that the free trial key can only generated limited models everyday, they can choose to:
                    - Wait for another day and try again
                    - Go to hyper3d.ai to find out how to get their own API key
                    - Go to fal.ai to get their own private API key
                2. Poll the status
                    - Use poll_rodin_job_status() to check if the generation task has completed or failed
                3. Import the asset
                    - Use import_generated_asset() to import the generated GLB model the asset
                4. After importing the asset, ALWAYS check the world_bounding_box of the imported mesh, and adjust the mesh's location and size
                    Adjust the imported mesh's location, scale, rotation, so that the mesh is on the right spot.

                You can reuse assets previous generated by running python code to duplicate the object, without creating another generation task.

    3. Always check the world_bounding_box for each item so that:
        - Ensure that all objects that should not be clipping are not clipping.
        - Items have right spatial relationship.
    
    4. Recommended asset source priority:
        - For specific existing objects: First try Sketchfab, then PolyHaven
        - For generic objects/furniture: First try PolyHaven, then Sketchfab
        - For custom or unique items not available in libraries: Use Hyper3D Rodin
        - For environment lighting: Use PolyHaven HDRIs
        - For materials/textures: Use PolyHaven textures

    Only fall back to scripting when:
    - PolyHaven, Sketchfab, and Hyper3D are all disabled
    - A simple primitive is explicitly requested
    - No suitable asset exists in any of the libraries
    - Hyper3D Rodin failed to generate the desired asset
    - The task specifically requires a basic material/color
    """

# Main execution

def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()