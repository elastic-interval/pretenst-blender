import bpy

import csv
from dataclasses import dataclass
from os import path
from datetime import datetime
import mathutils
import math
import time


@dataclass
class Joint:
    index: int
    co: mathutils.Vector


@dataclass
class Interval:
    alpha: Joint
    omega: Joint
    type: str
    strain: float
    elasticity: float
    linear_density: float
    role: str
    length: float


INTERVAL_ROLES = [
    ("NexusPush", "NexusPush", "NexusPush", 0),
    ("ColumnPush", "ColumnPush", "ColumnPush", 1),
    ("Triangle", "Triangle", "Triangle", 2),
    ("Ring", "Ring", "Ring", 3),
    ("NexusCross", "NexusCross", "NexusCross", 4),
    ("ColumnCross", "ColumnCross", "ColumnCross", 5),
    ("BowMid", "BowMid", "BowMid", 6),
    ("BowEnd", "BowEnd", "BowEnd", 7),
    ("FacePull", "FacePull", "FacePull", 8),
]


def float_comma(s):
    return float(s.replace(',', '.'))


def joint_csv_to_dataclass(joint_csv):
    x = float_comma(joint_csv['x'])
    y = float_comma(joint_csv['y'])
    z = float_comma(joint_csv['z'])
    return Joint(
        index=int(joint_csv['index']),
        co=mathutils.Vector((x, y, z)),
    )


def interval_csv_to_dataclass(interval_csv, joints_dict):
    iv_joints = interval_csv['joints'].replace('=', '').replace('"', '')
    alpha_idx, omega_idx = iv_joints.split(',')
    return Interval(
        alpha=joints_dict[int(alpha_idx)],
        omega=joints_dict[int(omega_idx)],
        type=interval_csv['type'],
        strain=float_comma(interval_csv['strain']),
        elasticity=float_comma(interval_csv['elasticity']),
        linear_density=float_comma(interval_csv['linear density']),
        role=interval_csv['role'],
        length=float_comma(interval_csv['length']),
    )


def load_csv(dirpath, filepath):
    p = path.join(dirpath, filepath)
    with open(p, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=";")
        return [row for row in reader]


def load_intervals_from_csv(dirpath):
    joints_csv = load_csv(dirpath, "joints.csv")
    joints = [joint_csv_to_dataclass(joint_csv) for joint_csv in joints_csv]
    joints_dict = {
        joint.index: joint
        for joint in joints
    }
    intervals_csv = load_csv(dirpath, "intervals.csv")
    intervals = [
        interval_csv_to_dataclass(interval_csv, joints_dict)
        for interval_csv in intervals_csv
    ]
    return intervals


def test():
    bpy.data.metaballs["Mball"].elements.new(type="PLANE")


def read_pretenst_csv(self, context, filepath):
    dirpath = path.dirname(filepath)
    _, pretenst_name = path.split(dirpath)
    intervals = load_intervals_from_csv(dirpath)
    self.report({'INFO'}, f"Pretenst: Loaded {len(intervals)} intervals from {dirpath}.")
    collection_name = f"Pretenst: {pretenst_name} ({datetime.now()})"
    collection = bpy.data.collections.new(name=collection_name)
    context.scene.collection.children.link(collection)
    for i, interval in enumerate(intervals):
        obj_name = f"I{i} {interval.role} (J{interval.alpha.index} ~ J{interval.omega.index})"
        mball = bpy.data.metaballs.new(name=obj_name)
        obj = bpy.data.objects.new(mball.name, mball)
        collection.objects.link(obj)
        arrow = interval.omega.co - interval.alpha.co
        rot = mathutils.Vector((1.0, 0.0, 0.0)).rotation_difference(arrow)
        obj.location = interval.alpha.co.lerp(interval.omega.co, 0.5)
        thiccness = math.sqrt(interval.elasticity) * 2
        if interval.type == "Pull":
            thiccness /= 4
        obj.scale = (arrow.length / 2.3, thiccness, thiccness)
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = rot
        mball.elements.new(type='BALL')
        obj.pretenst_role = interval.role
    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator


class ImportPretenst(Operator, ImportHelper):
    """Import a directory of Pretenst CSV files describing a tensegrity structure"""
    bl_idname = "import_data.pretenst"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import"

    # ImportHelper mixin class uses this
    filename_ext = ".csv"

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_pretenst_csv(self, context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportPretenst.bl_idname, text="Pretenst CSV")


def register():
    bpy.utils.register_class(ImportPretenst)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

    bpy.types.Object.pretenst_role = bpy.props.EnumProperty(items=INTERVAL_ROLES)


def unregister():
    bpy.utils.unregister_class(ImportPretenst)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    del bpy.types.Object.pretenst_role


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_data.pretenst('INVOKE_DEFAULT')
