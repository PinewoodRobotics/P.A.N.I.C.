import numpy as np

from project.common.config import Config
from project.recognition.position.pos_extrapolator.src.tag_pos_to_world import (
    TagPosToWorld,
)


def get_rotation_matrix_deg(pitch: float, yaw: float) -> np.ndarray:
    return get_rotation_matrix(np.deg2rad(pitch), np.deg2rad(yaw))


def get_rotation_matrix(pitch: float, yaw: float) -> np.ndarray:
    # First create individual rotation matrices
    pitch_matrix = np.array(
        [
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)],
        ]
    )

    yaw_matrix = np.array(
        [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
    )

    # Combine the rotations (order matters - here yaw is applied first, then pitch)
    return pitch_matrix @ yaw_matrix


def rotate_vector(vector: np.ndarray, rotation_matrix: np.ndarray) -> np.ndarray:
    return rotation_matrix @ vector


def translate_vector(vector: np.ndarray, translation_vector: np.ndarray) -> np.ndarray:
    return vector + translation_vector


def rotate_pitch_yaw(
    pitch: float, yaw: float, rotation_pitch: float, rotation_yaw: float
) -> tuple[float, float]:
    return pitch + rotation_pitch, yaw + rotation_yaw


def convert_tag_to_world_pos(
    tag_position: tuple[float, float, float],
    camera_config: Config,
    tag_pos_to_world: TagPosToWorld,
    camera_name: str,
) -> tuple[float, float, float]:
    rotation_matrix = get_rotation_matrix_deg(
        camera_config.camera_parameters.camera_parameters[camera_name].rotation_vector[
            0
        ],
        camera_config.camera_parameters.camera_parameters[camera_name].rotation_vector[
            1
        ],
    )
    translation_vector = np.array(
        camera_config.camera_parameters.camera_parameters[
            camera_name
        ].translation_vector
    )

    tag_vector = np.array(tag_position)
    rotated_tag_vector = rotate_vector(tag_vector, rotation_matrix)
    translated_tag_vector = translate_vector(rotated_tag_vector, translation_vector)

    world_pos = tag_pos_to_world.get_world_pos(
        (translated_tag_vector[0], translated_tag_vector[1], translated_tag_vector[2])
    )

    return world_pos
