# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Quick Tools Panel",
    "author": "BlenderMCP",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Quick Tools",
    "description": "Quick access to Apply, Set Origin, Relations, and Parent tools",
    "category": "Object",
}

import bpy


# ============================================
# APPLY TOOLS PANEL
# ============================================
class QUICKTOOLS_PT_apply(bpy.types.Panel):
    bl_label = "Apply"
    bl_idname = "QUICKTOOLS_PT_apply"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quick Tools"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.transform_apply", text="Location").location = True
        col.operator("object.transform_apply", text="Rotation").rotation = True
        col.operator("object.transform_apply", text="Scale").scale = True
        
        col.separator()
        
        # All Transforms
        op = col.operator("object.transform_apply", text="All Transforms")
        op.location = True
        op.rotation = True
        op.scale = True
        
        col.separator()
        
        # Additional apply operations
        col.operator("object.transform_apply", text="Rotation & Scale").properties = False
        col.operator("object.visual_transform_apply", text="Visual Transform")
        col.operator("object.duplicates_make_real", text="Make Instances Real")
        

# ============================================
# SET ORIGIN TOOLS PANEL
# ============================================
class QUICKTOOLS_PT_set_origin(bpy.types.Panel):
    bl_label = "Set Origin"
    bl_idname = "QUICKTOOLS_PT_set_origin"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quick Tools"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.origin_set", text="Geometry to Origin").type = 'GEOMETRY_ORIGIN'
        col.operator("object.origin_set", text="Origin to Geometry").type = 'ORIGIN_GEOMETRY'
        col.operator("object.origin_set", text="Origin to 3D Cursor").type = 'ORIGIN_CURSOR'
        
        col.separator()
        
        col.operator("object.origin_set", text="Origin to Center of Mass (Surface)").type = 'ORIGIN_CENTER_OF_MASS'
        col.operator("object.origin_set", text="Origin to Center of Mass (Volume)").type = 'ORIGIN_CENTER_OF_VOLUME'


# ============================================
# PARENT TOOLS PANEL
# ============================================
class QUICKTOOLS_PT_parent(bpy.types.Panel):
    bl_label = "Parent"
    bl_idname = "QUICKTOOLS_PT_parent"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quick Tools"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        
        # Set Parent
        col.label(text="Set Parent:", icon='LINKED')
        col.operator("object.parent_set", text="Object").type = 'OBJECT'
        col.operator("object.parent_set", text="Object (Keep Transform)").type = 'OBJECT'
        col.operator("object.parent_no_inverse_set", text="Object (Without Inverse)")
        
        col.separator()
        
        # Clear Parent
        col.label(text="Clear Parent:", icon='UNLINKED')
        col.operator("object.parent_clear", text="Clear Parent").type = 'CLEAR'
        col.operator("object.parent_clear", text="Clear and Keep Transform").type = 'CLEAR_KEEP_TRANSFORM'
        col.operator("object.parent_clear", text="Clear Parent Inverse").type = 'CLEAR_INVERSE'


# ============================================
# RELATIONS TOOLS PANEL
# ============================================
class QUICKTOOLS_PT_relations(bpy.types.Panel):
    bl_label = "Relations"
    bl_idname = "QUICKTOOLS_PT_relations"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quick Tools"
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        
        # Collections
        col.label(text="Collections:", icon='OUTLINER_COLLECTION')
        col.operator("object.move_to_collection", text="Move to Collection")
        col.operator("object.link_to_collection", text="Link to Collection")
        
        col.separator()
        
        # Make Links
        col.label(text="Make Links:", icon='LINKED')
        col.operator("object.make_links_data", text="Link Object Data").type = 'OBDATA'
        col.operator("object.make_links_data", text="Link Materials").type = 'MATERIAL'
        col.operator("object.make_links_data", text="Link Modifiers").type = 'MODIFIERS'
        
        col.separator()
        
        # Object relationships
        col.label(text="Object Data:", icon='OBJECT_DATA')
        col.operator("object.make_single_user", text="Make Single User")
        col.operator("object.make_local", text="Make Local")


# ============================================
# CLEAR TRANSFORMS PANEL  
# ============================================
class QUICKTOOLS_PT_clear(bpy.types.Panel):
    bl_label = "Clear"
    bl_idname = "QUICKTOOLS_PT_clear"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Quick Tools"
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.operator("object.location_clear", text="Clear Location")
        col.operator("object.rotation_clear", text="Clear Rotation")
        col.operator("object.scale_clear", text="Clear Scale")
        
        col.separator()
        
        col.operator("object.origin_clear", text="Clear Origin")


# ============================================
# REGISTRATION
# ============================================
classes = (
    QUICKTOOLS_PT_apply,
    QUICKTOOLS_PT_set_origin,
    QUICKTOOLS_PT_parent,
    QUICKTOOLS_PT_relations,
    QUICKTOOLS_PT_clear,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
