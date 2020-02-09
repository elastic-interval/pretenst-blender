import csv
from dataclasses import dataclass
from os import path


@dataclass
class Joint:
    index: int
    x: float
    y: float
    z: float


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


def float_comma(s):
    return float(s.replace(',', '.'))


def joint_csv_to_dataclass(joint_csv):
    return Joint(
        index=int(joint_csv['index']),
        x=float_comma(joint_csv['x']),
        y=float_comma(joint_csv['y']),
        z=float_comma(joint_csv['z']),
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
    with open(path.join(dirpath, filepath), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=";")
        return [row for row in reader]


def load_intervals_from_csv(filepath):
    dirpath = path.dirname(filepath)
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


if __name__ == '__main__':
    print(load_intervals_from_csv("lander/intervals.csv"))
