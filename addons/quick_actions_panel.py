bl_info = {
    "name": "Quick Actions Panel",
    "author": "BlenderMCP",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Quick Actions",
    "description": "Customizable panel with quick action buttons and custom labels",
    "category": "Interface",
}

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup, Panel, Operator, UIList


class QuickActionItem(PropertyGroup):
    """Property group for a single quick action"""
    enabled: BoolProperty(
        name="Enabled",
        description="Show this action in the panel",
        default=True
    )
    label: StringProperty(
        name="Label",
        description="Custom label for this action",
        default=""
    )
    operator: StringProperty(
        name="Operator",
        description="The operator ID (e.g., mesh.primitive_cube_add)",
        default=""
    )
    operator_args: StringProperty(
        name="Arguments",
        description="Operator arguments as key=value pairs (e.g., type='ORIGIN_GEOMETRY')",
        default=""
    )
    icon: StringProperty(
        name="Icon",
        description="Icon name (e.g., MESH_CUBE)",
        default="NONE"
    )
    category: StringProperty(
        name="Category",
        description="Category for grouping actions",
        default="General"
    )


class QUICKACTIONS_UL_items(UIList):
    """UI List for displaying quick actions"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.prop(item, "label", text="", emboss=False)
            row.label(text=item.operator, icon=item.icon if item.icon != "NONE" else 'DOT')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.label, icon=item.icon if item.icon != "NONE" else 'DOT')


class QUICKACTIONS_OT_add_action(Operator):
    """Add a new quick action"""
    bl_idname = "quickactions.add_action"
    bl_label = "Add Quick Action"
    bl_options = {'REGISTER', 'UNDO'}

    operator: StringProperty(name="Operator ID")
    operator_args: StringProperty(name="Arguments", default="")
    label: StringProperty(name="Label")
    icon: StringProperty(name="Icon", default="NONE")
    category: StringProperty(name="Category", default="General")

    def execute(self, context):
        props = context.scene.quick_actions
        item = props.items.add()
        item.operator = self.operator
        item.operator_args = self.operator_args
        item.label = self.label if self.label else self.operator.split(".")[-1].replace("_", " ").title()
        item.icon = self.icon
        item.category = self.category
        item.enabled = True
        props.active_index = len(props.items) - 1
        return {'FINISHED'}


class QUICKACTIONS_OT_remove_action(Operator):
    """Remove the selected quick action"""
    bl_idname = "quickactions.remove_action"
    bl_label = "Remove Quick Action"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.quick_actions
        if props.items and props.active_index >= 0:
            props.items.remove(props.active_index)
            props.active_index = min(props.active_index, len(props.items) - 1)
        return {'FINISHED'}


class QUICKACTIONS_OT_move_action(Operator):
    """Move the selected action up or down"""
    bl_idname = "quickactions.move_action"
    bl_label = "Move Quick Action"
    bl_options = {'REGISTER', 'UNDO'}

    direction: StringProperty(name="Direction", default="UP")

    def execute(self, context):
        props = context.scene.quick_actions
        idx = props.active_index
        if self.direction == "UP" and idx > 0:
            props.items.move(idx, idx - 1)
            props.active_index -= 1
        elif self.direction == "DOWN" and idx < len(props.items) - 1:
            props.items.move(idx, idx + 1)
            props.active_index += 1
        return {'FINISHED'}


class QUICKACTIONS_OT_run_action(Operator):
    """Run a quick action operator"""
    bl_idname = "quickactions.run_action"
    bl_label = "Run Quick Action"

    operator: StringProperty(name="Operator ID")
    operator_args: StringProperty(name="Arguments", default="")

    def execute(self, context):
        try:
            # Parse operator ID like "mesh.primitive_cube_add"
            parts = self.operator.split(".")
            if len(parts) >= 2:
                category = parts[0]
                op_name = ".".join(parts[1:])
                op_category = getattr(bpy.ops, category, None)
                if op_category:
                    op = getattr(op_category, op_name, None)
                    if op:
                        # Parse arguments if provided
                        kwargs = {}
                        if self.operator_args:
                            # Parse key=value pairs like "type='ORIGIN_GEOMETRY', center='BOUNDS'"
                            import re
                            # Match key='value' or key="value" or key=value patterns
                            pattern = r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|([^,\s]+))"
                            matches = re.findall(pattern, self.operator_args)
                            for match in matches:
                                key = match[0]
                                value = match[1] or match[2] or match[3]
                                # Try to convert to appropriate type
                                if value.lower() == 'true':
                                    kwargs[key] = True
                                elif value.lower() == 'false':
                                    kwargs[key] = False
                                else:
                                    try:
                                        kwargs[key] = int(value)
                                    except ValueError:
                                        try:
                                            kwargs[key] = float(value)
                                        except ValueError:
                                            kwargs[key] = value
                        op(**kwargs)
                        return {'FINISHED'}
            self.report({'WARNING'}, f"Operator not found: {self.operator}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error running {self.operator}: {str(e)}")
            return {'CANCELLED'}


class QUICKACTIONS_OT_add_preset(Operator):
    """Add preset quick actions for common workflows"""
    bl_idname = "quickactions.add_preset"
    bl_label = "Add Preset Actions"
    bl_options = {'REGISTER', 'UNDO'}

    preset: StringProperty(name="Preset", default="modeling")

    def execute(self, context):
        presets = {
            "modeling": [
                ("object.shade_smooth", "Shade Smooth", "SMOOTHCURVE", "Shading"),
                ("object.shade_flat", "Shade Flat", "LINCURVE", "Shading"),
                ("mesh.subdivide", "Subdivide", "MOD_SUBSURF", "Mesh"),
                ("mesh.extrude_region_move", "Extrude", "ORIENTATION_NORMAL", "Mesh"),
                ("mesh.inset", "Inset Faces", "FULLSCREEN_EXIT", "Mesh"),
                ("mesh.bevel", "Bevel", "MOD_BEVEL", "Mesh"),
                ("mesh.loop_cut_slide", "Loop Cut", "MOD_EDGESPLIT", "Mesh"),
                ("mesh.bridge_edge_loops", "Bridge Edge Loops", "AUTOMERGE_OFF", "Mesh"),
                ("mesh.fill", "Fill", "SNAP_FACE", "Mesh"),
                ("mesh.merge", "Merge Vertices", "AUTOMERGE_ON", "Mesh"),
            ],
            "object": [
                ("object.duplicate_move", "Duplicate", "DUPLICATE", "Object"),
                ("object.join", "Join Objects", "OBJECT_DATA", "Object"),
                ("object.parent_set", "Set Parent", "LINKED", "Object"),
                ("object.parent_clear", "Clear Parent", "UNLINKED", "Object"),
                ("object.origin_set", "Set Origin", "OBJECT_ORIGIN", "Object"),
                ("object.transform_apply", "Apply Transforms", "CHECKMARK", "Object"),
                ("object.convert", "Convert To", "FILE_REFRESH", "Object"),
                ("object.modifier_add", "Add Modifier", "MODIFIER", "Modifiers"),
            ],
            "view": [
                ("view3d.view_selected", "View Selected", "VIEWZOOM", "View"),
                ("view3d.view_all", "View All", "FULLSCREEN_ENTER", "View"),
                ("view3d.localview", "Toggle Local View", "SOLO_ON", "View"),
                ("view3d.view_persportho", "Persp/Ortho", "VIEW_PERSPECTIVE", "View"),
                ("screen.screen_full_area", "Toggle Fullscreen", "WINDOW", "View"),
            ],
            "nodes": [
                ("node.add_search", "Add Node", "ADD", "Nodes"),
                ("node.duplicate_move", "Duplicate Node", "DUPLICATE", "Nodes"),
                ("node.delete", "Delete Node", "X", "Nodes"),
                ("node.mute_toggle", "Mute Node", "HIDE_ON", "Nodes"),
                ("node.link_make", "Make Link", "LINKED", "Nodes"),
                ("node.links_cut", "Cut Links", "UNLINKED", "Nodes"),
                ("node.group_make", "Make Group", "NODETREE", "Nodes"),
                ("node.group_ungroup", "Ungroup", "X", "Nodes"),
            ],
            "materials": [
                ("material.new", "New Material", "MATERIAL", "Materials"),
                ("object.material_slot_add", "Add Slot", "ADD", "Materials"),
                ("object.material_slot_remove", "Remove Slot", "REMOVE", "Materials"),
                ("object.material_slot_assign", "Assign Material", "FORWARD", "Materials"),
            ],
        }

        if self.preset in presets:
            for op, label, icon, category in presets[self.preset]:
                bpy.ops.quickactions.add_action(
                    operator=op, label=label, icon=icon, category=category
                )
            self.report({'INFO'}, f"Added {len(presets[self.preset])} {self.preset} actions")

        return {'FINISHED'}


class QUICKACTIONS_OT_clear_all(Operator):
    """Clear all quick actions"""
    bl_idname = "quickactions.clear_all"
    bl_label = "Clear All Actions"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        context.scene.quick_actions.items.clear()
        return {'FINISHED'}


class QuickActionsProperties(PropertyGroup):
    """Properties for the quick actions panel"""
    items: CollectionProperty(type=QuickActionItem)
    active_index: IntProperty(name="Active Index", default=0)
    show_edit_mode: BoolProperty(
        name="Edit Mode",
        description="Show editing controls",
        default=False
    )
    group_by_category: BoolProperty(
        name="Group by Category",
        description="Group actions by category",
        default=True
    )


class QUICKACTIONS_PT_main_panel(Panel):
    """Main Quick Actions Panel in the 3D Viewport sidebar"""
    bl_label = "Quick Actions"
    bl_idname = "QUICKACTIONS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Quick Actions'

    def draw(self, context):
        layout = self.layout
        props = context.scene.quick_actions

        # Header with edit toggle
        row = layout.row(align=True)
        row.prop(props, "show_edit_mode", text="Edit", icon="PREFERENCES", toggle=True)
        row.prop(props, "group_by_category", text="", icon="SORTALPHA", toggle=True)

        if props.show_edit_mode:
            self.draw_edit_mode(context, layout, props)
        else:
            self.draw_action_buttons(context, layout, props)

    def draw_edit_mode(self, context, layout, props):
        """Draw the editing interface"""
        # List of actions
        row = layout.row()
        row.template_list("QUICKACTIONS_UL_items", "", props, "items", props, "active_index", rows=6)

        # List controls
        col = row.column(align=True)
        col.operator("quickactions.add_action", icon='ADD', text="")
        col.operator("quickactions.remove_action", icon='REMOVE', text="")
        col.separator()
        col.operator("quickactions.move_action", icon='TRIA_UP', text="").direction = "UP"
        col.operator("quickactions.move_action", icon='TRIA_DOWN', text="").direction = "DOWN"

        # Edit selected item
        if props.items and props.active_index >= 0 and props.active_index < len(props.items):
            item = props.items[props.active_index]
            box = layout.box()
            box.label(text="Edit Action:", icon="PREFERENCES")
            box.prop(item, "label", text="Label")
            box.prop(item, "operator", text="Operator")
            box.prop(item, "operator_args", text="Args")
            box.prop(item, "icon", text="Icon")
            box.prop(item, "category", text="Category")

        # Presets
        layout.separator()
        layout.label(text="Add Presets:", icon="PRESET")
        row = layout.row(align=True)
        op = row.operator("quickactions.add_preset", text="Modeling")
        op.preset = "modeling"
        op = row.operator("quickactions.add_preset", text="Object")
        op.preset = "object"
        row = layout.row(align=True)
        op = row.operator("quickactions.add_preset", text="View")
        op.preset = "view"
        op = row.operator("quickactions.add_preset", text="Nodes")
        op.preset = "nodes"
        row = layout.row(align=True)
        op = row.operator("quickactions.add_preset", text="Materials")
        op.preset = "materials"

        layout.separator()
        layout.operator("quickactions.clear_all", text="Clear All", icon="X")

    def draw_action_buttons(self, context, layout, props):
        """Draw the action buttons"""
        if not props.items:
            layout.label(text="No actions configured", icon="INFO")
            layout.label(text="Enable Edit Mode to add actions")
            return

        if props.group_by_category:
            # Group by category
            categories = {}
            for item in props.items:
                if not item.enabled:
                    continue
                cat = item.category or "General"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            for cat_name in sorted(categories.keys()):
                box = layout.box()
                box.label(text=cat_name, icon="DOT")
                col = box.column(align=True)
                for item in categories[cat_name]:
                    icon = item.icon if item.icon and item.icon != "NONE" else "NONE"
                    op = col.operator("quickactions.run_action", text=item.label, icon=icon)
                    op.operator = item.operator
                    op.operator_args = item.operator_args
        else:
            # Simple list
            col = layout.column(align=True)
            for item in props.items:
                if not item.enabled:
                    continue
                icon = item.icon if item.icon and item.icon != "NONE" else "NONE"
                op = col.operator("quickactions.run_action", text=item.label, icon=icon)
                op.operator = item.operator
                op.operator_args = item.operator_args


# Registration
classes = [
    QuickActionItem,
    QuickActionsProperties,
    QUICKACTIONS_UL_items,
    QUICKACTIONS_OT_add_action,
    QUICKACTIONS_OT_remove_action,
    QUICKACTIONS_OT_move_action,
    QUICKACTIONS_OT_run_action,
    QUICKACTIONS_OT_add_preset,
    QUICKACTIONS_OT_clear_all,
    QUICKACTIONS_PT_main_panel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.quick_actions = bpy.props.PointerProperty(type=QuickActionsProperties)


def unregister():
    del bpy.types.Scene.quick_actions
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
