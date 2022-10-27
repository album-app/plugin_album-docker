import sys
import unittest
from unittest import mock
from unittest.mock import patch

from album.api import Album
from album.argument_parsing import main
from album.core.api.model.collection_solution import ICollectionSolution
from album.runner.album_logging import get_active_logger


class TestIntegrationExampleCommand(unittest.TestCase):

    @patch('album.argument_parsing.create_album_instance', return_value=mock.create_autospec(Album))
    def test_examplecommand(self, create_album_instance_mock):
        #mocks
        resolve_result = mock.create_autospec(ICollectionSolution)
        create_album_instance_mock.return_value.resolve.return_value = resolve_result
        resolve_result.coordinates.return_value = "my-group:my-solution:my-version"

        with self.assertLogs(get_active_logger(), level='INFO') as cm:

            # run
            sys.argv = ["", "examplecommand", "solution.py"]
            self.assertIsNone(main())

            # assert
            self.assertEqual(4, len(cm.output))
            self.assertIn('my-group:my-solution:my-version', cm.output[3])


if __name__ == '__main__':
    unittest.main()
