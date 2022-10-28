import inspect
import shutil
import sys
import unittest.mock
from argparse import Namespace
from pathlib import Path

import pkg_resources

from album.argument_parsing import create_parser
from album.docker_plugin.argument_parsing import album_docker
from album.docker_plugin.build_image import create_dockerfile, copy_to_context, get_solution_info
from album.runner.album_logging import get_active_logger
from test_docker.test_common import TestCommon


class TestUnitDocker(TestCommon):

    def test_run(self):
        with self.assertLogs(get_active_logger(), level='INFO') as cm:
            album_docker(self.album_mock,
                         Namespace(solution=str(self.resolve_result.path), output=str(self.tmp_dir.name)))
            self.assertEqual(3, len(cm.output))

    def test_create_parser(self):
        parser = create_parser()
        sys.argv = ["", "docker", "--solution", "1234", "--output", "bla"]
        args = parser.parse_known_args()
        self.assertEqual("bla", args[0].output)
        self.assertEqual("1234", args[0].solution)
        self.assertEqual(inspect.getsource(album_docker), inspect.getsource(args[0].func))

    def test_create_dockerfile(self):
        # prepare
        test_string = '''FROM frolvlad/alpine-miniconda3\n\nCOPY . /solution\n\nRUN apk add git --no-cache \\ 
\t&& pip install album \\ \n\t&& album install /solution/solution.py
ENTRYPOINT ["album", "run", "/solution/solution.py"]'''

        # call
        dockerfile = create_dockerfile(self.tmp_dir.name)
        with open(dockerfile, 'r') as file:
            dockerfile_string = file.read()

        # assert
        self.assertTrue(Path(dockerfile).is_file(), "No Dockerfile created.")
        self.assertEqual(test_string, dockerfile_string, "The created Dockerfile is not correct.")

    def test_copy_to_context_file(self):
        # prepare
        test_file = Path(pkg_resources.resource_filename('test_docker.resources.test_solution', 'solution.py'))
        test_target = Path(self.tmp_dir.name).joinpath('solution.py')

        # call
        copy_to_context(test_file, self.tmp_dir.name)

        # assert
        self.assertTrue(Path(test_target).is_file(), "Solution file did not get copied to context.")

    def test_copy_to_context_dir(self):
        # prepare
        test_files = Path(pkg_resources.resource_filename('test_docker.resources.test_solution', 'solution.py')).parent
        test_src = Path(self.tmp_dir.name).joinpath('test_source')
        test_target = Path(self.tmp_dir.name).joinpath('test_target')
        test_src_solution = Path(test_files).joinpath('solution.py')
        test_src_local_import = Path(test_files).joinpath('meintest.py')
        test_target_solution = Path(test_target).joinpath('solution.py')
        test_target_local_import = Path(test_target).joinpath('meintest.py')

        Path(test_src).mkdir()
        Path(test_target).mkdir()
        shutil.copy(test_src_solution, test_src)
        shutil.copy(test_src_local_import, test_src)

        # call
        copy_to_context(test_src, test_target)

        # assert
        self.assertTrue(Path(test_target_solution).exists(), 'Solution.py file is missing in context directory')
        self.assertTrue(Path(test_target_local_import).exists(), 'Local import file is missing in context directory')

    def test_get_solution_info(self):
        # prepare
        test_coordinates = "album:import_unittest:0.1.0"
        test_path = Path(pkg_resources.resource_filename('test_docker.resources.test_solution', 'solution.py'))

        # call
        returned_path, returned_coordinates = get_solution_info(self.album_mock, test_path)

        # assert
        self.assertEqual(test_coordinates, str(returned_coordinates), "Coordinates were not returned correctly.")
        self.assertEqual(test_path, returned_path, "The solution path was not returned correctly.")


if __name__ == '__main__':
    unittest.main()
