"""
GLTF Conversion Pipeline - Blender Addon Panel

Provides a UI panel in Blender for converting various 3D formats to GLTF/GLB.
Supports OBJ, FBX input with optimization and validation options.

Installation:
1. In Blender: Edit > Preferences > Add-ons > Install
2. Select this file
3. Enable "Import-Export: GLTF Conversion Pipeline"

The panel appears in the 3D View sidebar (N) under "GLTF Pipeline"
"""

bl_info = {
    "name": "GLTF Conversion Pipeline",
    "author": "BlenderMCP",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > GLTF Pipeline",
    "description": "Convert OBJ, FBX and other formats to optimized GLTF/GLB",
    "category": "Import-Export",
}

import bpy
import os
import json
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    CollectionProperty,
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    UIList,
)


# ============================================================================
# Property Groups
# ============================================================================

class GLTF_PipelineFileItem(PropertyGroup):
    """Single file in the conversion queue"""
    filepath: StringProperty(
        name="File Path",
        description="Path to the input file",
        default="",
        subtype='FILE_PATH'
    )
    status: EnumProperty(
        name="Status",
        items=[
            ('PENDING', "Pending", "Waiting to be converted"),
            ('CONVERTING', "Converting", "Currently being converted"),
            ('SUCCESS', "Success", "Conversion completed successfully"),
            ('FAILED', "Failed", "Conversion failed"),
        ],
        default='PENDING'
    )
    message: StringProperty(
        name="Message",
        description="Status message or error",
        default=""
    )


class GLTF_PipelineSettings(PropertyGroup):
    """Main settings for the conversion pipeline"""
    
    # Input/Output
    input_file: StringProperty(
        name="Input File",
        description="Single file to convert",
        default="",
        subtype='FILE_PATH'
    )
    
    output_directory: StringProperty(
        name="Output Directory",
        description="Directory for converted files (blank = same as input)",
        default="",
        subtype='DIR_PATH'
    )
    
    output_format: EnumProperty(
        name="Output Format",
        description="Output file format",
        items=[
            ('GLB', "GLB (Binary)", "Single binary file, recommended"),
            ('GLTF', "GLTF (Separate)", "JSON + separate binary and textures"),
        ],
        default='GLB'
    )
    
    # Import Settings
    import_scale: FloatProperty(
        name="Scale",
        description="Global scale factor for import",
        default=1.0,
        min=0.001,
        max=1000.0
    )
    
    import_animations: BoolProperty(
        name="Import Animations",
        description="Import animations from the source file",
        default=True
    )
    
    # Optimization Settings
    optimize: BoolProperty(
        name="Optimize",
        description="Apply optimization passes after conversion",
        default=True
    )
    
    remove_doubles: BoolProperty(
        name="Remove Doubles",
        description="Merge vertices by distance",
        default=True
    )
    
    merge_distance: FloatProperty(
        name="Merge Distance",
        description="Maximum distance for merging vertices",
        default=0.0001,
        min=0.0,
        max=1.0,
        precision=5
    )
    
    decimate: BoolProperty(
        name="Decimate",
        description="Reduce polygon count of high-poly meshes",
        default=False
    )
    
    decimate_ratio: FloatProperty(
        name="Decimate Ratio",
        description="Target ratio (0.5 = half the faces)",
        default=0.5,
        min=0.01,
        max=1.0
    )
    
    decimate_min_faces: IntProperty(
        name="Min Faces",
        description="Only decimate meshes above this face count",
        default=1000,
        min=100,
        max=1000000
    )
    
    recalculate_normals: BoolProperty(
        name="Recalculate Normals",
        description="Recalculate vertex normals",
        default=False
    )
    
    apply_transforms: BoolProperty(
        name="Apply Transforms",
        description="Apply rotation and scale transforms",
        default=True
    )
    
    # Material Settings
    standardize_materials: BoolProperty(
        name="Standardize Materials",
        description="Ensure all materials use Principled BSDF for GLTF compatibility",
        default=True
    )
    
    remove_unused_materials: BoolProperty(
        name="Remove Unused Materials",
        description="Remove materials not used by any object",
        default=True
    )
    
    # Export Settings
    export_textures: BoolProperty(
        name="Export Textures",
        description="Include textures in the export",
        default=True
    )
    
    export_lights: BoolProperty(
        name="Export Lights",
        description="Export light sources",
        default=True
    )
    
    export_cameras: BoolProperty(
        name="Export Cameras",
        description="Export cameras",
        default=True
    )
    
    # Validation
    validate_output: BoolProperty(
        name="Validate Output",
        description="Validate the output file after conversion",
        default=True
    )
    
    # Batch mode
    batch_mode: BoolProperty(
        name="Batch Mode",
        description="Convert multiple files",
        default=False
    )
    
    # File list for batch mode
    file_list_index: IntProperty(
        name="Active File Index",
        default=0
    )


# ============================================================================
# UI Lists
# ============================================================================

class GLTF_UL_FileList(UIList):
    """UI List for batch conversion files"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # Status icon
            if item.status == 'PENDING':
                icon = 'TIME'
            elif item.status == 'CONVERTING':
                icon = 'SORTTIME'
            elif item.status == 'SUCCESS':
                icon = 'CHECKMARK'
            else:  # FAILED
                icon = 'ERROR'
            
            row.label(text="", icon=icon)
            
            # Filename
            filename = os.path.basename(item.filepath)
            row.label(text=filename)
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='FILE_3D')


# ============================================================================
# Operators
# ============================================================================

class GLTF_OT_SelectInputFile(Operator):
    """Select input file for conversion"""
    bl_idname = "gltf_pipeline.select_input_file"
    bl_label = "Select Input File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(
        default="*.obj;*.fbx;*.gltf;*.glb",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        context.scene.gltf_pipeline.input_file = self.filepath
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GLTF_OT_AddBatchFile(Operator):
    """Add file to batch conversion list"""
    bl_idname = "gltf_pipeline.add_batch_file"
    bl_label = "Add File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: StringProperty(subtype='DIR_PATH')
    filter_glob: StringProperty(
        default="*.obj;*.fbx;*.gltf;*.glb",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        settings = context.scene.gltf_pipeline
        
        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)
            
            # Check if already in list
            exists = any(item.filepath == filepath for item in settings.file_list)
            if not exists:
                item = settings.file_list.add()
                item.filepath = filepath
                item.status = 'PENDING'
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GLTF_OT_RemoveBatchFile(Operator):
    """Remove selected file from batch list"""
    bl_idname = "gltf_pipeline.remove_batch_file"
    bl_label = "Remove File"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.gltf_pipeline
        
        if settings.file_list and settings.file_list_index >= 0:
            settings.file_list.remove(settings.file_list_index)
            settings.file_list_index = max(0, settings.file_list_index - 1)
        
        return {'FINISHED'}


class GLTF_OT_ClearBatchFiles(Operator):
    """Clear all files from batch list"""
    bl_idname = "gltf_pipeline.clear_batch_files"
    bl_label = "Clear All"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.gltf_pipeline.file_list.clear()
        return {'FINISHED'}


class GLTF_OT_ConvertSingle(Operator):
    """Convert single file to GLTF"""
    bl_idname = "gltf_pipeline.convert_single"
    bl_label = "Convert File"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.gltf_pipeline
        
        if not settings.input_file:
            self.report({'ERROR'}, "No input file selected")
            return {'CANCELLED'}
        
        if not os.path.exists(settings.input_file):
            self.report({'ERROR'}, f"File not found: {settings.input_file}")
            return {'CANCELLED'}
        
        # Determine output path
        input_path = bpy.path.abspath(settings.input_file)
        ext = '.glb' if settings.output_format == 'GLB' else '.gltf'
        
        if settings.output_directory:
            output_dir = bpy.path.abspath(settings.output_directory)
            filename = os.path.splitext(os.path.basename(input_path))[0] + ext
            output_path = os.path.join(output_dir, filename)
        else:
            output_path = os.path.splitext(input_path)[0] + ext
        
        try:
            # Clear scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            
            # Import based on format
            input_ext = os.path.splitext(input_path)[1].lower()
            
            if input_ext == '.obj':
                bpy.ops.wm.obj_import(filepath=input_path, global_scale=settings.import_scale)
            elif input_ext == '.fbx':
                bpy.ops.import_scene.fbx(
                    filepath=input_path,
                    global_scale=settings.import_scale,
                    use_anim=settings.import_animations,
                )
            elif input_ext in ('.gltf', '.glb'):
                bpy.ops.import_scene.gltf(filepath=input_path)
            else:
                self.report({'ERROR'}, f"Unsupported format: {input_ext}")
                return {'CANCELLED'}
            
            # Optimization
            if settings.optimize:
                self._optimize(context, settings)
            
            # Export
            bpy.ops.object.select_all(action='SELECT')
            
            export_format = 'GLB' if settings.output_format == 'GLB' else 'GLTF_SEPARATE'
            
            bpy.ops.export_scene.gltf(
                filepath=output_path,
                export_format=export_format,
                use_selection=True,
                export_apply=settings.apply_transforms,
                export_lights=settings.export_lights,
                export_cameras=settings.export_cameras,
                export_animations=settings.import_animations,
            )
            
            self.report({'INFO'}, f"Converted: {os.path.basename(output_path)}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Conversion failed: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
    def _optimize(self, context, settings):
        """Apply optimization passes"""
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            
            context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # Apply transforms
            if settings.apply_transforms:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            
            # Mesh cleanup
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            
            if settings.remove_doubles:
                bpy.ops.mesh.remove_doubles(threshold=settings.merge_distance)
            
            if settings.recalculate_normals:
                bpy.ops.mesh.normals_make_consistent(inside=False)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Decimate
            if settings.decimate and len(obj.data.polygons) > settings.decimate_min_faces:
                decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate_mod.ratio = settings.decimate_ratio
                bpy.ops.object.modifier_apply(modifier="Decimate")
            
            obj.select_set(False)
        
        # Material optimization
        if settings.standardize_materials:
            for mat in bpy.data.materials:
                if not mat.use_nodes:
                    mat.use_nodes = True
                
                if mat.node_tree:
                    nodes = mat.node_tree.nodes
                    
                    # Ensure Principled BSDF exists
                    has_principled = any(n.type == 'BSDF_PRINCIPLED' for n in nodes)
                    if not has_principled:
                        principled = nodes.new('ShaderNodeBsdfPrincipled')
                        principled.location = (0, 0)
                        
                        # Find output and connect
                        output = None
                        for node in nodes:
                            if node.type == 'OUTPUT_MATERIAL':
                                output = node
                                break
                        
                        if output:
                            mat.node_tree.links.new(
                                principled.outputs['BSDF'],
                                output.inputs['Surface']
                            )
        
        if settings.remove_unused_materials:
            used_mats = set()
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for slot in obj.material_slots:
                        if slot.material:
                            used_mats.add(slot.material.name)
            
            for mat in list(bpy.data.materials):
                if mat.name not in used_mats and mat.users == 0:
                    bpy.data.materials.remove(mat)


class GLTF_OT_ConvertBatch(Operator):
    """Convert all files in batch list"""
    bl_idname = "gltf_pipeline.convert_batch"
    bl_label = "Convert All"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.gltf_pipeline
        
        if not settings.file_list:
            self.report({'ERROR'}, "No files in batch list")
            return {'CANCELLED'}
        
        success_count = 0
        fail_count = 0
        
        for item in settings.file_list:
            item.status = 'CONVERTING'
            
            # Set as current input and convert
            settings.input_file = item.filepath
            
            try:
                bpy.ops.gltf_pipeline.convert_single()
                item.status = 'SUCCESS'
                item.message = "Converted successfully"
                success_count += 1
            except Exception as e:
                item.status = 'FAILED'
                item.message = str(e)
                fail_count += 1
        
        self.report({'INFO'}, f"Batch complete: {success_count} success, {fail_count} failed")
        
        return {'FINISHED'}


class GLTF_OT_ValidateFile(Operator):
    """Validate a GLTF/GLB file"""
    bl_idname = "gltf_pipeline.validate_file"
    bl_label = "Validate"
    bl_options = {'REGISTER'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(
        default="*.gltf;*.glb",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}
        
        filepath = bpy.path.abspath(self.filepath)
        
        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"File not found: {filepath}")
            return {'CANCELLED'}
        
        # Basic validation
        try:
            if filepath.lower().endswith('.glb'):
                with open(filepath, 'rb') as f:
                    magic = f.read(4)
                    if magic != b'glTF':
                        self.report({'ERROR'}, "Invalid GLB file: wrong magic bytes")
                        return {'CANCELLED'}
                    
                    version = int.from_bytes(f.read(4), 'little')
                    if version != 2:
                        self.report({'WARNING'}, f"Unexpected version: {version}")
                    
                    total_length = int.from_bytes(f.read(4), 'little')
                    file_size = os.path.getsize(filepath)
                    
                    if total_length != file_size:
                        self.report({'WARNING'}, f"Size mismatch: header says {total_length}, file is {file_size}")
            
            else:  # .gltf
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                if 'asset' not in data:
                    self.report({'ERROR'}, "Invalid GLTF: missing 'asset' property")
                    return {'CANCELLED'}
                
                if data.get('asset', {}).get('version') != '2.0':
                    self.report({'WARNING'}, f"Unexpected version: {data.get('asset', {}).get('version')}")
            
            self.report({'INFO'}, f"Validation passed: {os.path.basename(filepath)}")
            
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"Invalid JSON: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Validation failed: {e}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Pre-fill with current input file if it's a GLTF
        settings = context.scene.gltf_pipeline
        if settings.input_file and settings.input_file.lower().endswith(('.gltf', '.glb')):
            self.filepath = settings.input_file
            return self.execute(context)
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ============================================================================
# Panels
# ============================================================================

class GLTF_PT_MainPanel(Panel):
    """Main panel for GLTF Pipeline"""
    bl_label = "GLTF Conversion Pipeline"
    bl_idname = "GLTF_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        
        # Mode toggle
        row = layout.row(align=True)
        row.prop(settings, "batch_mode", text="Batch Mode", toggle=True)


class GLTF_PT_InputPanel(Panel):
    """Input file selection panel"""
    bl_label = "Input"
    bl_idname = "GLTF_PT_InputPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    bl_parent_id = "GLTF_PT_MainPanel"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        
        if settings.batch_mode:
            # Batch file list
            row = layout.row()
            row.template_list(
                "GLTF_UL_FileList", "",
                settings, "file_list",
                settings, "file_list_index",
                rows=4
            )
            
            col = row.column(align=True)
            col.operator("gltf_pipeline.add_batch_file", icon='ADD', text="")
            col.operator("gltf_pipeline.remove_batch_file", icon='REMOVE', text="")
            col.separator()
            col.operator("gltf_pipeline.clear_batch_files", icon='X', text="")
            
            # File count
            layout.label(text=f"Files: {len(settings.file_list)}")
            
        else:
            # Single file
            row = layout.row(align=True)
            row.prop(settings, "input_file", text="")
            row.operator("gltf_pipeline.select_input_file", icon='FILE_FOLDER', text="")
            
            # Show format info
            if settings.input_file:
                ext = os.path.splitext(settings.input_file)[1].lower()
                format_names = {
                    '.obj': 'Wavefront OBJ',
                    '.fbx': 'Autodesk FBX',
                    '.gltf': 'glTF JSON',
                    '.glb': 'glTF Binary',
                }
                format_name = format_names.get(ext, 'Unknown')
                layout.label(text=f"Format: {format_name}", icon='INFO')


class GLTF_PT_OutputPanel(Panel):
    """Output settings panel"""
    bl_label = "Output"
    bl_idname = "GLTF_PT_OutputPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    bl_parent_id = "GLTF_PT_MainPanel"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        
        layout.prop(settings, "output_format")
        layout.prop(settings, "output_directory")


class GLTF_PT_ImportPanel(Panel):
    """Import settings panel"""
    bl_label = "Import Settings"
    bl_idname = "GLTF_PT_ImportPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    bl_parent_id = "GLTF_PT_MainPanel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        
        layout.prop(settings, "import_scale")
        layout.prop(settings, "import_animations")


class GLTF_PT_OptimizationPanel(Panel):
    """Optimization settings panel"""
    bl_label = "Optimization"
    bl_idname = "GLTF_PT_OptimizationPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    bl_parent_id = "GLTF_PT_MainPanel"
    
    def draw_header(self, context):
        settings = context.scene.gltf_pipeline
        self.layout.prop(settings, "optimize", text="")
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        layout.enabled = settings.optimize
        
        # Mesh
        box = layout.box()
        box.label(text="Mesh", icon='MESH_DATA')
        
        row = box.row()
        row.prop(settings, "remove_doubles")
        if settings.remove_doubles:
            row.prop(settings, "merge_distance", text="Distance")
        
        box.prop(settings, "recalculate_normals")
        box.prop(settings, "apply_transforms")
        
        # Decimation
        row = box.row()
        row.prop(settings, "decimate")
        if settings.decimate:
            col = box.column(align=True)
            col.prop(settings, "decimate_ratio")
            col.prop(settings, "decimate_min_faces")
        
        # Materials
        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        box.prop(settings, "standardize_materials")
        box.prop(settings, "remove_unused_materials")


class GLTF_PT_ExportPanel(Panel):
    """Export settings panel"""
    bl_label = "Export Settings"
    bl_idname = "GLTF_PT_ExportPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    bl_parent_id = "GLTF_PT_MainPanel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        
        layout.prop(settings, "export_textures")
        layout.prop(settings, "export_lights")
        layout.prop(settings, "export_cameras")


class GLTF_PT_ActionsPanel(Panel):
    """Action buttons panel"""
    bl_label = "Actions"
    bl_idname = "GLTF_PT_ActionsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLTF Pipeline"
    bl_parent_id = "GLTF_PT_MainPanel"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.gltf_pipeline
        
        # Convert button
        if settings.batch_mode:
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.operator("gltf_pipeline.convert_batch", icon='EXPORT')
        else:
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.operator("gltf_pipeline.convert_single", icon='EXPORT')
        
        # Validate button
        layout.operator("gltf_pipeline.validate_file", icon='CHECKMARK')


# ============================================================================
# Registration
# ============================================================================

classes = [
    # Property Groups
    GLTF_PipelineFileItem,
    GLTF_PipelineSettings,
    # UI Lists
    GLTF_UL_FileList,
    # Operators
    GLTF_OT_SelectInputFile,
    GLTF_OT_AddBatchFile,
    GLTF_OT_RemoveBatchFile,
    GLTF_OT_ClearBatchFiles,
    GLTF_OT_ConvertSingle,
    GLTF_OT_ConvertBatch,
    GLTF_OT_ValidateFile,
    # Panels
    GLTF_PT_MainPanel,
    GLTF_PT_InputPanel,
    GLTF_PT_OutputPanel,
    GLTF_PT_ImportPanel,
    GLTF_PT_OptimizationPanel,
    GLTF_PT_ExportPanel,
    GLTF_PT_ActionsPanel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register properties
    bpy.types.Scene.gltf_pipeline = bpy.props.PointerProperty(type=GLTF_PipelineSettings)
    
    # Add file list to settings
    GLTF_PipelineSettings.file_list = CollectionProperty(type=GLTF_PipelineFileItem)
    
    print("GLTF Conversion Pipeline addon registered")


def unregister():
    # Remove properties
    del bpy.types.Scene.gltf_pipeline
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    print("GLTF Conversion Pipeline addon unregistered")


if __name__ == "__main__":
    register()
