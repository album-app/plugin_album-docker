import unittest
from argparse import Namespace
from importlib.resources import files
from pathlib import Path

import docker

from album.docker_plugin import build_image
from test_docker.test_common import TestCommon


class TestIntegrationBuildImage(TestCommon):

    def test_output_path(self):
        # test if an output path that didn't exist prior to the test was created
        # call
        build_image.run(self.album_mock, Namespace(
            solution=files('test_docker.resources.test_solution') / 'solution.py',
            output=Path(self.tmp_dir.name).joinpath('test_output')))

        # assert
        self.assertTrue(Path(self.tmp_dir.name).joinpath('test_output').is_dir(),
                        "Output directory was not created.")

    def test_build_image(self):
        # prepare
        output_file = Path(self.tmp_dir.name).joinpath("album_import_unittest_0.1.0_image.tar")

        # call
        build_image.run(self.album_mock, Namespace(
            solution=files('test_docker.resources.test_solution') / 'solution.py',
            output=Path(self.tmp_dir.name)))

        # assert
        self.assertTrue(Path(output_file).is_file(), 'No image tarball was created')

    def test_run_image(self):
        # prepare
        output_file = Path(self.tmp_dir.name).joinpath("album_import_unittest_0.1.0_image.tar")
        solution_output = "Success!"
        docker_client = docker.client.from_env()

        # call
        build_image.run(self.album_mock, Namespace(
            solution=files('test_docker.resources.test_solution') / 'solution.py',
            output=Path(self.tmp_dir.name)))

        # processing of call output for assertion
        with open(output_file, 'rb') as file:
            image = docker_client.images.load(file)[0]
        image_output = docker_client.containers.run(image, detach=False).decode()

        # assert
        self.assertTrue(image_output.find(solution_output) != -1, "Solution images did not run correctly.")


if __name__ == '__main__':
    unittest.main()
