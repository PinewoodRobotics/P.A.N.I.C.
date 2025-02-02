import time

import numpy as np
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.pos_extrapolator import ImuConfig, TagPositionConfig
from project.common.util.math import (
    create_transformation_matrix,
    from_float_list,
    get_translation_rotation_components,
    get_world_pos,
)
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
from project.generated.project.common.proto.Imu_pb2 import Imu
from project.generated.project.common.proto.Odometry_pb2 import Odometry
from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy
from project.recognition.position.pos_extrapolator.src.filters.kalman import (
    KalmanFilterStrategy,
)


class WorldConversion:
    def __init__(
        self,
        filter_strategy: FilterStrategy,
        tag_configs: dict[str, TagPositionConfig] | None = None,
        imu_configs: dict[str, ImuConfig] | None = None,
        odometry_config: list[float] | None = None,
    ):
        self.filter_strategy = filter_strategy
        self.tag_configs = tag_configs
        self.imu_configs = imu_configs
        self.odometry_config = odometry_config
        self.last_timestamps = {}

    def insert_data(self, data: AprilTags | Imu | Odometry):
        if isinstance(self.filter_strategy, KalmanFilterStrategy):
            current_time = time.time()
            if str(type(data)) not in self.last_timestamps:
                self.last_timestamps[str(type(data))] = current_time

            self.filter_strategy.update_state_transition_matrix_5_5(
                current_time - self.last_timestamps[str(type(data))]
            )

            self.last_timestamps[str(type(data))] = current_time

            self.filter_strategy.predict()

        if isinstance(data, AprilTags):
            self._insert_april_tags(data)
        elif isinstance(data, Imu):
            self._insert_imu(data)
        elif isinstance(data, Odometry):
            self._insert_odometry(data)

    def get_position(self) -> list[float]:
        return self.filter_strategy.get_filtered_data()

    def get_confidence(self) -> float:
        return self.filter_strategy.get_confidence()

    def _insert_april_tags(self, data: AprilTags):
        if self.tag_configs is None:
            raise ValueError("Tag configs are not set")

        for tag in data.tags:
            if not str(tag.tag_id) in self.tag_configs:
                continue

            T_in_camera = create_transformation_matrix(
                from_float_list(list(tag.pose_R), 3, 3),
                np.array(
                    [
                        tag.pose_t[0],
                        tag.pose_t[1],
                        tag.pose_t[2],
                    ]
                ),
            )

            tag_config = self.tag_configs[str(tag.tag_id)]
            world_transform = get_world_pos(T_in_camera, tag_config.transformation)
            translation_component, rotation_component = (
                get_translation_rotation_components(world_transform)
            )

            # Extract yaw angle from rotation matrix
            yaw = np.arctan2(rotation_component[1, 0], rotation_component[0, 0])

            self.filter_strategy.filter_data(
                [
                    translation_component[0],
                    translation_component[2],
                    0,
                    0,
                    0,
                ],
                MeasurementType.APRIL_TAG,
            )

    def _insert_imu(self, data: Imu):
        if self.imu_configs is None:
            raise ValueError("Imu configs are not set")

        if not str(data.imu_id) in self.imu_configs:
            return

        imu_config = self.imu_configs[str(data.imu_id)]

        self.filter_strategy.filter_data(
            [
                data.x - imu_config.imu_local_position[0],
                data.y - imu_config.imu_local_position[1],
                data.velocity_x,
                data.velocity_y,
                data.yaw - imu_config.imu_yaw_offset,
            ],
            MeasurementType.IMU,
        )

    def _insert_odometry(self, data: Odometry):
        if self.odometry_config is None:
            raise ValueError("Odometry config is not set")

        # print(f"{data}")

        self.filter_strategy.filter_data(
            [
                data.y - self.odometry_config[0],
                data.x - self.odometry_config[1],
                data.vy,
                data.vx,
                data.theta - self.odometry_config[2],
            ],
            MeasurementType.ODOMETRY,
        )

        self.last_timestamps[type(data)] = data.timestamp
