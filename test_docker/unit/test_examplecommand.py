import inspect
import sys
import unittest.mock
from argparse import Namespace
from unittest import mock

from album.api import Album
from album.argument_parsing import create_parser
from album.core.api.model.collection_solution import ICollectionSolution
from album.runner.album_logging import get_active_logger

from src.album.examplecommand import examplecommand


class TestArgumentParsing(unittest.TestCase):

    def test_run(self):
        album = mock.create_autospec(Album)
        resolve_result = mock.create_autospec(ICollectionSolution)
        album.resolve.return_value = resolve_result
        resolve_result.coordinates.return_value = "my-group:my-solution:my-version"

        with self.assertLogs(get_active_logger(), level='INFO') as cm:
            examplecommand.run(album, Namespace(solution='solution.py', example_arg="test"))
            self.assertEqual(3, len(cm.output))

    def test_create_parser(self):
        parser = create_parser()
        sys.argv = ["", "examplecommand", "1234", "--example_arg", "bla"]
        args = parser.parse_known_args()
        self.assertEqual("bla", args[0].example_arg)
        self.assertEqual("1234", args[0].solution)
        self.assertEqual(inspect.getsource(examplecommand.run), inspect.getsource(args[0].func))


if __name__ == '__main__':
    unittest.main()
