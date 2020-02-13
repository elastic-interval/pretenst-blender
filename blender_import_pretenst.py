import csv
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
    elasticity: float
    linear_density: float
    role: str
    length: float


def float_comma(s):
    return float(s.replace(',', '.'))


def joint_csv_to_dataclass(joint_csv):
    x = float_comma(joint_csv['x'])
    y = float_comma(joint_csv['y'])
    z = float_comma(joint_csv['z'])
    return Joint(
        index=int(joint_csv['index']),
        co=Vector((x, y, z)),
    )


def interval_csv_to_dataclass(index, interval_csv, joints_dict):
    iv_joints = interval_csv['joints'].replace('=', '').replace('"', '')
    alpha_idx, omega_idx = iv_joints.split(',')
    return Interval(
        index=index,
        alpha=joints_dict[int(alpha_idx)],
        omega=joints_dict[int(omega_idx)],
        type=interval_csv['type'],
        strain=float_comma(interval_csv['strain']),
        elasticity=float_comma(interval_csv['elasticity']),
        linear_density=float_comma(interval_csv['linear density']),
        role=interval_csv['role'],
        length=float_comma(interval_csv['length']),
    )


def load_csv_rows(dirpath, filepath):
    p = path.join(dirpath, filepath)
    with open(p, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=";")
        return [row for row in reader]


def load_pretenst_from_csv(dirpath):
    joints_csv = load_csv_rows(dirpath, "joints.csv")
    joints = [joint_csv_to_dataclass(joint_csv) for joint_csv in joints_csv]
    joints_dict = {
        joint.index: joint
        for joint in joints
    }
    intervals_csv = load_csv_rows(dirpath, "intervals.csv")
    intervals = [
        interval_csv_to_dataclass(i, interval_csv, joints_dict)
        for i, interval_csv in enumerate(intervals_csv)
    ]
    return intervals, joints


def track_axis_to_vector(track_axis: str) -> Vector:
    if track_axis == "POS_X":
        return Vector((1, 0, 0))
    if track_axis == "POS_Y":
        return Vector((0, 1, 0))
    if track_axis == "POS_Z":
        return Vector((0, 0, 1))
    raise ValueError(f"Cannot convert tracking axis {track_axis}")


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
    diameter_coeff = math.sqrt(intv.elasticity) * 200
    diameter_delta = diameter_coeff * (Vector((1, 1, 1)) - track_axis)
    intv_length = intv_arrow.length
    if intv.type == "Push":
        joint_radius = prototype_scene.objects["Joint"].scale.x
        intv_length -= 2 * joint_radius
    length_delta = track_axis * intv_length
    scale_delta = diameter_delta + length_delta
    intv_node.scale.x *= scale_delta.x
    intv_node.scale.y *= scale_delta.y
    intv_node.scale.z *= scale_delta.z

    return intv_node


def create_joint_node(jt: Joint, prototype_scene: bpy.types.Scene) -> bpy.types.Object:
    joint_node = prototype_scene.objects["Joint"].copy()
    joint_node.name = f"J{jt.index}"
    joint_node.location = jt.co

    return joint_node


class ImportPretenst(Operator, ImportHelper):
    """Import a directory of Pretenst CSV files describing a tensegrity structure"""
    bl_idname = "pretenst.do_import"
    bl_label = "Pretenst Import"

    # ImportHelper mixin class uses this
    filename_ext = ".csv"

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        do_import_pretenst_csv(self, context)
        return {'FINISHED'}


def clean_main_scene(scene: bpy.types.Scene):
    for (name, collection) in scene.collection.children.items():
        if not name.startswith("Pretenst"):
            continue
        print(f"Deleting collection '{name}'")
        for obj in collection.objects.values():
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection, do_unlink=True)


def do_import_pretenst_csv(self: ImportPretenst, context):
    dirpath = path.dirname(self.filepath)
    _, pretenst_name = path.split(dirpath)
    intervals, joints = load_pretenst_from_csv(dirpath)
    self.report({'INFO'}, f"Pretenst: Loaded {len(intervals)} intervals and {len(joints)} joints from {dirpath}.")
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


def menu_func_import(self, context):
    self.layout.operator(ImportPretenst.bl_idname, text="Pretenst CSV")


def register():
    bpy.utils.register_class(ImportPretenst)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportPretenst)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    bpy.utils.register_class(ImportPretenst)

    # test call
    bpy.ops.pretenst.do_import('INVOKE_DEFAULT')
