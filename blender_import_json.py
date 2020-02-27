import json
import math
from dataclasses import dataclass
from datetime import datetime
from os import path

import bpy
from mathutils import Vector
from bpy.props import StringProperty, PointerProperty, FloatProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

@dataclass
class Joint:
    index: int
    co: Vector


@dataclass
class Interval:
    index: int
    alpha: Joint
    omega: Joint
    type: str
    strain: float
    stiffness: float
    linear_density: float
    role: str
    length: float


def track_axis_to_vector(track_axis: str) -> Vector:
    if track_axis == "POS_X":
        return Vector((1, 0, 0))
    if track_axis == "POS_Y":
        return Vector((0, 1, 0))
    if track_axis == "POS_Z":
        return Vector((0, 0, 1))
    raise ValueError(f"Cannot convert tracking axis {track_axis}")


def create_joint_node(jt: Joint, prototype_scene: bpy.types.Scene) -> bpy.types.Object:
    joint_node = prototype_scene.objects["Joint"].copy()
    joint_node.name = f"J{jt.index}"
    joint_node.location = jt.co

    return joint_node


def create_interval_node(intv: Interval, prototype_scene: bpy.types.Scene) -> bpy.types.Object:
    alpha = intv.alpha
    omega = intv.omega

    intv_node = prototype_scene.objects[intv.type].copy()
    intv_node.name = f"I{intv.index} {intv.role} (J{alpha.index} ~ J{omega.index})"

    intv_arrow = omega.co - alpha.co
    track_axis = track_axis_to_vector(intv_node.track_axis)

    # Translation
    intv_node.location = alpha.co.lerp(omega.co, 0.5)

    # Rotation
    rotation = track_axis.rotation_difference(intv_arrow)
    intv_node.rotation_mode = 'QUATERNION'
    intv_node.rotation_quaternion = rotation

    # Scale
    diameter_coeff = math.sqrt(intv.stiffness) * 200
    diameter_delta = diameter_coeff * (Vector((1, 1, 1)) - track_axis)
    length_delta = track_axis * intv_arrow.length
    scale_delta = diameter_delta + length_delta
    intv_node.scale.x *= scale_delta.x
    intv_node.scale.y *= scale_delta.y
    intv_node.scale.z *= scale_delta.z

    return intv_node


def clean_main_scene(scene: bpy.types.Scene):
    for (name, collection) in scene.collection.children.items():
        if not name.startswith("Pretenst"):
            continue
        print(f"Deleting collection '{name}'")
        for obj in collection.objects.values():
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection, do_unlink=True)


def joint_dict_to_dataclass(joint_dict):
    x = joint_dict['x']
    y = joint_dict['y']
    z = joint_dict['z']
    return Joint(
        index=int(joint_dict['index']),
        co=Vector((x, y, z)),
    )


def interval_dict_to_dataclass(index, interval_dict, joints_dict):
    joints = interval_dict['joints']
    return Interval(
        index=index,
        alpha=joints_dict[joints[0]],
        omega=joints_dict[joints[1]],
        type=interval_dict['type'],
        strain=interval_dict['strain'],
        stiffness=interval_dict['stiffness'],
        linear_density=interval_dict['linearDensity'],
        role=interval_dict['role'],
        length=interval_dict['length'],
    )


def load_pretenst_from_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        fabric = json.load(f)
    joints = [joint_dict_to_dataclass(joint_dict) for joint_dict in fabric['joints']]
    joints_dict = {
        joint.index: joint
        for joint in joints
    }
    intervals = [
        interval_dict_to_dataclass(i, interval_dict, joints_dict)
        for i, interval_dict in enumerate(fabric['intervals'])
    ]
    return intervals, joints


class ImportPretenst(Operator, ImportHelper):
    """Import a directory of Pretenst JSON files describing a tensegrity structure"""
    bl_idname = "pretenst.do_import"
    bl_label = "Pretenst Import"

    # ImportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    def execute(self, context):
        do_import_pretenst_json(self, context)
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportPretenst.bl_idname, text="Pretenst JSON")


def register():
    bpy.utils.register_class(ImportPretenst)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportPretenst)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

def do_import_pretenst_json(self: ImportPretenst, context):
    intervals, joints = load_pretenst_from_json(self.filepath)
    self.report({'INFO'}, f"Pretenst: Loaded {len(intervals)} intervals and {len(joints)} joints from {self.filepath}.")
    _, pretenst_name = path.split(self.filepath)
    collection_name = f"Pretenst: {pretenst_name}"
    collection = bpy.data.collections.new(name=collection_name)
    main_scene = bpy.data.scenes["Scene"]
    clean_main_scene(main_scene)
    main_scene.collection.children.link(collection)
    prototype_scene = bpy.data.scenes["Prototype"]
    for interval in intervals:
        intv_node = create_interval_node(interval, prototype_scene)
        collection.objects.link(intv_node)
    for joint in joints:
        joint_node = create_joint_node(joint, prototype_scene)
        collection.objects.link(joint_node)

if __name__ == "__main__":
    register()

    # test call
    bpy.ops.pretenst.do_import('INVOKE_DEFAULT')

