import asyncio
import time
import numpy as np

from generated.util.vector_pb2 import Vector2
from generated.util.position_pb2 import Position2d
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.pos_extrapolator import PositionExtrapolationMethod
from generated.AprilTag_pb2 import AprilTags
from generated.Imu_pb2 import Imu
from generated.Odometry_pb2 import Odometry
from filter import FilterStrategy
from filters.average import (
    AverageFilter,
)
from filters.weighted_average import (
    WeightedAverageFilter,
)
from filters.kalman import (
    KalmanFilterStrategy,
)
from generated.RobotPosition_pb2 import RobotPosition
from world_conversion import (
    WorldConversion,
)


async def main():
    config = Config(
        "config.toml",
        exclude=[
            Module.IMAGE_RECOGNITION,
            Module.APRIL_DETECTION,
            Module.PROFILER,
            Module.WEIGHTED_AVG_FILTER,
        ],
    )

    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()

    sensor_data_queue: asyncio.Queue[Odometry | AprilTags | Imu] = asyncio.Queue()

    # Initialize filter strategy based on config
    filter_strategy: FilterStrategy
    match config.pos_extrapolator.position_extrapolation_method:
        case PositionExtrapolationMethod.AVERAGE_POSITION.value:
            filter_strategy = AverageFilter()
        case PositionExtrapolationMethod.WEIGHTED_AVERAGE_POSITION.value:
            filter_strategy = WeightedAverageFilter(config.weighted_avg_filter)
        case PositionExtrapolationMethod.KALMAN_LINEAR_FILTER.value:
            filter_strategy = KalmanFilterStrategy(config.kalman_filter)

    async def process_tags(message: bytes):
        tags = AprilTags()
        tags.ParseFromString(message)
        await sensor_data_queue.put(tags)

    async def process_odom(message: bytes):
        odom = Odometry()
        odom.ParseFromString(message)
        await sensor_data_queue.put(odom)

    async def process_imu(message: bytes):
        imu = Imu()
        imu.ParseFromString(message)
        await sensor_data_queue.put(imu)

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_tag_input_topic,
        process_tags,
    )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_odometry_input_topic,
        process_odom,
    )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_imu_input_topic,
        process_imu,
    )

    world_conversion = WorldConversion(
        filter_strategy,
        config.pos_extrapolator.tag_configs.config,
        config.pos_extrapolator.imu_configs,
        config.pos_extrapolator.odometry_global_position,
    )

    while True:
        sensor_data = await sensor_data_queue.get()
        world_conversion.insert_data(sensor_data)

        filtered_position = world_conversion.get_position()

        await autobahn_server.publish(
            config.pos_extrapolator.message.post_robot_position_output_topic,
            RobotPosition(
                camera_name=config.pos_extrapolator.cameras_to_analyze[0],
                timestamp=time.time() * 1000,
                confidence=world_conversion.get_confidence(),
                estimated_position=Position2d(
                    position=Vector2(
                        x=filtered_position[0],
                        y=filtered_position[1],
                    ),
                    direction=Vector2(
                        x=np.sin(filtered_position[4]),
                        y=np.cos(filtered_position[4]),
                    ),
                ),
            ).SerializeToString(),
        )


if __name__ == "__main__":
    asyncio.run(main())
