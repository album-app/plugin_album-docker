import logging
import os
import re
from pathlib import Path

import pkg_resources

from album.api import Album
from album.runner.album_logging import get_active_logger

from album.docker_plugin.create_dockerfile import create_dockerfile


def build_image(dockerfile):
    pass


def get_solution_info(album_instance: Album, solution):
    if not Path(solution).exists():
        path = album_instance.resolve(str(solution)).path()
    else:
        path = solution
    coordinates = album_instance.resolve(str(solution)).coordinates()
    return path, coordinates


def run(album_instance: Album, args):
    solution_path, coordinates = get_solution_info(album_instance, args.solution)

    get_active_logger().info("Build an docker image which runs the solution.")
    get_active_logger().info("solution: %s at %s" % (coordinates, solution_path))
    get_active_logger().info("output directory: %s" % args.output)

    dockerfile = create_dockerfile(solution_path)
    build_image(dockerfile)


