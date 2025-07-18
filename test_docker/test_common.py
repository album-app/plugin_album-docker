import gc
import platform
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest import mock

from album.api import Album
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.utils.operations.file_operations import force_remove
from album.runner.core.model.coordinates import Coordinates


class TestCommon(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.setup_tmp_resources()
        self.album_mock = mock.create_autospec(Album)
        self.resolve_result = mock.create_autospec(ICollectionSolution)
        self.album_mock.resolve.return_value = self.resolve_result
        self.resolve_result.coordinates.return_value = Coordinates(
            "album", "import_unittest", "0.1.0"
        )
        self.resolve_result.path.return_value = Path(
            str(files("test_docker.resources.test_solution") / "solution.py")
        )

    def tearDown(self) -> None:
        if self.album_mock:
            self.album_mock.close()
        self.teardown_tmp_resources()
        super().tearDown()

    def setup_tmp_resources(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()
        # os.chmod(self.closed_tmp_file.name, 0o777)

    def teardown_tmp_resources(self):
        # garbage collector
        gc.collect()
        try:
            Path(self.closed_tmp_file.name).unlink()
            self.tmp_dir.cleanup()
            # NotADirectoryError is needed since on windows systems an installed solution environment
            # contains DLLs which are in use by the testing python interpreter and raising NotADirectoryErrors
            # when shutil tries to remove them
        except (PermissionError, NotADirectoryError):
            try:
                force_remove(self.tmp_dir.name)
            except PermissionError:
                if platform.system() == "Windows":
                    pass
                else:
                    raise

    def setup_clear_album_base_dir(self):
        if Path.home().joinpath(".album").is_dir():
            force_remove(Path.home().joinpath(".album"))
