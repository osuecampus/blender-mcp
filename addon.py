# Code created by Siddharth Ahuja: www.github.com/ahujasid © 2025

import bpy
import mathutils
import json
import threading
import socket
import time
import requests
import tempfile
import traceback
import os
import shutil
import zipfile
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
import io
from contextlib import redirect_stdout, suppress

bl_info = {
    "name": "Blender MCP",
    "author": "BlenderMCP",
    "version": (1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "Connect Blender to Claude via MCP",
    "category": "Interface",
}

RODIN_FREE_TRIAL_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez"

# Add User-Agent as required by Poly Haven API
REQ_HEADERS = requests.utils.default_headers()
REQ_HEADERS.update({"User-Agent": "blender-mcp"})

class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None

    def start(self):
        if self.running:
            print("Server is already running")
            return

        self.running = True

        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)

            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()

            print(f"BlenderMCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()

    def stop(self):
        self.running = False

        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        # Wait for thread to finish
        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None

        print("BlenderMCP server stopped")

    def _server_loop(self):
        """Main server loop in a separate thread"""
        print("Server thread started")
        self.socket.settimeout(1.0)  # Timeout to allow for stopping

        while self.running:
            try:
                # Accept new connection
                try:
                    client, address = self.socket.accept()
                    print(f"Connected to client: {address}")

                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Just check running condition
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {str(e)}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error in server loop: {str(e)}")
                if not self.running:
                    break
                time.sleep(0.5)

        print("Server thread stopped")

    def _handle_client(self, client):
        """Handle connected client"""
        print("Client handler started")
        client.settimeout(None)  # No timeout
        buffer = b''

        try:
            while self.running:
                # Receive data
                try:
                    data = client.recv(8192)
                    if not data:
                        print("Client disconnected")
                        break

                    buffer += data
                    try:
                        # Try to parse command
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b''

                        # Execute command in Blender's main thread
                        def execute_wrapper():
                            try:
                                response = self.execute_command(command)
                                response_json = json.dumps(response)
                                try:
                                    client.sendall(response_json.encode('utf-8'))
                                except:
                                    print("Failed to send response - client disconnected")
                            except Exception as e:
                                print(f"Error executing command: {str(e)}")
                                traceback.print_exc()
                                try:
                                    error_response = {
                                        "status": "error",
                                        "message": str(e)
                                    }
                                    client.sendall(json.dumps(error_response).encode('utf-8'))
                                except:
                                    pass
                            return None

                        # Schedule execution in main thread
                        bpy.app.timers.register(execute_wrapper, first_interval=0.0)
                    except json.JSONDecodeError:
                        # Incomplete data, wait for more
                        pass
                except Exception as e:
                    print(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            print(f"Error in client handler: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            print("Client handler stopped")

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            return self._execute_command_internal(command)

        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})

        # Add a handler for checking PolyHaven status
        if cmd_type == "get_polyhaven_status":
            return {"status": "success", "result": self.get_polyhaven_status()}

        # Base handlers that are always available
        handlers = {
            "get_scene_info": self.get_scene_info,
            "get_object_info": self.get_object_info,
            "get_node_details": self.get_node_details,
            "get_node_links": self.get_node_links,
            "get_node_connections": self.get_node_connections,
            "get_geometry_stats": self.get_geometry_stats,
            "trace_node_dataflow": self.trace_node_dataflow,
            "set_geonode_parameter": self.set_geonode_parameter,
            "find_orphan_nodes": self.find_orphan_nodes,
            "get_modifier_details": self.get_modifier_details,
            "list_node_trees": self.list_node_trees,
            "list_materials": self.list_materials,
            "get_material_nodes": self.get_material_nodes,
            "get_selection": self.get_selection,
            "set_selection": self.set_selection,
            "batch_rename": self.batch_rename,
            "get_viewport_screenshot": self.get_viewport_screenshot,
            "execute_code": self.execute_code,
            "get_polyhaven_status": self.get_polyhaven_status,
            "get_hyper3d_status": self.get_hyper3d_status,
            "get_sketchfab_status": self.get_sketchfab_status,
            # Geometry nodes building tools
            "inspect_node_type": self.inspect_node_type,
            "create_geonode_node": self.create_geonode_node,
            "create_geonode_link": self.create_geonode_link,
            "delete_geonode_node": self.delete_geonode_node,
            "delete_geonode_link": self.delete_geonode_link,
            "set_node_socket_default": self.set_node_socket_default,
            "validate_geonode_network": self.validate_geonode_network,
            "get_node_tree_interface": self.get_node_tree_interface,
            "insert_node_between": self.insert_node_between,
        }

        # Add Polyhaven handlers only if enabled
        if bpy.context.scene.blendermcp_use_polyhaven:
            polyhaven_handlers = {
                "get_polyhaven_categories": self.get_polyhaven_categories,
                "search_polyhaven_assets": self.search_polyhaven_assets,
                "download_polyhaven_asset": self.download_polyhaven_asset,
                "set_texture": self.set_texture,
            }
            handlers.update(polyhaven_handlers)

        # Add Hyper3d handlers only if enabled
        if bpy.context.scene.blendermcp_use_hyper3d:
            polyhaven_handlers = {
                "create_rodin_job": self.create_rodin_job,
                "poll_rodin_job_status": self.poll_rodin_job_status,
                "import_generated_asset": self.import_generated_asset,
            }
            handlers.update(polyhaven_handlers)

        # Add Sketchfab handlers only if enabled
        if bpy.context.scene.blendermcp_use_sketchfab:
            sketchfab_handlers = {
                "search_sketchfab_models": self.search_sketchfab_models,
                "download_sketchfab_model": self.download_sketchfab_model,
            }
            handlers.update(sketchfab_handlers)

        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}



    def get_scene_info(self):
        """Get information about the current Blender scene"""
        try:
            print("Getting scene info...")
            # Simplify the scene info to reduce data size
            scene_info = {
                "name": bpy.context.scene.name,
                "object_count": len(bpy.context.scene.objects),
                "objects": [],
                "materials_count": len(bpy.data.materials),
            }

            # Collect minimal object information (limit to first 10 objects)
            for i, obj in enumerate(bpy.context.scene.objects):
                if i >= 10:  # Reduced from 20 to 10
                    break

                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    # Only include basic location data
                    "location": [round(float(obj.location.x), 2),
                                round(float(obj.location.y), 2),
                                round(float(obj.location.z), 2)],
                }
                scene_info["objects"].append(obj_info)

            print(f"Scene info collected: {len(scene_info['objects'])} objects")
            return scene_info
        except Exception as e:
            print(f"Error in get_scene_info: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

    @staticmethod
    def _get_aabb(obj):
        """ Returns the world-space axis-aligned bounding box (AABB) of an object. """
        if obj.type != 'MESH':
            raise TypeError("Object must be a mesh")

        # Get the bounding box corners in local space
        local_bbox_corners = [mathutils.Vector(corner) for corner in obj.bound_box]

        # Convert to world coordinates
        world_bbox_corners = [obj.matrix_world @ corner for corner in local_bbox_corners]

        # Compute axis-aligned min/max coordinates
        min_corner = mathutils.Vector(map(min, zip(*world_bbox_corners)))
        max_corner = mathutils.Vector(map(max, zip(*world_bbox_corners)))

        return [
            [*min_corner], [*max_corner]
        ]



    def get_object_info(self, name):
        """Get detailed information about a specific object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")

        # Basic object info
        obj_info = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
            "materials": [],
        }

        if obj.type == "MESH":
            bounding_box = self._get_aabb(obj)
            obj_info["world_bounding_box"] = bounding_box

        # Add material slots
        for slot in obj.material_slots:
            if slot.material:
                obj_info["materials"].append(slot.material.name)

        # Add mesh data if applicable
        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            obj_info["mesh"] = {
                "vertices": len(mesh.vertices),
                "edges": len(mesh.edges),
                "polygons": len(mesh.polygons),
            }

        return obj_info

    def get_node_details(self, node_tree_name, node_name=None):
        """
        Get detailed information about nodes in a Blender node tree.
        
        Parameters:
        - node_tree_name: Name of the node tree (e.g., "Geometry Nodes")
        - node_name: Optional specific node name. If None, returns all nodes.
        
        Returns detailed node information including type, sockets, and node-specific properties.
        """
        # Find the node tree
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}. Available: {[ng.name for ng in bpy.data.node_groups]}")
        
        def get_socket_value(socket):
            """Safely extract socket default value and ensure JSON serializable"""
            try:
                if hasattr(socket, 'default_value'):
                    val = socket.default_value
                    # Skip None values
                    if val is None:
                        return None
                    # Handle Blender ID types (Object, Material, etc.) - just return name
                    if hasattr(val, 'name') and hasattr(val, 'bl_rna'):
                        return f"<{type(val).__name__}: {val.name}>"
                    # Handle vectors, colors, etc.
                    if hasattr(val, '__iter__') and not isinstance(val, str):
                        try:
                            return [float(v) if isinstance(v, (int, float)) else str(v) for v in val]
                        except (TypeError, ValueError):
                            return str(val)
                    # Handle simple types
                    if isinstance(val, (bool, int, float, str)):
                        return val
                    # Fallback - convert to string
                    return str(val)
            except (AttributeError, TypeError, RuntimeError):
                pass
            return None
        
        def get_node_specific_props(node):
            """Extract node-type-specific properties"""
            props = {}
            
            # Common properties that many nodes have
            prop_names = [
                'operation',      # Math, Compare, Boolean Math, etc.
                'data_type',      # Various nodes
                'domain',         # Attribute nodes
                'mode',           # Various nodes
                'blend_type',     # Mix nodes
                'clamp',          # Math nodes
                'use_clamp',      # Math nodes
                'mapping',        # Mapping nodes
                'distribution',   # Random nodes
                'interpolation_type',  # Interpolation nodes
            ]
            
            for prop in prop_names:
                if hasattr(node, prop):
                    try:
                        val = getattr(node, prop)
                        # Convert enum values to strings
                        if isinstance(val, str) or isinstance(val, bool) or isinstance(val, (int, float)):
                            props[prop] = val
                        else:
                            props[prop] = str(val)
                    except (AttributeError, TypeError):
                        pass
            
            # Handle Group nodes specially - get the nested node tree name
            if node.bl_idname == 'GeometryNodeGroup' or node.bl_idname == 'ShaderNodeGroup':
                if hasattr(node, 'node_tree') and node.node_tree:
                    props['node_tree'] = node.node_tree.name
            
            return props
        
        def extract_node_info(node):
            """Extract all relevant information from a node"""
            node_info = {
                "name": node.name,
                "bl_idname": node.bl_idname,
                "label": node.label if node.label else None,
                "location": [round(node.location.x, 2), round(node.location.y, 2)],
                "mute": node.mute,
                "inputs": [],
                "outputs": [],
                "properties": get_node_specific_props(node),
            }
            
            # Extract input sockets
            for inp in node.inputs:
                socket_info = {
                    "name": inp.name,
                    "type": inp.bl_idname if hasattr(inp, 'bl_idname') else type(inp).__name__,
                    "is_linked": inp.is_linked,
                }
                # Only include default_value if socket is not linked
                if not inp.is_linked:
                    val = get_socket_value(inp)
                    if val is not None:
                        socket_info["default_value"] = val
                node_info["inputs"].append(socket_info)
            
            # Extract output sockets
            for out in node.outputs:
                socket_info = {
                    "name": out.name,
                    "type": out.bl_idname if hasattr(out, 'bl_idname') else type(out).__name__,
                    "is_linked": out.is_linked,
                }
                node_info["outputs"].append(socket_info)
            
            return node_info
        
        # If specific node requested, return just that node
        if node_name:
            node = node_tree.nodes.get(node_name)
            if not node:
                raise ValueError(f"Node not found: {node_name}. Available: {[n.name for n in node_tree.nodes]}")
            return extract_node_info(node)
        
        # Otherwise return all nodes
        result = {
            "node_tree_name": node_tree.name,
            "node_tree_type": node_tree.bl_idname,
            "node_count": len(node_tree.nodes),
            "link_count": len(node_tree.links),
            "nodes": [extract_node_info(n) for n in node_tree.nodes]
        }
        
        return result

    def get_node_links(self, node_tree_name):
        """
        Get all connections between nodes in a node tree.
        
        Parameters:
        - node_tree_name: Name of the node tree (e.g., "Geometry Nodes")
        
        Returns list of links with from/to node and socket information.
        """
        # Find the node tree
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}. Available: {[ng.name for ng in bpy.data.node_groups]}")
        
        def get_socket_index(socket, socket_collection):
            """Get the index of a socket in its collection"""
            for i, s in enumerate(socket_collection):
                if s == socket:
                    return i
            return -1
        
        links = []
        for link in node_tree.links:
            link_info = {
                "from_node": link.from_node.name,
                "from_socket": {
                    "name": link.from_socket.name,
                    "index": get_socket_index(link.from_socket, link.from_node.outputs),
                    "type": link.from_socket.bl_idname if hasattr(link.from_socket, 'bl_idname') else type(link.from_socket).__name__,
                },
                "to_node": link.to_node.name,
                "to_socket": {
                    "name": link.to_socket.name,
                    "index": get_socket_index(link.to_socket, link.to_node.inputs),
                    "type": link.to_socket.bl_idname if hasattr(link.to_socket, 'bl_idname') else type(link.to_socket).__name__,
                },
            }
            links.append(link_info)
        
        return {
            "node_tree_name": node_tree.name,
            "link_count": len(links),
            "links": links
        }

    def get_node_connections(self, node_tree_name, node_name):
        """
        Get all connections to and from a specific node.
        
        Parameters:
        - node_tree_name: Name of the node tree
        - node_name: Name of the specific node to inspect
        
        Returns incoming, outgoing, and unconnected sockets.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}. Available: {[ng.name for ng in bpy.data.node_groups]}")
        
        node = node_tree.nodes.get(node_name)
        if not node:
            raise ValueError(f"Node not found: {node_name}. Available: {[n.name for n in node_tree.nodes]}")
        
        incoming = []
        outgoing = []
        
        for link in node_tree.links:
            if link.to_node == node:
                incoming.append({
                    "from_node": link.from_node.name,
                    "from_socket": link.from_socket.name,
                    "to_socket": link.to_socket.name,
                    "to_socket_index": list(node.inputs).index(link.to_socket),
                })
            if link.from_node == node:
                outgoing.append({
                    "to_node": link.to_node.name,
                    "to_socket": link.to_socket.name,
                    "from_socket": link.from_socket.name,
                    "from_socket_index": list(node.outputs).index(link.from_socket),
                })
        
        # Find unconnected sockets
        unconnected_inputs = []
        for i, inp in enumerate(node.inputs):
            if not inp.is_linked:
                socket_info = {
                    "index": i,
                    "name": inp.name,
                    "type": inp.bl_idname if hasattr(inp, 'bl_idname') else type(inp).__name__,
                }
                # Add default value if available
                if hasattr(inp, 'default_value'):
                    try:
                        val = inp.default_value
                        if hasattr(val, '__iter__') and not isinstance(val, str):
                            socket_info["default_value"] = list(val)
                        else:
                            socket_info["default_value"] = val
                    except (TypeError, RuntimeError):
                        pass
                unconnected_inputs.append(socket_info)
        
        unconnected_outputs = []
        for i, out in enumerate(node.outputs):
            if not out.is_linked:
                unconnected_outputs.append({
                    "index": i,
                    "name": out.name,
                    "type": out.bl_idname if hasattr(out, 'bl_idname') else type(out).__name__,
                })
        
        return {
            "node_tree_name": node_tree.name,
            "node_name": node.name,
            "node_type": node.bl_idname,
            "incoming": incoming,
            "outgoing": outgoing,
            "unconnected_inputs": unconnected_inputs,
            "unconnected_outputs": unconnected_outputs,
            "incoming_count": len(incoming),
            "outgoing_count": len(outgoing),
        }

    def get_geometry_stats(self, object_name, apply_modifiers=True):
        """
        Get geometry statistics for an object.
        
        Parameters:
        - object_name: Name of the object
        - apply_modifiers: If True, evaluate after modifiers
        
        Returns vertex/edge/face counts, bounding box, dimensions.
        """
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}. Available: {[o.name for o in bpy.data.objects]}")
        
        if obj.type != 'MESH':
            # Try to get evaluated geometry for non-mesh objects
            if apply_modifiers:
                dg = bpy.context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(dg)
                try:
                    mesh = obj_eval.to_mesh()
                except RuntimeError:
                    return {
                        "object_name": obj.name,
                        "object_type": obj.type,
                        "error": f"Cannot get mesh data for object type: {obj.type}"
                    }
            else:
                return {
                    "object_name": obj.name,
                    "object_type": obj.type,
                    "error": f"Object is not a mesh: {obj.type}"
                }
        else:
            if apply_modifiers:
                dg = bpy.context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(dg)
                mesh = obj_eval.to_mesh()
            else:
                mesh = obj.data
                obj_eval = None
        
        # Get mesh statistics
        stats = {
            "object_name": obj.name,
            "object_type": obj.type,
            "modifiers_applied": apply_modifiers,
            "vertex_count": len(mesh.vertices),
            "edge_count": len(mesh.edges),
            "face_count": len(mesh.polygons),
        }
        
        # Calculate bounding box in world space
        if len(mesh.vertices) > 0:
            # Get world matrix
            world_matrix = obj.matrix_world
            
            # Transform all vertices to world space
            world_verts = [world_matrix @ v.co for v in mesh.vertices]
            
            min_x = min(v.x for v in world_verts)
            max_x = max(v.x for v in world_verts)
            min_y = min(v.y for v in world_verts)
            max_y = max(v.y for v in world_verts)
            min_z = min(v.z for v in world_verts)
            max_z = max(v.z for v in world_verts)
            
            stats["bounding_box"] = {
                "min": [round(min_x, 4), round(min_y, 4), round(min_z, 4)],
                "max": [round(max_x, 4), round(max_y, 4), round(max_z, 4)],
            }
            stats["dimensions"] = {
                "x": round(max_x - min_x, 4),
                "y": round(max_y - min_y, 4),
                "z": round(max_z - min_z, 4),
            }
            stats["center"] = {
                "x": round((min_x + max_x) / 2, 4),
                "y": round((min_y + max_y) / 2, 4),
                "z": round((min_z + max_z) / 2, 4),
            }
        else:
            stats["bounding_box"] = None
            stats["dimensions"] = {"x": 0, "y": 0, "z": 0}
            stats["center"] = {"x": 0, "y": 0, "z": 0}
        
        # Clean up temporary mesh
        if apply_modifiers and obj_eval:
            obj_eval.to_mesh_clear()
        
        return stats

    def trace_node_dataflow(self, node_tree_name, from_node, from_socket, to_node, to_socket):
        """
        Trace data flow path between two sockets in a node tree.
        
        Parameters:
        - node_tree_name: Name of the node tree
        - from_node: Starting node name
        - from_socket: Starting socket name (output)
        - to_node: Ending node name  
        - to_socket: Ending socket name (input)
        
        Returns all paths found between the sockets.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        start_node = node_tree.nodes.get(from_node)
        end_node = node_tree.nodes.get(to_node)
        if not start_node:
            raise ValueError(f"From node not found: {from_node}")
        if not end_node:
            raise ValueError(f"To node not found: {to_node}")
        
        # Build adjacency map: node -> list of (output_socket, target_node, target_socket)
        adjacency = {}
        for link in node_tree.links:
            node_name = link.from_node.name
            if node_name not in adjacency:
                adjacency[node_name] = []
            adjacency[node_name].append({
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name,
            })
        
        # Check for direct connection first
        direct = False
        for link in node_tree.links:
            if (link.from_node.name == from_node and 
                link.from_socket.name == from_socket and
                link.to_node.name == to_node and 
                link.to_socket.name == to_socket):
                direct = True
                break
        
        # BFS to find all paths
        paths = []
        queue = [[(from_node, from_socket)]]  # Each item is a path
        max_paths = 10  # Limit to prevent explosion
        max_depth = 50  # Prevent infinite loops
        
        while queue and len(paths) < max_paths:
            path = queue.pop(0)
            if len(path) > max_depth:
                continue
            
            current_node, current_socket = path[-1]
            
            # Check if we've reached the destination
            if current_node == to_node:
                # Verify socket matches if this is a direct connection
                if len(path) == 1:
                    # Need to check if there's a direct link to target socket
                    for adj in adjacency.get(current_node, []):
                        if (adj["from_socket"] == current_socket and 
                            adj["to_node"] == to_node and 
                            adj["to_socket"] == to_socket):
                            paths.append(path + [(to_node, to_socket)])
                else:
                    paths.append(path)
                continue
            
            # Explore neighbors from current socket
            for adj in adjacency.get(current_node, []):
                if adj["from_socket"] == current_socket:
                    next_node = adj["to_node"]
                    next_socket = adj["to_socket"]
                    
                    # Avoid cycles
                    visited_nodes = [p[0] for p in path]
                    if next_node not in visited_nodes or next_node == to_node:
                        # Find output sockets of next_node to continue tracing
                        new_path = path + [(next_node, next_socket)]
                        
                        if next_node == to_node and next_socket == to_socket:
                            paths.append(new_path)
                        else:
                            # Continue from each output of this node
                            for out in node_tree.nodes[next_node].outputs:
                                if out.is_linked:
                                    queue.append(new_path[:-1] + [(next_node, out.name)])
        
        # Format paths for output
        formatted_paths = []
        for path in paths:
            formatted_paths.append([
                {"node": node, "socket": socket} 
                for node, socket in path
            ])
        
        return {
            "node_tree_name": node_tree.name,
            "from": {"node": from_node, "socket": from_socket},
            "to": {"node": to_node, "socket": to_socket},
            "direct_connection": direct,
            "path_count": len(formatted_paths),
            "paths": formatted_paths,
        }

    def set_geonode_parameter(self, object_name, modifier_name, parameter_name, value):
        """
        Set a geometry nodes modifier parameter with automatic depsgraph refresh.
        
        Uses the viewport toggle workaround to force re-evaluation.
        
        Parameters:
        - object_name: Name of the object
        - modifier_name: Name of the geometry nodes modifier  
        - parameter_name: Socket identifier or display name
        - value: New value to set
        """
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")
        
        mod = obj.modifiers.get(modifier_name)
        if not mod:
            raise ValueError(f"Modifier not found: {modifier_name}")
        
        if mod.type != 'NODES':
            raise ValueError(f"Modifier is not a geometry nodes modifier: {mod.type}")
        
        if not mod.node_group:
            raise ValueError(f"Modifier has no node group assigned")
        
        # Find the parameter - could be by identifier (Socket_1) or by name (Trunk Count)
        param_id = None
        param_info = None
        
        if hasattr(mod.node_group, 'interface'):
            for item in mod.node_group.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
                    if item.identifier == parameter_name or item.name == parameter_name:
                        param_id = item.identifier
                        param_info = {
                            "name": item.name,
                            "identifier": item.identifier,
                            "socket_type": item.socket_type,
                        }
                        break
        
        if not param_id:
            # List available parameters
            available = []
            if hasattr(mod.node_group, 'interface'):
                for item in mod.node_group.interface.items_tree:
                    if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
                        available.append(f"{item.name} ({item.identifier})")
            raise ValueError(f"Parameter not found: {parameter_name}. Available: {available}")
        
        # Get old value
        try:
            old_value = mod[param_id]
            if hasattr(old_value, '__iter__') and not isinstance(old_value, str):
                old_value = list(old_value)
        except KeyError:
            old_value = None
        
        # Set new value
        mod[param_id] = value
        
        # Force depsgraph refresh using viewport toggle workaround
        mod.show_viewport = False
        mod.show_viewport = True
        bpy.context.view_layer.update()
        
        # Verify new value
        try:
            new_value = mod[param_id]
            if hasattr(new_value, '__iter__') and not isinstance(new_value, str):
                new_value = list(new_value)
        except KeyError:
            new_value = value
        
        return {
            "success": True,
            "object_name": obj.name,
            "modifier_name": mod.name,
            "parameter": param_info,
            "old_value": old_value,
            "new_value": new_value,
            "geometry_updated": True,
        }

    def find_orphan_nodes(self, node_tree_name):
        """
        Find nodes and sockets with no connections.
        
        Parameters:
        - node_tree_name: Name of the node tree
        
        Returns orphan nodes and partially connected nodes.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        # Skip these node types as they're often intentionally unconnected
        interface_types = {'NodeGroupInput', 'NodeGroupOutput', 'NodeFrame', 'NodeReroute'}
        
        orphan_nodes = []
        partial_nodes = []
        unconnected_required = []
        
        for node in node_tree.nodes:
            if node.bl_idname in interface_types:
                continue
            
            # Count connections
            connected_inputs = sum(1 for inp in node.inputs if inp.is_linked)
            connected_outputs = sum(1 for out in node.outputs if out.is_linked)
            total_inputs = len(node.inputs)
            total_outputs = len(node.outputs)
            
            # Completely orphaned (no connections at all)
            if connected_inputs == 0 and connected_outputs == 0:
                orphan_nodes.append({
                    "name": node.name,
                    "type": node.bl_idname,
                    "label": node.label if node.label else None,
                    "location": [round(node.location.x, 2), round(node.location.y, 2)],
                    "input_count": total_inputs,
                    "output_count": total_outputs,
                })
            # Partially connected
            elif connected_inputs < total_inputs or connected_outputs < total_outputs:
                unconnected_inputs = []
                unconnected_outputs = []
                
                for i, inp in enumerate(node.inputs):
                    if not inp.is_linked and inp.enabled:
                        unconnected_inputs.append({
                            "index": i,
                            "name": inp.name,
                            "type": inp.bl_idname if hasattr(inp, 'bl_idname') else "",
                        })
                
                for i, out in enumerate(node.outputs):
                    if not out.is_linked and out.enabled:
                        unconnected_outputs.append({
                            "index": i,
                            "name": out.name,
                            "type": out.bl_idname if hasattr(out, 'bl_idname') else "",
                        })
                
                if unconnected_inputs or unconnected_outputs:
                    partial_nodes.append({
                        "name": node.name,
                        "type": node.bl_idname,
                        "unconnected_inputs": unconnected_inputs,
                        "unconnected_outputs": unconnected_outputs,
                    })
                
                # Check for commonly required inputs
                required_input_names = {"Geometry", "Mesh", "Curve", "Points", "Instances"}
                for inp in node.inputs:
                    if inp.name in required_input_names and not inp.is_linked:
                        unconnected_required.append({
                            "node": node.name,
                            "socket": inp.name,
                            "type": inp.bl_idname if hasattr(inp, 'bl_idname') else "",
                        })
        
        return {
            "node_tree_name": node_tree.name,
            "total_nodes": len(node_tree.nodes),
            "orphan_nodes": orphan_nodes,
            "orphan_count": len(orphan_nodes),
            "partial_nodes": partial_nodes,
            "partial_count": len(partial_nodes),
            "unconnected_required": unconnected_required,
        }

    # ============================================
    # Geometry Nodes Building Tools
    # ============================================

    def inspect_node_type(self, node_type):
        """
        Inspect a Blender node type to discover its sockets and properties.
        Creates a temporary node to examine its structure.
        """
        # Create a temporary node group to inspect the node
        temp_ng = bpy.data.node_groups.new("_TempInspect", "GeometryNodeTree")
        
        try:
            # Try to create the node
            try:
                node = temp_ng.nodes.new(node_type)
            except RuntimeError as e:
                raise ValueError(f"Invalid node type: {node_type}. Error: {str(e)}")
            
            # Gather input socket info
            inputs = []
            for i, inp in enumerate(node.inputs):
                inp_info = {
                    "index": i,
                    "name": inp.name,
                    "type": inp.bl_idname if hasattr(inp, 'bl_idname') else type(inp).__name__,
                    "is_linked": inp.is_linked,
                }
                # Try to get default value
                if hasattr(inp, 'default_value'):
                    try:
                        val = inp.default_value
                        if hasattr(val, '__iter__') and not isinstance(val, str):
                            inp_info["default_value"] = list(val)
                        else:
                            inp_info["default_value"] = val
                    except:
                        pass
                inputs.append(inp_info)
            
            # Gather output socket info
            outputs = []
            for i, out in enumerate(node.outputs):
                outputs.append({
                    "index": i,
                    "name": out.name,
                    "type": out.bl_idname if hasattr(out, 'bl_idname') else type(out).__name__,
                })
            
            # Gather configurable properties
            properties = {}
            # Common properties to check
            property_names = ['operation', 'mode', 'data_type', 'domain', 'distribute_method',
                              'blend_type', 'clamp', 'use_clamp', 'interpolation_type']
            for prop_name in property_names:
                if hasattr(node, prop_name):
                    try:
                        val = getattr(node, prop_name)
                        properties[prop_name] = str(val) if not isinstance(val, (bool, int, float, str)) else val
                    except:
                        pass
            
            return {
                "node_type": node_type,
                "bl_label": node.bl_label if hasattr(node, 'bl_label') else node_type,
                "bl_idname": node.bl_idname,
                "inputs": inputs,
                "outputs": outputs,
                "properties": properties,
            }
        finally:
            # Clean up temporary node group
            bpy.data.node_groups.remove(temp_ng)

    def create_geonode_node(self, node_tree_name, node_type, name=None, location=None, properties=None, defaults=None):
        """
        Create a new node in a geometry node tree.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        # Create the node
        try:
            node = node_tree.nodes.new(node_type)
        except RuntimeError as e:
            raise ValueError(f"Failed to create node of type '{node_type}': {str(e)}")
        
        # Set name if provided
        if name:
            node.name = name
        
        # Set location if provided
        if location and len(location) >= 2:
            node.location = (location[0], location[1])
        
        # Set properties if provided
        if properties:
            for prop_name, prop_value in properties.items():
                if hasattr(node, prop_name):
                    try:
                        setattr(node, prop_name, prop_value)
                    except Exception as e:
                        print(f"Warning: Could not set property {prop_name}: {e}")
        
        # Set socket defaults if provided
        if defaults:
            for socket_id, value in defaults.items():
                # Handle both index and name
                socket = None
                if isinstance(socket_id, int):
                    if socket_id < len(node.inputs):
                        socket = node.inputs[socket_id]
                else:
                    socket = node.inputs.get(socket_id)
                
                if socket and hasattr(socket, 'default_value'):
                    try:
                        socket.default_value = value
                    except Exception as e:
                        print(f"Warning: Could not set default for {socket_id}: {e}")
        
        # Return node info
        inputs = [{"index": i, "name": inp.name} for i, inp in enumerate(node.inputs)]
        outputs = [{"index": i, "name": out.name} for i, out in enumerate(node.outputs)]
        
        return {
            "success": True,
            "name": node.name,
            "type": node.bl_idname,
            "location": [node.location.x, node.location.y],
            "inputs": inputs,
            "outputs": outputs,
        }

    def create_geonode_link(self, node_tree_name, from_node, from_socket, to_node, to_socket):
        """
        Create a link between two nodes.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        # Find source node
        src_node = node_tree.nodes.get(from_node)
        if not src_node:
            raise ValueError(f"Source node not found: {from_node}. Available: {[n.name for n in node_tree.nodes]}")
        
        # Find destination node
        dst_node = node_tree.nodes.get(to_node)
        if not dst_node:
            raise ValueError(f"Destination node not found: {to_node}. Available: {[n.name for n in node_tree.nodes]}")
        
        # Find source socket (output)
        src_socket = None
        if isinstance(from_socket, int):
            if from_socket < len(src_node.outputs):
                src_socket = src_node.outputs[from_socket]
            else:
                raise ValueError(f"Output socket index {from_socket} out of range. Node has {len(src_node.outputs)} outputs.")
        else:
            src_socket = src_node.outputs.get(from_socket)
            if not src_socket:
                available = [f"[{i}] {o.name}" for i, o in enumerate(src_node.outputs)]
                raise ValueError(f"Output socket not found: {from_socket}. Available: {available}")
        
        # Find destination socket (input)
        dst_socket = None
        if isinstance(to_socket, int):
            if to_socket < len(dst_node.inputs):
                dst_socket = dst_node.inputs[to_socket]
            else:
                raise ValueError(f"Input socket index {to_socket} out of range. Node has {len(dst_node.inputs)} inputs.")
        else:
            dst_socket = dst_node.inputs.get(to_socket)
            if not dst_socket:
                available = [f"[{i}] {inp.name}" for i, inp in enumerate(dst_node.inputs)]
                raise ValueError(f"Input socket not found: {to_socket}. Available: {available}")
        
        # Create the link
        link = node_tree.links.new(src_socket, dst_socket)
        
        return {
            "success": True,
            "from_node": src_node.name,
            "from_socket": src_socket.name,
            "from_socket_index": list(src_node.outputs).index(src_socket),
            "to_node": dst_node.name,
            "to_socket": dst_socket.name,
            "to_socket_index": list(dst_node.inputs).index(dst_socket),
        }

    def delete_geonode_node(self, node_tree_name, node_name):
        """
        Delete a node from a geometry node tree.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        node = node_tree.nodes.get(node_name)
        if not node:
            raise ValueError(f"Node not found: {node_name}. Available: {[n.name for n in node_tree.nodes]}")
        
        # Count links that will be removed
        removed_links = 0
        for inp in node.inputs:
            removed_links += len(inp.links)
        for out in node.outputs:
            removed_links += len(out.links)
        
        # Remove the node (this also removes connected links)
        node_tree.nodes.remove(node)
        
        return {
            "success": True,
            "removed_node": node_name,
            "removed_links": removed_links,
        }

    def delete_geonode_link(self, node_tree_name, from_node, from_socket, to_node, to_socket):
        """
        Delete a specific link between two nodes.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        # Find the source node and socket
        src_node = node_tree.nodes.get(from_node)
        if not src_node:
            raise ValueError(f"Source node not found: {from_node}")
        
        src_socket = None
        if isinstance(from_socket, int):
            if from_socket < len(src_node.outputs):
                src_socket = src_node.outputs[from_socket]
        else:
            src_socket = src_node.outputs.get(from_socket)
        
        if not src_socket:
            raise ValueError(f"Source socket not found: {from_socket}")
        
        # Find the destination node and socket
        dst_node = node_tree.nodes.get(to_node)
        if not dst_node:
            raise ValueError(f"Destination node not found: {to_node}")
        
        dst_socket = None
        if isinstance(to_socket, int):
            if to_socket < len(dst_node.inputs):
                dst_socket = dst_node.inputs[to_socket]
        else:
            dst_socket = dst_node.inputs.get(to_socket)
        
        if not dst_socket:
            raise ValueError(f"Destination socket not found: {to_socket}")
        
        # Find and remove the link
        link_found = False
        for link in list(node_tree.links):
            if (link.from_node == src_node and 
                link.from_socket == src_socket and
                link.to_node == dst_node and 
                link.to_socket == dst_socket):
                node_tree.links.remove(link)
                link_found = True
                break
        
        if not link_found:
            raise ValueError(f"Link not found from {from_node}.{from_socket} to {to_node}.{to_socket}")
        
        return {
            "success": True,
            "from_node": from_node,
            "from_socket": src_socket.name,
            "to_node": to_node,
            "to_socket": dst_socket.name,
        }

    def set_node_socket_default(self, node_tree_name, node_name, socket_name, value, is_output=False):
        """
        Set the default value of an unconnected socket.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        node = node_tree.nodes.get(node_name)
        if not node:
            raise ValueError(f"Node not found: {node_name}")
        
        # Get the socket collection
        sockets = node.outputs if is_output else node.inputs
        
        # Find the socket
        socket = None
        if isinstance(socket_name, int):
            if socket_name < len(sockets):
                socket = sockets[socket_name]
        else:
            socket = sockets.get(socket_name)
        
        if not socket:
            available = [f"[{i}] {s.name}" for i, s in enumerate(sockets)]
            socket_type = "output" if is_output else "input"
            raise ValueError(f"{socket_type.title()} socket not found: {socket_name}. Available: {available}")
        
        if not hasattr(socket, 'default_value'):
            raise ValueError(f"Socket {socket.name} does not have a default_value property")
        
        # Get old value
        try:
            old_value = socket.default_value
            if hasattr(old_value, '__iter__') and not isinstance(old_value, str):
                old_value = list(old_value)
        except:
            old_value = None
        
        # Set new value
        socket.default_value = value
        
        # Get new value
        try:
            new_value = socket.default_value
            if hasattr(new_value, '__iter__') and not isinstance(new_value, str):
                new_value = list(new_value)
        except:
            new_value = value
        
        return {
            "success": True,
            "node": node.name,
            "socket": socket.name,
            "old_value": old_value,
            "new_value": new_value,
        }

    def validate_geonode_network(self, node_tree_name):
        """
        Comprehensive validation of a geometry node network.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        issues = []
        suggestions = []
        
        # Find orphan nodes
        orphan_nodes = []
        interface_types = {'NodeGroupInput', 'NodeGroupOutput', 'NodeFrame', 'NodeReroute'}
        
        for node in node_tree.nodes:
            if node.bl_idname in interface_types:
                continue
            
            has_input = any(inp.is_linked for inp in node.inputs)
            has_output = any(out.is_linked for out in node.outputs)
            
            if not has_input and not has_output:
                orphan_nodes.append(node.name)
                issues.append({
                    "severity": "warning",
                    "type": "orphan_node",
                    "node": node.name,
                    "message": f"Node '{node.name}' has no connections",
                })
        
        if orphan_nodes:
            suggestions.append({
                "priority": 1,
                "action": "delete_orphan_nodes",
                "nodes": orphan_nodes,
                "message": f"Delete {len(orphan_nodes)} orphan nodes that have no effect",
            })
        
        # Check for missing required inputs
        required_types = {'NodeSocketGeometry'}
        missing_required = []
        
        for node in node_tree.nodes:
            if node.bl_idname in interface_types:
                continue
            
            for inp in node.inputs:
                socket_type = inp.bl_idname if hasattr(inp, 'bl_idname') else ''
                if socket_type in required_types and not inp.is_linked:
                    # Check if it's the main geometry input (first one)
                    if list(node.inputs).index(inp) == 0 or inp.name in ['Geometry', 'Mesh', 'Curve']:
                        missing_required.append({
                            "node": node.name,
                            "socket": inp.name,
                            "type": socket_type,
                        })
                        issues.append({
                            "severity": "error",
                            "type": "missing_required",
                            "node": node.name,
                            "socket": inp.name,
                            "message": f"Required input '{inp.name}' on '{node.name}' is not connected",
                        })
        
        if missing_required:
            suggestions.append({
                "priority": 0,
                "action": "connect_required_inputs",
                "inputs": missing_required,
                "message": "Connect required geometry inputs",
            })
        
        # Check Group Input/Output
        has_group_input = False
        has_group_output = False
        group_output_connected = False
        
        for node in node_tree.nodes:
            if node.bl_idname == 'NodeGroupInput':
                has_group_input = True
            elif node.bl_idname == 'NodeGroupOutput':
                has_group_output = True
                group_output_connected = any(inp.is_linked for inp in node.inputs)
        
        if not has_group_output:
            issues.append({
                "severity": "error",
                "type": "group_interface",
                "message": "No Group Output node found",
            })
        elif not group_output_connected:
            issues.append({
                "severity": "warning",
                "type": "group_interface",
                "message": "Group Output has no connected inputs - nothing will be output",
            })
        
        # Statistics
        stats = {
            "total_nodes": len(node_tree.nodes),
            "total_links": len(node_tree.links),
            "orphan_count": len(orphan_nodes),
            "missing_required_count": len(missing_required),
        }
        
        # Determine overall validity
        has_errors = any(issue["severity"] == "error" for issue in issues)
        
        return {
            "node_tree_name": node_tree.name,
            "is_valid": not has_errors,
            "issues": issues,
            "issue_count": len(issues),
            "statistics": stats,
            "suggestions": sorted(suggestions, key=lambda x: x["priority"]),
        }

    def get_node_tree_interface(self, node_tree_name):
        """
        Get the interface (exposed inputs and outputs) of a node tree.
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        inputs = []
        outputs = []
        
        if hasattr(node_tree, 'interface'):
            for item in node_tree.interface.items_tree:
                if item.item_type == 'SOCKET':
                    socket_info = {
                        "name": item.name,
                        "identifier": item.identifier,
                        "socket_type": item.socket_type,
                    }
                    
                    # Try to get default value
                    if hasattr(item, 'default_value'):
                        try:
                            val = item.default_value
                            if hasattr(val, '__iter__') and not isinstance(val, str):
                                socket_info["default_value"] = list(val)
                            else:
                                socket_info["default_value"] = val
                        except:
                            pass
                    
                    if item.in_out == 'INPUT':
                        inputs.append(socket_info)
                    else:
                        outputs.append(socket_info)
        
        return {
            "node_tree_name": node_tree.name,
            "inputs": inputs,
            "outputs": outputs,
        }

    def insert_node_between(self, node_tree_name, from_node, from_socket, to_node, to_socket,
                            new_node_type, new_node_name=None, input_socket=0, output_socket=0,
                            properties=None):
        """
        Insert a new node between two connected nodes.
        
        This removes the existing link and creates:
        from_node[from_socket] -> new_node[input_socket]
        new_node[output_socket] -> to_node[to_socket]
        """
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            raise ValueError(f"Node tree not found: {node_tree_name}")
        
        # Find the source and destination nodes
        src_node = node_tree.nodes.get(from_node)
        if not src_node:
            raise ValueError(f"Source node not found: {from_node}")
        
        dst_node = node_tree.nodes.get(to_node)
        if not dst_node:
            raise ValueError(f"Destination node not found: {to_node}")
        
        # Find the source socket
        if isinstance(from_socket, int):
            if from_socket >= len(src_node.outputs):
                raise ValueError(f"Output index {from_socket} out of range for {from_node}")
            src_socket = src_node.outputs[from_socket]
        else:
            src_socket = src_node.outputs.get(from_socket)
            if not src_socket:
                raise ValueError(f"Output socket '{from_socket}' not found on {from_node}")
        
        # Find the destination socket
        if isinstance(to_socket, int):
            if to_socket >= len(dst_node.inputs):
                raise ValueError(f"Input index {to_socket} out of range for {to_node}")
            dst_socket = dst_node.inputs[to_socket]
        else:
            dst_socket = dst_node.inputs.get(to_socket)
            if not dst_socket:
                raise ValueError(f"Input socket '{to_socket}' not found on {to_node}")
        
        # Find and remove the existing link
        existing_link = None
        for link in node_tree.links:
            if link.from_socket == src_socket and link.to_socket == dst_socket:
                existing_link = link
                break
        
        if not existing_link:
            raise ValueError(f"No link found between {from_node}:{from_socket} and {to_node}:{to_socket}")
        
        # Calculate position for new node (midpoint between source and dest)
        mid_x = (src_node.location.x + dst_node.location.x) / 2
        mid_y = (src_node.location.y + dst_node.location.y) / 2
        
        # Remove the existing link
        node_tree.links.remove(existing_link)
        
        # Create the new node
        try:
            new_node = node_tree.nodes.new(new_node_type)
        except RuntimeError as e:
            # Restore the original link if node creation fails
            node_tree.links.new(src_socket, dst_socket)
            raise ValueError(f"Failed to create node of type '{new_node_type}': {str(e)}")
        
        # Set name and position
        if new_node_name:
            new_node.name = new_node_name
        new_node.location = (mid_x, mid_y)
        
        # Set properties if provided
        if properties:
            for prop_name, prop_value in properties.items():
                if hasattr(new_node, prop_name):
                    try:
                        setattr(new_node, prop_name, prop_value)
                    except Exception as e:
                        print(f"Warning: Could not set property {prop_name}: {e}")
        
        # Find the input socket on new node
        if isinstance(input_socket, int):
            if input_socket >= len(new_node.inputs):
                raise ValueError(f"Input index {input_socket} out of range for new node")
            new_in_socket = new_node.inputs[input_socket]
        else:
            new_in_socket = new_node.inputs.get(input_socket)
            if not new_in_socket:
                raise ValueError(f"Input socket '{input_socket}' not found on new node")
        
        # Find the output socket on new node
        if isinstance(output_socket, int):
            if output_socket >= len(new_node.outputs):
                raise ValueError(f"Output index {output_socket} out of range for new node")
            new_out_socket = new_node.outputs[output_socket]
        else:
            new_out_socket = new_node.outputs.get(output_socket)
            if not new_out_socket:
                raise ValueError(f"Output socket '{output_socket}' not found on new node")
        
        # Create the two new links
        link1 = node_tree.links.new(src_socket, new_in_socket)
        link2 = node_tree.links.new(new_out_socket, dst_socket)
        
        return {
            "success": True,
            "new_node": new_node.name,
            "new_node_type": new_node.bl_idname,
            "location": [new_node.location.x, new_node.location.y],
            "links_created": [
                {
                    "from": f"{from_node}:{src_socket.name}",
                    "to": f"{new_node.name}:{new_in_socket.name}"
                },
                {
                    "from": f"{new_node.name}:{new_out_socket.name}",
                    "to": f"{to_node}:{dst_socket.name}"
                }
            ],
            "link_removed": f"{from_node}:{src_socket.name} -> {to_node}:{dst_socket.name}"
        }

    def get_modifier_details(self, object_name, modifier_name=None):
        """
        Get detailed information about modifiers on an object.
        
        Parameters:
        - object_name: Name of the object
        - modifier_name: Optional specific modifier name
        
        Returns modifier info including type-specific properties.
        """
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}. Available: {[o.name for o in bpy.data.objects]}")
        
        def get_input_value(modifier, identifier):
            """Get the value of a modifier input by identifier"""
            try:
                val = modifier[identifier]
                # Handle different value types
                if val is None:
                    return None
                # Handle Blender ID types (Object, Material, etc.)
                if hasattr(val, 'name') and hasattr(val, 'bl_rna'):
                    return {"type": type(val).__name__, "name": val.name}
                # Handle vectors, colors
                if hasattr(val, '__iter__') and not isinstance(val, str):
                    try:
                        return [float(v) if isinstance(v, (int, float)) else str(v) for v in val]
                    except (TypeError, ValueError):
                        return str(val)
                # Handle simple types
                if isinstance(val, (bool, int, float, str)):
                    return val
                return str(val)
            except (KeyError, TypeError):
                return None
        
        def extract_modifier_info(mod):
            """Extract information from a single modifier"""
            mod_info = {
                "name": mod.name,
                "type": mod.type,
                "show_viewport": mod.show_viewport,
                "show_render": mod.show_render,
            }
            
            # Special handling for Geometry Nodes modifiers
            if mod.type == 'NODES':
                if mod.node_group:
                    mod_info["node_group"] = mod.node_group.name
                    
                    # Get exposed inputs from the node group interface
                    inputs = []
                    if hasattr(mod.node_group, 'interface'):
                        for item in mod.node_group.interface.items_tree:
                            if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
                                input_info = {
                                    "name": item.name,
                                    "identifier": item.identifier,
                                    "socket_type": item.socket_type,
                                }
                                # Get the actual value from the modifier
                                val = get_input_value(mod, item.identifier)
                                if val is not None:
                                    input_info["value"] = val
                                inputs.append(input_info)
                    mod_info["inputs"] = inputs
                    
                    # Get any warnings
                    if hasattr(mod, 'node_warnings') and mod.node_warnings:
                        mod_info["warnings"] = [w.message for w in mod.node_warnings]
                else:
                    mod_info["node_group"] = None
            
            # Add common properties for other modifier types
            elif mod.type == 'SUBSURF':
                mod_info["levels"] = mod.levels
                mod_info["render_levels"] = mod.render_levels
            elif mod.type == 'MIRROR':
                mod_info["use_axis"] = [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]]
            elif mod.type == 'ARRAY':
                mod_info["count"] = mod.count
                mod_info["relative_offset_displace"] = list(mod.relative_offset_displace)
            elif mod.type == 'BEVEL':
                mod_info["width"] = mod.width
                mod_info["segments"] = mod.segments
            elif mod.type == 'SOLIDIFY':
                mod_info["thickness"] = mod.thickness
            
            return mod_info
        
        # If specific modifier requested
        if modifier_name:
            mod = obj.modifiers.get(modifier_name)
            if not mod:
                raise ValueError(f"Modifier not found: {modifier_name}. Available: {[m.name for m in obj.modifiers]}")
            return extract_modifier_info(mod)
        
        # Return all modifiers
        return {
            "object_name": obj.name,
            "modifier_count": len(obj.modifiers),
            "modifiers": [extract_modifier_info(m) for m in obj.modifiers]
        }

    def list_node_trees(self):
        """
        List all node trees (node groups) in the file.
        
        Returns node trees organized by type with usage information.
        """
        # Organize by type
        by_type = {}
        
        for ng in bpy.data.node_groups:
            tree_type = ng.bl_idname
            if tree_type not in by_type:
                by_type[tree_type] = []
            
            tree_info = {
                "name": ng.name,
                "node_count": len(ng.nodes),
                "link_count": len(ng.links),
                "users": [],
            }
            
            # Find what uses this node tree
            # Check modifiers on objects
            for obj in bpy.data.objects:
                for mod in obj.modifiers:
                    if mod.type == 'NODES' and mod.node_group == ng:
                        tree_info["users"].append({
                            "type": "modifier",
                            "object": obj.name,
                            "modifier": mod.name
                        })
            
            # Check if used as a group node inside other node trees
            for other_ng in bpy.data.node_groups:
                if other_ng != ng:
                    for node in other_ng.nodes:
                        if node.bl_idname in ('GeometryNodeGroup', 'ShaderNodeGroup', 'CompositorNodeGroup'):
                            if hasattr(node, 'node_tree') and node.node_tree == ng:
                                tree_info["users"].append({
                                    "type": "node_group",
                                    "parent_tree": other_ng.name,
                                    "node_name": node.name
                                })
            
            by_type[tree_type].append(tree_info)
        
        # Also check material node trees
        material_trees = []
        for mat in bpy.data.materials:
            if mat.use_nodes and mat.node_tree:
                material_trees.append({
                    "name": mat.name,
                    "node_count": len(mat.node_tree.nodes),
                    "link_count": len(mat.node_tree.links),
                    "type": "material"
                })
        
        return {
            "node_groups": by_type,
            "material_node_trees": material_trees,
            "total_node_groups": len(bpy.data.node_groups),
            "total_materials_with_nodes": len(material_trees)
        }

    def list_materials(self):
        """
        List all materials in the file with usage info.
        """
        materials = []
        
        for mat in bpy.data.materials:
            mat_info = {
                "name": mat.name,
                "use_nodes": mat.use_nodes,
                "users": mat.users,
                "used_by": [],
            }
            
            # Find which objects use this material
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.data:
                    for slot in obj.material_slots:
                        if slot.material == mat:
                            mat_info["used_by"].append(obj.name)
                            break
            
            # Basic node tree info if node-based
            if mat.use_nodes and mat.node_tree:
                mat_info["node_count"] = len(mat.node_tree.nodes)
                mat_info["link_count"] = len(mat.node_tree.links)
                
                # Find the main shader type (Principled BSDF, etc.)
                for node in mat.node_tree.nodes:
                    if node.bl_idname in ('ShaderNodeBsdfPrincipled', 'ShaderNodeEmission', 
                                          'ShaderNodeBsdfDiffuse', 'ShaderNodeBsdfGlossy',
                                          'ShaderNodeMixShader', 'ShaderNodeBsdfGlass'):
                        mat_info["main_shader"] = node.bl_idname.replace('ShaderNode', '')
                        break
            
            materials.append(mat_info)
        
        return {
            "material_count": len(materials),
            "materials": materials
        }

    def get_material_nodes(self, material_name, node_name=None):
        """
        Get detailed node information for a material's shader tree.
        """
        mat = bpy.data.materials.get(material_name)
        if not mat:
            raise ValueError(f"Material not found: {material_name}. Available: {[m.name for m in bpy.data.materials]}")
        
        if not mat.use_nodes or not mat.node_tree:
            return {"material_name": material_name, "use_nodes": False, "message": "Material does not use nodes"}
        
        node_tree = mat.node_tree
        
        def get_socket_value(socket):
            """Safely extract socket default value"""
            try:
                if hasattr(socket, 'default_value'):
                    val = socket.default_value
                    if val is None:
                        return None
                    if hasattr(val, 'name') and hasattr(val, 'bl_rna'):
                        return f"<{type(val).__name__}: {val.name}>"
                    if hasattr(val, '__iter__') and not isinstance(val, str):
                        try:
                            return [float(v) if isinstance(v, (int, float)) else str(v) for v in val]
                        except (TypeError, ValueError):
                            return str(val)
                    if isinstance(val, (bool, int, float, str)):
                        return val
                    return str(val)
            except (AttributeError, TypeError, RuntimeError):
                pass
            return None
        
        def extract_node_info(node):
            node_info = {
                "name": node.name,
                "bl_idname": node.bl_idname,
                "label": node.label if node.label else None,
                "location": [round(node.location.x, 2), round(node.location.y, 2)],
                "inputs": [],
                "outputs": [],
            }
            
            # Node-specific properties
            if hasattr(node, 'image') and node.image:
                node_info["image"] = node.image.name
            if hasattr(node, 'color_ramp'):
                node_info["has_color_ramp"] = True
            if hasattr(node, 'blend_type'):
                node_info["blend_type"] = node.blend_type
            if hasattr(node, 'operation'):
                node_info["operation"] = node.operation
            
            for inp in node.inputs:
                socket_info = {
                    "name": inp.name,
                    "type": inp.bl_idname if hasattr(inp, 'bl_idname') else type(inp).__name__,
                    "is_linked": inp.is_linked,
                }
                if not inp.is_linked:
                    val = get_socket_value(inp)
                    if val is not None:
                        socket_info["default_value"] = val
                node_info["inputs"].append(socket_info)
            
            for out in node.outputs:
                socket_info = {
                    "name": out.name,
                    "type": out.bl_idname if hasattr(out, 'bl_idname') else type(out).__name__,
                    "is_linked": out.is_linked,
                }
                node_info["outputs"].append(socket_info)
            
            return node_info
        
        # Get links
        links = []
        for link in node_tree.links:
            links.append({
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name,
            })
        
        if node_name:
            node = node_tree.nodes.get(node_name)
            if not node:
                raise ValueError(f"Node not found: {node_name}. Available: {[n.name for n in node_tree.nodes]}")
            return extract_node_info(node)
        
        return {
            "material_name": mat.name,
            "node_count": len(node_tree.nodes),
            "link_count": len(node_tree.links),
            "nodes": [extract_node_info(n) for n in node_tree.nodes],
            "links": links
        }

    def get_selection(self):
        """
        Get current selection state.
        """
        context = bpy.context
        
        result = {
            "active_object": None,
            "selected_objects": [],
            "selection_count": 0,
            "mode": context.mode,
        }
        
        # Active object
        if context.active_object:
            obj = context.active_object
            result["active_object"] = {
                "name": obj.name,
                "type": obj.type,
                "location": [round(obj.location.x, 4), round(obj.location.y, 4), round(obj.location.z, 4)],
            }
        
        # All selected objects
        for obj in context.selected_objects:
            result["selected_objects"].append({
                "name": obj.name,
                "type": obj.type,
                "is_active": (obj == context.active_object),
            })
        
        result["selection_count"] = len(context.selected_objects)
        
        return result

    def set_selection(self, object_names, mode="replace", active=None):
        """
        Set object selection.
        """
        # Validate mode
        if mode not in ("replace", "add", "remove"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'replace', 'add', or 'remove'")
        
        # Validate object names exist
        not_found = []
        objects = []
        for name in object_names:
            obj = bpy.data.objects.get(name)
            if obj:
                objects.append(obj)
            else:
                not_found.append(name)
        
        if not_found:
            raise ValueError(f"Objects not found: {not_found}. Available: {[o.name for o in bpy.data.objects]}")
        
        # Apply selection based on mode
        if mode == "replace":
            # Deselect all first
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
        elif mode == "add":
            for obj in objects:
                obj.select_set(True)
        elif mode == "remove":
            for obj in objects:
                obj.select_set(False)
        
        # Set active object if specified
        if active:
            active_obj = bpy.data.objects.get(active)
            if not active_obj:
                raise ValueError(f"Active object not found: {active}")
            if not active_obj.select_get():
                raise ValueError(f"Active object must be selected: {active}")
            bpy.context.view_layer.objects.active = active_obj
        elif mode == "replace" and objects:
            # Default: make first object active
            bpy.context.view_layer.objects.active = objects[0]
        
        # Return new selection state
        return self.get_selection()

    def batch_rename(self, object_names=None, use_selection=False, new_base_name=None,
                     find=None, replace=None, prefix=None, suffix=None,
                     number_start=1, number_padding=2):
        """
        Batch rename objects with various modes.
        """
        # Get target objects
        if use_selection:
            objects = list(bpy.context.selected_objects)
        elif object_names:
            objects = []
            not_found = []
            for name in object_names:
                obj = bpy.data.objects.get(name)
                if obj:
                    objects.append(obj)
                else:
                    not_found.append(name)
            if not_found:
                raise ValueError(f"Objects not found: {not_found}")
        else:
            raise ValueError("Must provide object_names or use_selection=True")
        
        if not objects:
            raise ValueError("No objects to rename")
        
        renames = []
        
        # Determine rename mode
        if new_base_name:
            # Sequential naming: BaseName.01, BaseName.02, etc.
            for i, obj in enumerate(objects):
                old_name = obj.name
                num = str(number_start + i).zfill(number_padding)
                new_name = f"{new_base_name}.{num}"
                obj.name = new_name
                renames.append({"old": old_name, "new": obj.name})
        
        elif find is not None and replace is not None:
            # Find/replace mode
            for obj in objects:
                old_name = obj.name
                if find in old_name:
                    new_name = old_name.replace(find, replace)
                    obj.name = new_name
                    renames.append({"old": old_name, "new": obj.name})
                else:
                    renames.append({"old": old_name, "new": old_name, "skipped": "pattern not found"})
        
        elif prefix:
            # Add prefix
            for obj in objects:
                old_name = obj.name
                new_name = f"{prefix}{old_name}"
                obj.name = new_name
                renames.append({"old": old_name, "new": obj.name})
        
        elif suffix:
            # Add suffix
            for obj in objects:
                old_name = obj.name
                new_name = f"{old_name}{suffix}"
                obj.name = new_name
                renames.append({"old": old_name, "new": obj.name})
        
        else:
            raise ValueError("Must specify a rename mode: new_base_name, find/replace, prefix, or suffix")
        
        return {
            "renamed_count": len([r for r in renames if r.get("old") != r.get("new")]),
            "total_processed": len(renames),
            "renames": renames
        }

    def get_viewport_screenshot(self, max_size=800, filepath=None, format="png"):
        """
        Capture a screenshot of the current 3D viewport and save it to the specified path.

        Parameters:
        - max_size: Maximum size in pixels for the largest dimension of the image
        - filepath: Path where to save the screenshot file
        - format: Image format (png, jpg, etc.)

        Returns success/error status
        """
        try:
            if not filepath:
                return {"error": "No filepath provided"}

            # Find the active 3D viewport
            area = None
            for a in bpy.context.screen.areas:
                if a.type == 'VIEW_3D':
                    area = a
                    break

            if not area:
                return {"error": "No 3D viewport found"}

            # Take screenshot with proper context override
            with bpy.context.temp_override(area=area):
                bpy.ops.screen.screenshot_area(filepath=filepath)

            # Load and resize if needed
            img = bpy.data.images.load(filepath)
            width, height = img.size

            if max(width, height) > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img.scale(new_width, new_height)

                # Set format and save
                img.file_format = format.upper()
                img.save()
                width, height = new_width, new_height

            # Cleanup Blender image data
            bpy.data.images.remove(img)

            return {
                "success": True,
                "width": width,
                "height": height,
                "filepath": filepath
            }

        except Exception as e:
            return {"error": str(e)}

    def execute_code(self, code):
        """Execute arbitrary Blender Python code"""
        # This is powerful but potentially dangerous - use with caution
        try:
            # Create a local namespace for execution
            namespace = {"bpy": bpy}

            # Capture stdout during execution, and return it as result
            capture_buffer = io.StringIO()
            with redirect_stdout(capture_buffer):
                exec(code, namespace)

            captured_output = capture_buffer.getvalue()
            return {"executed": True, "result": captured_output}
        except Exception as e:
            raise Exception(f"Code execution error: {str(e)}")



    def get_polyhaven_categories(self, asset_type):
        """Get categories for a specific asset type from Polyhaven"""
        try:
            if asset_type not in ["hdris", "textures", "models", "all"]:
                return {"error": f"Invalid asset type: {asset_type}. Must be one of: hdris, textures, models, all"}

            response = requests.get(f"https://api.polyhaven.com/categories/{asset_type}", headers=REQ_HEADERS)
            if response.status_code == 200:
                return {"categories": response.json()}
            else:
                return {"error": f"API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def search_polyhaven_assets(self, asset_type=None, categories=None):
        """Search for assets from Polyhaven with optional filtering"""
        try:
            url = "https://api.polyhaven.com/assets"
            params = {}

            if asset_type and asset_type != "all":
                if asset_type not in ["hdris", "textures", "models"]:
                    return {"error": f"Invalid asset type: {asset_type}. Must be one of: hdris, textures, models, all"}
                params["type"] = asset_type

            if categories:
                params["categories"] = categories

            response = requests.get(url, params=params, headers=REQ_HEADERS)
            if response.status_code == 200:
                # Limit the response size to avoid overwhelming Blender
                assets = response.json()
                # Return only the first 20 assets to keep response size manageable
                limited_assets = {}
                for i, (key, value) in enumerate(assets.items()):
                    if i >= 20:  # Limit to 20 assets
                        break
                    limited_assets[key] = value

                return {"assets": limited_assets, "total_count": len(assets), "returned_count": len(limited_assets)}
            else:
                return {"error": f"API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def download_polyhaven_asset(self, asset_id, asset_type, resolution="1k", file_format=None):
        try:
            # First get the files information
            files_response = requests.get(f"https://api.polyhaven.com/files/{asset_id}", headers=REQ_HEADERS)
            if files_response.status_code != 200:
                return {"error": f"Failed to get asset files: {files_response.status_code}"}

            files_data = files_response.json()

            # Handle different asset types
            if asset_type == "hdris":
                # For HDRIs, download the .hdr or .exr file
                if not file_format:
                    file_format = "hdr"  # Default format for HDRIs

                if "hdri" in files_data and resolution in files_data["hdri"] and file_format in files_data["hdri"][resolution]:
                    file_info = files_data["hdri"][resolution][file_format]
                    file_url = file_info["url"]

                    # For HDRIs, we need to save to a temporary file first
                    # since Blender can't properly load HDR data directly from memory
                    with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
                        # Download the file
                        response = requests.get(file_url, headers=REQ_HEADERS)
                        if response.status_code != 200:
                            return {"error": f"Failed to download HDRI: {response.status_code}"}

                        tmp_file.write(response.content)
                        tmp_path = tmp_file.name

                    try:
                        # Create a new world if none exists
                        if not bpy.data.worlds:
                            bpy.data.worlds.new("World")

                        world = bpy.data.worlds[0]
                        world.use_nodes = True
                        node_tree = world.node_tree

                        # Clear existing nodes
                        for node in node_tree.nodes:
                            node_tree.nodes.remove(node)

                        # Create nodes
                        tex_coord = node_tree.nodes.new(type='ShaderNodeTexCoord')
                        tex_coord.location = (-800, 0)

                        mapping = node_tree.nodes.new(type='ShaderNodeMapping')
                        mapping.location = (-600, 0)

                        # Load the image from the temporary file
                        env_tex = node_tree.nodes.new(type='ShaderNodeTexEnvironment')
                        env_tex.location = (-400, 0)
                        env_tex.image = bpy.data.images.load(tmp_path)

                        # Use a color space that exists in all Blender versions
                        if file_format.lower() == 'exr':
                            # Try to use Linear color space for EXR files
                            try:
                                env_tex.image.colorspace_settings.name = 'Linear'
                            except:
                                # Fallback to Non-Color if Linear isn't available
                                env_tex.image.colorspace_settings.name = 'Non-Color'
                        else:  # hdr
                            # For HDR files, try these options in order
                            for color_space in ['Linear', 'Linear Rec.709', 'Non-Color']:
                                try:
                                    env_tex.image.colorspace_settings.name = color_space
                                    break  # Stop if we successfully set a color space
                                except:
                                    continue

                        background = node_tree.nodes.new(type='ShaderNodeBackground')
                        background.location = (-200, 0)

                        output = node_tree.nodes.new(type='ShaderNodeOutputWorld')
                        output.location = (0, 0)

                        # Connect nodes
                        node_tree.links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
                        node_tree.links.new(mapping.outputs['Vector'], env_tex.inputs['Vector'])
                        node_tree.links.new(env_tex.outputs['Color'], background.inputs['Color'])
                        node_tree.links.new(background.outputs['Background'], output.inputs['Surface'])

                        # Set as active world
                        bpy.context.scene.world = world

                        # Clean up temporary file
                        try:
                            tempfile._cleanup()  # This will clean up all temporary files
                        except:
                            pass

                        return {
                            "success": True,
                            "message": f"HDRI {asset_id} imported successfully",
                            "image_name": env_tex.image.name
                        }
                    except Exception as e:
                        return {"error": f"Failed to set up HDRI in Blender: {str(e)}"}
                else:
                    return {"error": f"Requested resolution or format not available for this HDRI"}

            elif asset_type == "textures":
                if not file_format:
                    file_format = "jpg"  # Default format for textures

                downloaded_maps = {}

                try:
                    for map_type in files_data:
                        if map_type not in ["blend", "gltf"]:  # Skip non-texture files
                            if resolution in files_data[map_type] and file_format in files_data[map_type][resolution]:
                                file_info = files_data[map_type][resolution][file_format]
                                file_url = file_info["url"]

                                # Use NamedTemporaryFile like we do for HDRIs
                                with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
                                    # Download the file
                                    response = requests.get(file_url, headers=REQ_HEADERS)
                                    if response.status_code == 200:
                                        tmp_file.write(response.content)
                                        tmp_path = tmp_file.name

                                        # Load image from temporary file
                                        image = bpy.data.images.load(tmp_path)
                                        image.name = f"{asset_id}_{map_type}.{file_format}"

                                        # Pack the image into .blend file
                                        image.pack()

                                        # Set color space based on map type
                                        if map_type in ['color', 'diffuse', 'albedo']:
                                            try:
                                                image.colorspace_settings.name = 'sRGB'
                                            except:
                                                pass
                                        else:
                                            try:
                                                image.colorspace_settings.name = 'Non-Color'
                                            except:
                                                pass

                                        downloaded_maps[map_type] = image

                                        # Clean up temporary file
                                        try:
                                            os.unlink(tmp_path)
                                        except:
                                            pass

                    if not downloaded_maps:
                        return {"error": f"No texture maps found for the requested resolution and format"}

                    # Create a new material with the downloaded textures
                    mat = bpy.data.materials.new(name=asset_id)
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links

                    # Clear default nodes
                    for node in nodes:
                        nodes.remove(node)

                    # Create output node
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (300, 0)

                    # Create principled BSDF node
                    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
                    principled.location = (0, 0)
                    links.new(principled.outputs[0], output.inputs[0])

                    # Add texture nodes based on available maps
                    tex_coord = nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = (-800, 0)

                    mapping = nodes.new(type='ShaderNodeMapping')
                    mapping.location = (-600, 0)
                    mapping.vector_type = 'TEXTURE'  # Changed from default 'POINT' to 'TEXTURE'
                    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

                    # Position offset for texture nodes
                    x_pos = -400
                    y_pos = 300

                    # Connect different texture maps
                    for map_type, image in downloaded_maps.items():
                        tex_node = nodes.new(type='ShaderNodeTexImage')
                        tex_node.location = (x_pos, y_pos)
                        tex_node.image = image

                        # Set color space based on map type
                        if map_type.lower() in ['color', 'diffuse', 'albedo']:
                            try:
                                tex_node.image.colorspace_settings.name = 'sRGB'
                            except:
                                pass  # Use default if sRGB not available
                        else:
                            try:
                                tex_node.image.colorspace_settings.name = 'Non-Color'
                            except:
                                pass  # Use default if Non-Color not available

                        links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])

                        # Connect to appropriate input on Principled BSDF
                        if map_type.lower() in ['color', 'diffuse', 'albedo']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                        elif map_type.lower() in ['roughness', 'rough']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                        elif map_type.lower() in ['metallic', 'metalness', 'metal']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                        elif map_type.lower() in ['normal', 'nor']:
                            # Add normal map node
                            normal_map = nodes.new(type='ShaderNodeNormalMap')
                            normal_map.location = (x_pos + 200, y_pos)
                            links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                        elif map_type in ['displacement', 'disp', 'height']:
                            # Add displacement node
                            disp_node = nodes.new(type='ShaderNodeDisplacement')
                            disp_node.location = (x_pos + 200, y_pos - 200)
                            links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                            links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])

                        y_pos -= 250

                    return {
                        "success": True,
                        "message": f"Texture {asset_id} imported as material",
                        "material": mat.name,
                        "maps": list(downloaded_maps.keys())
                    }

                except Exception as e:
                    return {"error": f"Failed to process textures: {str(e)}"}

            elif asset_type == "models":
                # For models, prefer glTF format if available
                if not file_format:
                    file_format = "gltf"  # Default format for models

                if file_format in files_data and resolution in files_data[file_format]:
                    file_info = files_data[file_format][resolution][file_format]
                    file_url = file_info["url"]

                    # Create a temporary directory to store the model and its dependencies
                    temp_dir = tempfile.mkdtemp()
                    main_file_path = ""

                    try:
                        # Download the main model file
                        main_file_name = file_url.split("/")[-1]
                        main_file_path = os.path.join(temp_dir, main_file_name)

                        response = requests.get(file_url, headers=REQ_HEADERS)
                        if response.status_code != 200:
                            return {"error": f"Failed to download model: {response.status_code}"}

                        with open(main_file_path, "wb") as f:
                            f.write(response.content)

                        # Check for included files and download them
                        if "include" in file_info and file_info["include"]:
                            for include_path, include_info in file_info["include"].items():
                                # Get the URL for the included file - this is the fix
                                include_url = include_info["url"]

                                # Create the directory structure for the included file
                                include_file_path = os.path.join(temp_dir, include_path)
                                os.makedirs(os.path.dirname(include_file_path), exist_ok=True)

                                # Download the included file
                                include_response = requests.get(include_url, headers=REQ_HEADERS)
                                if include_response.status_code == 200:
                                    with open(include_file_path, "wb") as f:
                                        f.write(include_response.content)
                                else:
                                    print(f"Failed to download included file: {include_path}")

                        # Import the model into Blender
                        if file_format == "gltf" or file_format == "glb":
                            bpy.ops.import_scene.gltf(filepath=main_file_path)
                        elif file_format == "fbx":
                            bpy.ops.import_scene.fbx(filepath=main_file_path)
                        elif file_format == "obj":
                            bpy.ops.import_scene.obj(filepath=main_file_path)
                        elif file_format == "blend":
                            # For blend files, we need to append or link
                            with bpy.data.libraries.load(main_file_path, link=False) as (data_from, data_to):
                                data_to.objects = data_from.objects

                            # Link the objects to the scene
                            for obj in data_to.objects:
                                if obj is not None:
                                    bpy.context.collection.objects.link(obj)
                        else:
                            return {"error": f"Unsupported model format: {file_format}"}

                        # Get the names of imported objects
                        imported_objects = [obj.name for obj in bpy.context.selected_objects]

                        return {
                            "success": True,
                            "message": f"Model {asset_id} imported successfully",
                            "imported_objects": imported_objects
                        }
                    except Exception as e:
                        return {"error": f"Failed to import model: {str(e)}"}
                    finally:
                        # Clean up temporary directory
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                else:
                    return {"error": f"Requested format or resolution not available for this model"}

            else:
                return {"error": f"Unsupported asset type: {asset_type}"}

        except Exception as e:
            return {"error": f"Failed to download asset: {str(e)}"}

    def set_texture(self, object_name, texture_id):
        """Apply a previously downloaded Polyhaven texture to an object by creating a new material"""
        try:
            # Get the object
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"Object not found: {object_name}"}

            # Make sure object can accept materials
            if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                return {"error": f"Object {object_name} cannot accept materials"}

            # Find all images related to this texture and ensure they're properly loaded
            texture_images = {}
            for img in bpy.data.images:
                if img.name.startswith(texture_id + "_"):
                    # Extract the map type from the image name
                    map_type = img.name.split('_')[-1].split('.')[0]

                    # Force a reload of the image
                    img.reload()

                    # Ensure proper color space
                    if map_type.lower() in ['color', 'diffuse', 'albedo']:
                        try:
                            img.colorspace_settings.name = 'sRGB'
                        except:
                            pass
                    else:
                        try:
                            img.colorspace_settings.name = 'Non-Color'
                        except:
                            pass

                    # Ensure the image is packed
                    if not img.packed_file:
                        img.pack()

                    texture_images[map_type] = img
                    print(f"Loaded texture map: {map_type} - {img.name}")

                    # Debug info
                    print(f"Image size: {img.size[0]}x{img.size[1]}")
                    print(f"Color space: {img.colorspace_settings.name}")
                    print(f"File format: {img.file_format}")
                    print(f"Is packed: {bool(img.packed_file)}")

            if not texture_images:
                return {"error": f"No texture images found for: {texture_id}. Please download the texture first."}

            # Create a new material
            new_mat_name = f"{texture_id}_material_{object_name}"

            # Remove any existing material with this name to avoid conflicts
            existing_mat = bpy.data.materials.get(new_mat_name)
            if existing_mat:
                bpy.data.materials.remove(existing_mat)

            new_mat = bpy.data.materials.new(name=new_mat_name)
            new_mat.use_nodes = True

            # Set up the material nodes
            nodes = new_mat.node_tree.nodes
            links = new_mat.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create output node
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (600, 0)

            # Create principled BSDF node
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (300, 0)
            links.new(principled.outputs[0], output.inputs[0])

            # Add texture nodes based on available maps
            tex_coord = nodes.new(type='ShaderNodeTexCoord')
            tex_coord.location = (-800, 0)

            mapping = nodes.new(type='ShaderNodeMapping')
            mapping.location = (-600, 0)
            mapping.vector_type = 'TEXTURE'  # Changed from default 'POINT' to 'TEXTURE'
            links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

            # Position offset for texture nodes
            x_pos = -400
            y_pos = 300

            # Connect different texture maps
            for map_type, image in texture_images.items():
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (x_pos, y_pos)
                tex_node.image = image

                # Set color space based on map type
                if map_type.lower() in ['color', 'diffuse', 'albedo']:
                    try:
                        tex_node.image.colorspace_settings.name = 'sRGB'
                    except:
                        pass  # Use default if sRGB not available
                else:
                    try:
                        tex_node.image.colorspace_settings.name = 'Non-Color'
                    except:
                        pass  # Use default if Non-Color not available

                links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])

                # Connect to appropriate input on Principled BSDF
                if map_type.lower() in ['color', 'diffuse', 'albedo']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                elif map_type.lower() in ['roughness', 'rough']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                elif map_type.lower() in ['metallic', 'metalness', 'metal']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                elif map_type.lower() in ['normal', 'nor', 'dx', 'gl']:
                    # Add normal map node
                    normal_map = nodes.new(type='ShaderNodeNormalMap')
                    normal_map.location = (x_pos + 200, y_pos)
                    links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                    links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                elif map_type.lower() in ['displacement', 'disp', 'height']:
                    # Add displacement node
                    disp_node = nodes.new(type='ShaderNodeDisplacement')
                    disp_node.location = (x_pos + 200, y_pos - 200)
                    disp_node.inputs['Scale'].default_value = 0.1  # Reduce displacement strength
                    links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                    links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])

                y_pos -= 250

            # Second pass: Connect nodes with proper handling for special cases
            texture_nodes = {}

            # First find all texture nodes and store them by map type
            for node in nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    for map_type, image in texture_images.items():
                        if node.image == image:
                            texture_nodes[map_type] = node
                            break

            # Now connect everything using the nodes instead of images
            # Handle base color (diffuse)
            for map_name in ['color', 'diffuse', 'albedo']:
                if map_name in texture_nodes:
                    links.new(texture_nodes[map_name].outputs['Color'], principled.inputs['Base Color'])
                    print(f"Connected {map_name} to Base Color")
                    break

            # Handle roughness
            for map_name in ['roughness', 'rough']:
                if map_name in texture_nodes:
                    links.new(texture_nodes[map_name].outputs['Color'], principled.inputs['Roughness'])
                    print(f"Connected {map_name} to Roughness")
                    break

            # Handle metallic
            for map_name in ['metallic', 'metalness', 'metal']:
                if map_name in texture_nodes:
                    links.new(texture_nodes[map_name].outputs['Color'], principled.inputs['Metallic'])
                    print(f"Connected {map_name} to Metallic")
                    break

            # Handle normal maps
            for map_name in ['gl', 'dx', 'nor']:
                if map_name in texture_nodes:
                    normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                    normal_map_node.location = (100, 100)
                    links.new(texture_nodes[map_name].outputs['Color'], normal_map_node.inputs['Color'])
                    links.new(normal_map_node.outputs['Normal'], principled.inputs['Normal'])
                    print(f"Connected {map_name} to Normal")
                    break

            # Handle displacement
            for map_name in ['displacement', 'disp', 'height']:
                if map_name in texture_nodes:
                    disp_node = nodes.new(type='ShaderNodeDisplacement')
                    disp_node.location = (300, -200)
                    disp_node.inputs['Scale'].default_value = 0.1  # Reduce displacement strength
                    links.new(texture_nodes[map_name].outputs['Color'], disp_node.inputs['Height'])
                    links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])
                    print(f"Connected {map_name} to Displacement")
                    break

            # Handle ARM texture (Ambient Occlusion, Roughness, Metallic)
            if 'arm' in texture_nodes:
                separate_rgb = nodes.new(type='ShaderNodeSeparateRGB')
                separate_rgb.location = (-200, -100)
                links.new(texture_nodes['arm'].outputs['Color'], separate_rgb.inputs['Image'])

                # Connect Roughness (G) if no dedicated roughness map
                if not any(map_name in texture_nodes for map_name in ['roughness', 'rough']):
                    links.new(separate_rgb.outputs['G'], principled.inputs['Roughness'])
                    print("Connected ARM.G to Roughness")

                # Connect Metallic (B) if no dedicated metallic map
                if not any(map_name in texture_nodes for map_name in ['metallic', 'metalness', 'metal']):
                    links.new(separate_rgb.outputs['B'], principled.inputs['Metallic'])
                    print("Connected ARM.B to Metallic")

                # For AO (R channel), multiply with base color if we have one
                base_color_node = None
                for map_name in ['color', 'diffuse', 'albedo']:
                    if map_name in texture_nodes:
                        base_color_node = texture_nodes[map_name]
                        break

                if base_color_node:
                    mix_node = nodes.new(type='ShaderNodeMixRGB')
                    mix_node.location = (100, 200)
                    mix_node.blend_type = 'MULTIPLY'
                    mix_node.inputs['Fac'].default_value = 0.8  # 80% influence

                    # Disconnect direct connection to base color
                    for link in base_color_node.outputs['Color'].links:
                        if link.to_socket == principled.inputs['Base Color']:
                            links.remove(link)

                    # Connect through the mix node
                    links.new(base_color_node.outputs['Color'], mix_node.inputs[1])
                    links.new(separate_rgb.outputs['R'], mix_node.inputs[2])
                    links.new(mix_node.outputs['Color'], principled.inputs['Base Color'])
                    print("Connected ARM.R to AO mix with Base Color")

            # Handle AO (Ambient Occlusion) if separate
            if 'ao' in texture_nodes:
                base_color_node = None
                for map_name in ['color', 'diffuse', 'albedo']:
                    if map_name in texture_nodes:
                        base_color_node = texture_nodes[map_name]
                        break

                if base_color_node:
                    mix_node = nodes.new(type='ShaderNodeMixRGB')
                    mix_node.location = (100, 200)
                    mix_node.blend_type = 'MULTIPLY'
                    mix_node.inputs['Fac'].default_value = 0.8  # 80% influence

                    # Disconnect direct connection to base color
                    for link in base_color_node.outputs['Color'].links:
                        if link.to_socket == principled.inputs['Base Color']:
                            links.remove(link)

                    # Connect through the mix node
                    links.new(base_color_node.outputs['Color'], mix_node.inputs[1])
                    links.new(texture_nodes['ao'].outputs['Color'], mix_node.inputs[2])
                    links.new(mix_node.outputs['Color'], principled.inputs['Base Color'])
                    print("Connected AO to mix with Base Color")

            # CRITICAL: Make sure to clear all existing materials from the object
            while len(obj.data.materials) > 0:
                obj.data.materials.pop(index=0)

            # Assign the new material to the object
            obj.data.materials.append(new_mat)

            # CRITICAL: Make the object active and select it
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            # CRITICAL: Force Blender to update the material
            bpy.context.view_layer.update()

            # Get the list of texture maps
            texture_maps = list(texture_images.keys())

            # Get info about texture nodes for debugging
            material_info = {
                "name": new_mat.name,
                "has_nodes": new_mat.use_nodes,
                "node_count": len(new_mat.node_tree.nodes),
                "texture_nodes": []
            }

            for node in new_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    connections = []
                    for output in node.outputs:
                        for link in output.links:
                            connections.append(f"{output.name} → {link.to_node.name}.{link.to_socket.name}")

                    material_info["texture_nodes"].append({
                        "name": node.name,
                        "image": node.image.name,
                        "colorspace": node.image.colorspace_settings.name,
                        "connections": connections
                    })

            return {
                "success": True,
                "message": f"Created new material and applied texture {texture_id} to {object_name}",
                "material": new_mat.name,
                "maps": texture_maps,
                "material_info": material_info
            }

        except Exception as e:
            print(f"Error in set_texture: {str(e)}")
            traceback.print_exc()
            return {"error": f"Failed to apply texture: {str(e)}"}

    def get_polyhaven_status(self):
        """Get the current status of PolyHaven integration"""
        enabled = bpy.context.scene.blendermcp_use_polyhaven
        if enabled:
            return {"enabled": True, "message": "PolyHaven integration is enabled and ready to use."}
        else:
            return {
                "enabled": False,
                "message": """PolyHaven integration is currently disabled. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Check the 'Use assets from Poly Haven' checkbox
                            3. Restart the connection to Claude"""
        }

    #region Hyper3D
    def get_hyper3d_status(self):
        """Get the current status of Hyper3D Rodin integration"""
        enabled = bpy.context.scene.blendermcp_use_hyper3d
        if enabled:
            if not bpy.context.scene.blendermcp_hyper3d_api_key:
                return {
                    "enabled": False,
                    "message": """Hyper3D Rodin integration is currently enabled, but API key is not given. To enable it:
                                1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                                2. Keep the 'Use Hyper3D Rodin 3D model generation' checkbox checked
                                3. Choose the right plaform and fill in the API Key
                                4. Restart the connection to Claude"""
                }
            mode = bpy.context.scene.blendermcp_hyper3d_mode
            message = f"Hyper3D Rodin integration is enabled and ready to use. Mode: {mode}. " + \
                f"Key type: {'private' if bpy.context.scene.blendermcp_hyper3d_api_key != RODIN_FREE_TRIAL_KEY else 'free_trial'}"
            return {
                "enabled": True,
                "message": message
            }
        else:
            return {
                "enabled": False,
                "message": """Hyper3D Rodin integration is currently disabled. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Check the 'Use Hyper3D Rodin 3D model generation' checkbox
                            3. Restart the connection to Claude"""
            }

    def create_rodin_job(self, *args, **kwargs):
        match bpy.context.scene.blendermcp_hyper3d_mode:
            case "MAIN_SITE":
                return self.create_rodin_job_main_site(*args, **kwargs)
            case "FAL_AI":
                return self.create_rodin_job_fal_ai(*args, **kwargs)
            case _:
                return f"Error: Unknown Hyper3D Rodin mode!"

    def create_rodin_job_main_site(
            self,
            text_prompt: str=None,
            images: list[tuple[str, str]]=None,
            bbox_condition=None
        ):
        try:
            if images is None:
                images = []
            """Call Rodin API, get the job uuid and subscription key"""
            files = [
                *[("images", (f"{i:04d}{img_suffix}", img)) for i, (img_suffix, img) in enumerate(images)],
                ("tier", (None, "Sketch")),
                ("mesh_mode", (None, "Raw")),
            ]
            if text_prompt:
                files.append(("prompt", (None, text_prompt)))
            if bbox_condition:
                files.append(("bbox_condition", (None, json.dumps(bbox_condition))))
            response = requests.post(
                "https://hyperhuman.deemos.com/api/v2/rodin",
                headers={
                    "Authorization": f"Bearer {bpy.context.scene.blendermcp_hyper3d_api_key}",
                },
                files=files
            )
            data = response.json()
            return data
        except Exception as e:
            return {"error": str(e)}

    def create_rodin_job_fal_ai(
            self,
            text_prompt: str=None,
            images: list[tuple[str, str]]=None,
            bbox_condition=None
        ):
        try:
            req_data = {
                "tier": "Sketch",
            }
            if images:
                req_data["input_image_urls"] = images
            if text_prompt:
                req_data["prompt"] = text_prompt
            if bbox_condition:
                req_data["bbox_condition"] = bbox_condition
            response = requests.post(
                "https://queue.fal.run/fal-ai/hyper3d/rodin",
                headers={
                    "Authorization": f"Key {bpy.context.scene.blendermcp_hyper3d_api_key}",
                    "Content-Type": "application/json",
                },
                json=req_data
            )
            data = response.json()
            return data
        except Exception as e:
            return {"error": str(e)}

    def poll_rodin_job_status(self, *args, **kwargs):
        match bpy.context.scene.blendermcp_hyper3d_mode:
            case "MAIN_SITE":
                return self.poll_rodin_job_status_main_site(*args, **kwargs)
            case "FAL_AI":
                return self.poll_rodin_job_status_fal_ai(*args, **kwargs)
            case _:
                return f"Error: Unknown Hyper3D Rodin mode!"

    def poll_rodin_job_status_main_site(self, subscription_key: str):
        """Call the job status API to get the job status"""
        response = requests.post(
            "https://hyperhuman.deemos.com/api/v2/status",
            headers={
                "Authorization": f"Bearer {bpy.context.scene.blendermcp_hyper3d_api_key}",
            },
            json={
                "subscription_key": subscription_key,
            },
        )
        data = response.json()
        return {
            "status_list": [i["status"] for i in data["jobs"]]
        }

    def poll_rodin_job_status_fal_ai(self, request_id: str):
        """Call the job status API to get the job status"""
        response = requests.get(
            f"https://queue.fal.run/fal-ai/hyper3d/requests/{request_id}/status",
            headers={
                "Authorization": f"KEY {bpy.context.scene.blendermcp_hyper3d_api_key}",
            },
        )
        data = response.json()
        return data

    @staticmethod
    def _clean_imported_glb(filepath, mesh_name=None):
        # Get the set of existing objects before import
        existing_objects = set(bpy.data.objects)

        # Import the GLB file
        bpy.ops.import_scene.gltf(filepath=filepath)

        # Ensure the context is updated
        bpy.context.view_layer.update()

        # Get all imported objects
        imported_objects = list(set(bpy.data.objects) - existing_objects)
        # imported_objects = [obj for obj in bpy.context.view_layer.objects if obj.select_get()]

        if not imported_objects:
            print("Error: No objects were imported.")
            return

        # Identify the mesh object
        mesh_obj = None

        if len(imported_objects) == 1 and imported_objects[0].type == 'MESH':
            mesh_obj = imported_objects[0]
            print("Single mesh imported, no cleanup needed.")
        else:
            if len(imported_objects) == 2:
                empty_objs = [i for i in imported_objects if i.type == "EMPTY"]
                if len(empty_objs) != 1:
                    print("Error: Expected an empty node with one mesh child or a single mesh object.")
                    return
                parent_obj = empty_objs.pop()
                if len(parent_obj.children) == 1:
                    potential_mesh = parent_obj.children[0]
                    if potential_mesh.type == 'MESH':
                        print("GLB structure confirmed: Empty node with one mesh child.")

                        # Unparent the mesh from the empty node
                        potential_mesh.parent = None

                        # Remove the empty node
                        bpy.data.objects.remove(parent_obj)
                        print("Removed empty node, keeping only the mesh.")

                        mesh_obj = potential_mesh
                    else:
                        print("Error: Child is not a mesh object.")
                        return
                else:
                    print("Error: Expected an empty node with one mesh child or a single mesh object.")
                    return
            else:
                print("Error: Expected an empty node with one mesh child or a single mesh object.")
                return

        # Rename the mesh if needed
        try:
            if mesh_obj and mesh_obj.name is not None and mesh_name:
                mesh_obj.name = mesh_name
                if mesh_obj.data.name is not None:
                    mesh_obj.data.name = mesh_name
                print(f"Mesh renamed to: {mesh_name}")
        except Exception as e:
            print("Having issue with renaming, give up renaming.")

        return mesh_obj

    def import_generated_asset(self, *args, **kwargs):
        match bpy.context.scene.blendermcp_hyper3d_mode:
            case "MAIN_SITE":
                return self.import_generated_asset_main_site(*args, **kwargs)
            case "FAL_AI":
                return self.import_generated_asset_fal_ai(*args, **kwargs)
            case _:
                return f"Error: Unknown Hyper3D Rodin mode!"

    def import_generated_asset_main_site(self, task_uuid: str, name: str):
        """Fetch the generated asset, import into blender"""
        response = requests.post(
            "https://hyperhuman.deemos.com/api/v2/download",
            headers={
                "Authorization": f"Bearer {bpy.context.scene.blendermcp_hyper3d_api_key}",
            },
            json={
                'task_uuid': task_uuid
            }
        )
        data_ = response.json()
        temp_file = None
        for i in data_["list"]:
            if i["name"].endswith(".glb"):
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    prefix=task_uuid,
                    suffix=".glb",
                )

                try:
                    # Download the content
                    response = requests.get(i["url"], stream=True)
                    response.raise_for_status()  # Raise an exception for HTTP errors

                    # Write the content to the temporary file
                    for chunk in response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)

                    # Close the file
                    temp_file.close()

                except Exception as e:
                    # Clean up the file if there's an error
                    temp_file.close()
                    os.unlink(temp_file.name)
                    return {"succeed": False, "error": str(e)}

                break
        else:
            return {"succeed": False, "error": "Generation failed. Please first make sure that all jobs of the task are done and then try again later."}

        try:
            obj = self._clean_imported_glb(
                filepath=temp_file.name,
                mesh_name=name
            )
            result = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            }

            if obj.type == "MESH":
                bounding_box = self._get_aabb(obj)
                result["world_bounding_box"] = bounding_box

            return {
                "succeed": True, **result
            }
        except Exception as e:
            return {"succeed": False, "error": str(e)}

    def import_generated_asset_fal_ai(self, request_id: str, name: str):
        """Fetch the generated asset, import into blender"""
        response = requests.get(
            f"https://queue.fal.run/fal-ai/hyper3d/requests/{request_id}",
            headers={
                "Authorization": f"Key {bpy.context.scene.blendermcp_hyper3d_api_key}",
            }
        )
        data_ = response.json()
        temp_file = None

        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            prefix=request_id,
            suffix=".glb",
        )

        try:
            # Download the content
            response = requests.get(data_["model_mesh"]["url"], stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Write the content to the temporary file
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)

            # Close the file
            temp_file.close()

        except Exception as e:
            # Clean up the file if there's an error
            temp_file.close()
            os.unlink(temp_file.name)
            return {"succeed": False, "error": str(e)}

        try:
            obj = self._clean_imported_glb(
                filepath=temp_file.name,
                mesh_name=name
            )
            result = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            }

            if obj.type == "MESH":
                bounding_box = self._get_aabb(obj)
                result["world_bounding_box"] = bounding_box

            return {
                "succeed": True, **result
            }
        except Exception as e:
            return {"succeed": False, "error": str(e)}
    #endregion

    #region Sketchfab API
    def get_sketchfab_status(self):
        """Get the current status of Sketchfab integration"""
        enabled = bpy.context.scene.blendermcp_use_sketchfab
        api_key = bpy.context.scene.blendermcp_sketchfab_api_key

        # Test the API key if present
        if api_key:
            try:
                headers = {
                    "Authorization": f"Token {api_key}"
                }

                response = requests.get(
                    "https://api.sketchfab.com/v3/me",
                    headers=headers,
                    timeout=30  # Add timeout of 30 seconds
                )

                if response.status_code == 200:
                    user_data = response.json()
                    username = user_data.get("username", "Unknown user")
                    return {
                        "enabled": True,
                        "message": f"Sketchfab integration is enabled and ready to use. Logged in as: {username}"
                    }
                else:
                    return {
                        "enabled": False,
                        "message": f"Sketchfab API key seems invalid. Status code: {response.status_code}"
                    }
            except requests.exceptions.Timeout:
                return {
                    "enabled": False,
                    "message": "Timeout connecting to Sketchfab API. Check your internet connection."
                }
            except Exception as e:
                return {
                    "enabled": False,
                    "message": f"Error testing Sketchfab API key: {str(e)}"
                }

        if enabled and api_key:
            return {"enabled": True, "message": "Sketchfab integration is enabled and ready to use."}
        elif enabled and not api_key:
            return {
                "enabled": False,
                "message": """Sketchfab integration is currently enabled, but API key is not given. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Keep the 'Use Sketchfab' checkbox checked
                            3. Enter your Sketchfab API Key
                            4. Restart the connection to Claude"""
            }
        else:
            return {
                "enabled": False,
                "message": """Sketchfab integration is currently disabled. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Check the 'Use assets from Sketchfab' checkbox
                            3. Enter your Sketchfab API Key
                            4. Restart the connection to Claude"""
            }

    def search_sketchfab_models(self, query, categories=None, count=20, downloadable=True):
        """Search for models on Sketchfab based on query and optional filters"""
        try:
            api_key = bpy.context.scene.blendermcp_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}

            # Build search parameters with exact fields from Sketchfab API docs
            params = {
                "type": "models",
                "q": query,
                "count": count,
                "downloadable": downloadable,
                "archives_flavours": False
            }

            if categories:
                params["categories"] = categories

            # Make API request to Sketchfab search endpoint
            # The proper format according to Sketchfab API docs for API key auth
            headers = {
                "Authorization": f"Token {api_key}"
            }


            # Use the search endpoint as specified in the API documentation
            response = requests.get(
                "https://api.sketchfab.com/v3/search",
                headers=headers,
                params=params,
                timeout=30  # Add timeout of 30 seconds
            )

            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}

            if response.status_code != 200:
                return {"error": f"API request failed with status code {response.status_code}"}

            response_data = response.json()

            # Safety check on the response structure
            if response_data is None:
                return {"error": "Received empty response from Sketchfab API"}

            # Handle 'results' potentially missing from response
            results = response_data.get("results", [])
            if not isinstance(results, list):
                return {"error": f"Unexpected response format from Sketchfab API: {response_data}"}

            return response_data

        except requests.exceptions.Timeout:
            return {"error": "Request timed out. Check your internet connection."}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response from Sketchfab API: {str(e)}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def download_sketchfab_model(self, uid):
        """Download a model from Sketchfab by its UID"""
        try:
            api_key = bpy.context.scene.blendermcp_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}

            # Use proper authorization header for API key auth
            headers = {
                "Authorization": f"Token {api_key}"
            }

            # Request download URL using the exact endpoint from the documentation
            download_endpoint = f"https://api.sketchfab.com/v3/models/{uid}/download"

            response = requests.get(
                download_endpoint,
                headers=headers,
                timeout=30  # Add timeout of 30 seconds
            )

            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}

            if response.status_code != 200:
                return {"error": f"Download request failed with status code {response.status_code}"}

            data = response.json()

            # Safety check for None data
            if data is None:
                return {"error": "Received empty response from Sketchfab API for download request"}

            # Extract download URL with safety checks
            gltf_data = data.get("gltf")
            if not gltf_data:
                return {"error": "No gltf download URL available for this model. Response: " + str(data)}

            download_url = gltf_data.get("url")
            if not download_url:
                return {"error": "No download URL available for this model. Make sure the model is downloadable and you have access."}

            # Download the model (already has timeout)
            model_response = requests.get(download_url, timeout=60)  # 60 second timeout

            if model_response.status_code != 200:
                return {"error": f"Model download failed with status code {model_response.status_code}"}

            # Save to temporary file
            temp_dir = tempfile.mkdtemp()
            zip_file_path = os.path.join(temp_dir, f"{uid}.zip")

            with open(zip_file_path, "wb") as f:
                f.write(model_response.content)

            # Extract the zip file with enhanced security
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # More secure zip slip prevention
                for file_info in zip_ref.infolist():
                    # Get the path of the file
                    file_path = file_info.filename

                    # Convert directory separators to the current OS style
                    # This handles both / and \ in zip entries
                    target_path = os.path.join(temp_dir, os.path.normpath(file_path))

                    # Get absolute paths for comparison
                    abs_temp_dir = os.path.abspath(temp_dir)
                    abs_target_path = os.path.abspath(target_path)

                    # Ensure the normalized path doesn't escape the target directory
                    if not abs_target_path.startswith(abs_temp_dir):
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                        return {"error": "Security issue: Zip contains files with path traversal attempt"}

                    # Additional explicit check for directory traversal
                    if ".." in file_path:
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                        return {"error": "Security issue: Zip contains files with directory traversal sequence"}

                # If all files passed security checks, extract them
                zip_ref.extractall(temp_dir)

            # Find the main glTF file
            gltf_files = [f for f in os.listdir(temp_dir) if f.endswith('.gltf') or f.endswith('.glb')]

            if not gltf_files:
                with suppress(Exception):
                    shutil.rmtree(temp_dir)
                return {"error": "No glTF file found in the downloaded model"}

            main_file = os.path.join(temp_dir, gltf_files[0])

            # Import the model
            bpy.ops.import_scene.gltf(filepath=main_file)

            # Get the names of imported objects
            imported_objects = [obj.name for obj in bpy.context.selected_objects]

            # Clean up temporary files
            with suppress(Exception):
                shutil.rmtree(temp_dir)

            return {
                "success": True,
                "message": "Model imported successfully",
                "imported_objects": imported_objects
            }

        except requests.exceptions.Timeout:
            return {"error": "Request timed out. Check your internet connection and try again with a simpler model."}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response from Sketchfab API: {str(e)}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to download model: {str(e)}"}
    #endregion

# Blender UI Panel
class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "blendermcp_port")
        layout.prop(scene, "blendermcp_use_polyhaven", text="Use assets from Poly Haven")

        layout.prop(scene, "blendermcp_use_hyper3d", text="Use Hyper3D Rodin 3D model generation")
        if scene.blendermcp_use_hyper3d:
            layout.prop(scene, "blendermcp_hyper3d_mode", text="Rodin Mode")
            layout.prop(scene, "blendermcp_hyper3d_api_key", text="API Key")
            layout.operator("blendermcp.set_hyper3d_free_trial_api_key", text="Set Free Trial API Key")

        layout.prop(scene, "blendermcp_use_sketchfab", text="Use assets from Sketchfab")
        if scene.blendermcp_use_sketchfab:
            layout.prop(scene, "blendermcp_sketchfab_api_key", text="API Key")

        if not scene.blendermcp_server_running:
            layout.operator("blendermcp.start_server", text="Connect to MCP server")
        else:
            layout.operator("blendermcp.stop_server", text="Disconnect from MCP server")
            layout.label(text=f"Running on port {scene.blendermcp_port}")

# Operator to set Hyper3D API Key
class BLENDERMCP_OT_SetFreeTrialHyper3DAPIKey(bpy.types.Operator):
    bl_idname = "blendermcp.set_hyper3d_free_trial_api_key"
    bl_label = "Set Free Trial API Key"

    def execute(self, context):
        context.scene.blendermcp_hyper3d_api_key = RODIN_FREE_TRIAL_KEY
        context.scene.blendermcp_hyper3d_mode = 'MAIN_SITE'
        self.report({'INFO'}, "API Key set successfully!")
        return {'FINISHED'}

# Operator to start the server
class BLENDERMCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Connect to Claude"
    bl_description = "Start the BlenderMCP server to connect with Claude"

    def execute(self, context):
        scene = context.scene

        # Create a new server instance
        if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
            bpy.types.blendermcp_server = BlenderMCPServer(port=scene.blendermcp_port)

        # Start the server
        bpy.types.blendermcp_server.start()
        scene.blendermcp_server_running = True

        return {'FINISHED'}

# Operator to stop the server
class BLENDERMCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop the connection to Claude"
    bl_description = "Stop the connection to Claude"

    def execute(self, context):
        scene = context.scene

        # Stop the server if it exists
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server

        scene.blendermcp_server_running = False

        return {'FINISHED'}

# Registration functions
def register():
    bpy.types.Scene.blendermcp_port = IntProperty(
        name="Port",
        description="Port for the BlenderMCP server",
        default=9876,
        min=1024,
        max=65535
    )

    bpy.types.Scene.blendermcp_server_running = bpy.props.BoolProperty(
        name="Server Running",
        default=False
    )

    bpy.types.Scene.blendermcp_use_polyhaven = bpy.props.BoolProperty(
        name="Use Poly Haven",
        description="Enable Poly Haven asset integration",
        default=False
    )

    bpy.types.Scene.blendermcp_use_hyper3d = bpy.props.BoolProperty(
        name="Use Hyper3D Rodin",
        description="Enable Hyper3D Rodin generatino integration",
        default=False
    )

    bpy.types.Scene.blendermcp_hyper3d_mode = bpy.props.EnumProperty(
        name="Rodin Mode",
        description="Choose the platform used to call Rodin APIs",
        items=[
            ("MAIN_SITE", "hyper3d.ai", "hyper3d.ai"),
            ("FAL_AI", "fal.ai", "fal.ai"),
        ],
        default="MAIN_SITE"
    )

    bpy.types.Scene.blendermcp_hyper3d_api_key = bpy.props.StringProperty(
        name="Hyper3D API Key",
        subtype="PASSWORD",
        description="API Key provided by Hyper3D",
        default=""
    )

    bpy.types.Scene.blendermcp_use_sketchfab = bpy.props.BoolProperty(
        name="Use Sketchfab",
        description="Enable Sketchfab asset integration",
        default=False
    )

    bpy.types.Scene.blendermcp_sketchfab_api_key = bpy.props.StringProperty(
        name="Sketchfab API Key",
        subtype="PASSWORD",
        description="API Key provided by Sketchfab",
        default=""
    )

    bpy.utils.register_class(BLENDERMCP_PT_Panel)
    bpy.utils.register_class(BLENDERMCP_OT_SetFreeTrialHyper3DAPIKey)
    bpy.utils.register_class(BLENDERMCP_OT_StartServer)
    bpy.utils.register_class(BLENDERMCP_OT_StopServer)

    print("BlenderMCP addon registered")

def unregister():
    # Stop the server if it's running
    if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
        bpy.types.blendermcp_server.stop()
        del bpy.types.blendermcp_server

    bpy.utils.unregister_class(BLENDERMCP_PT_Panel)
    bpy.utils.unregister_class(BLENDERMCP_OT_SetFreeTrialHyper3DAPIKey)
    bpy.utils.unregister_class(BLENDERMCP_OT_StartServer)
    bpy.utils.unregister_class(BLENDERMCP_OT_StopServer)

    del bpy.types.Scene.blendermcp_port
    del bpy.types.Scene.blendermcp_server_running
    del bpy.types.Scene.blendermcp_use_polyhaven
    del bpy.types.Scene.blendermcp_use_hyper3d
    del bpy.types.Scene.blendermcp_hyper3d_mode
    del bpy.types.Scene.blendermcp_hyper3d_api_key
    del bpy.types.Scene.blendermcp_use_sketchfab
    del bpy.types.Scene.blendermcp_sketchfab_api_key

    print("BlenderMCP addon unregistered")

if __name__ == "__main__":
    register()
