import inspect
import io
import shutil
import sys
import unittest.mock
import zipfile
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from importlib.resources import files
from pathlib import Path

from docker.errors import BuildError

from album.argument_parsing import create_parser
from album.docker_plugin.argument_parsing import album_docker
from album.docker_plugin.build_image import (
    build_image,
    copy_to_context,
    create_dockerfile,
    get_solution_info,
    run,
)
from album.runner.album_logging import get_active_logger
from album.runner.core.model.coordinates import Coordinates
from test_docker.test_common import TestCommon


class TestUnitDocker(TestCommon):

    # def test_run(self):
    #    with self.assertLogs(get_active_logger(), level='INFO') as cm:
    #        album_docker(self.album_mock,
    #                     Namespace(solution=str(self.resolve_result.path), output=str(self.tmp_dir.name)))
    #        self.assertEqual(3, len(cm.output))

    def test_create_parser(self):
        parser = create_parser()
        sys.argv = ["", "docker", "--solution", "1234", "--output", "bla"]
        args = parser.parse_known_args()
        self.assertEqual("bla", args[0].output)
        self.assertEqual("1234", args[0].solution)
        self.assertEqual(
            inspect.getsource(album_docker), inspect.getsource(args[0].func)
        )

    def test_create_dockerfile(self):
        # call
        dockerfile = create_dockerfile(self.tmp_dir.name)

        # assert
        self.assertTrue(Path(dockerfile).is_file(), "No Dockerfile created.")

    def test_copy_to_context_file(self):
        # prepare
        test_file = Path(files("test_docker.resources.test_solution") / "solution.py")
        test_target = Path(self.tmp_dir.name).joinpath("solution.py")

        # call
        copy_to_context(test_file, self.tmp_dir.name)

        # assert
        self.assertTrue(
            Path(test_target).is_file(), "Solution file did not get copied to context."
        )

    def test_copy_to_context_dir(self):
        # prepare
        test_files = Path(
            files("test_docker.resources.test_solution") / "solution.py"
        ).parent
        test_src = Path(self.tmp_dir.name).joinpath("test_source")
        test_target = Path(self.tmp_dir.name).joinpath("test_target")
        test_src_solution = Path(test_files).joinpath("solution.py")
        test_src_local_import = Path(test_files).joinpath("meintest.py")
        test_target_solution = Path(test_target).joinpath("solution.py")
        test_target_local_import = Path(test_target).joinpath("meintest.py")

        Path(test_src).mkdir()
        Path(test_target).mkdir()
        shutil.copy(test_src_solution, test_src)
        shutil.copy(test_src_local_import, test_src)

        # call
        copy_to_context(test_src, test_target)

        # assert
        self.assertTrue(
            Path(test_target_solution).exists(),
            "Solution.py file is missing in context directory",
        )
        self.assertTrue(
            Path(test_target_local_import).exists(),
            "Local import file is missing in context directory",
        )

    def test_get_solution_info(self):
        # prepare
        test_coordinates = "album:import_unittest:0.1.0"
        test_path = Path(files("test_docker.resources.test_solution") / "solution.py")

        # call
        returned_path, returned_coordinates = get_solution_info(
            self.album_mock, test_path
        )

        # assert
        self.assertEqual(
            test_coordinates,
            str(returned_coordinates),
            "Coordinates were not returned correctly.",
        )
        self.assertEqual(
            test_path, returned_path, "The solution path was not returned correctly."
        )

    def test_create_parser_requires_solution(self):
        parser = create_parser()

        # call & assert: album's parser prints the help to stdout and the error to stderr
        with redirect_stderr(io.StringIO()) as stderr, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_known_args(["docker", "--output", "bla"])
        self.assertIn("--solution", stderr.getvalue())

    def test_create_dockerfile_content(self):
        # call
        dockerfile = create_dockerfile(
            self.tmp_dir.name,
            "apt-get update && apt-get install -y g++ cmake",
            "--allow-recursive",
        )

        # assert
        content = Path(dockerfile).read_text()
        lines = content.splitlines()
        self.assertIn("WORKDIR /", lines)
        self.assertIn('ENTRYPOINT ["/solution/solution_entrypoint.sh"]', lines)
        self.assertIn("RUN apt-get update && apt-get install -y g++ cmake", lines)
        self.assertIn("RUN album install --allow-recursive /solution", lines)
        self.assertLess(lines.index("WORKDIR /"), lines.index("COPY . /solution"))
        self.assertNotIn("./solution", content)

    def test_create_dockerfile_without_install_deps(self):
        # call
        dockerfile = create_dockerfile(self.tmp_dir.name)

        # assert
        lines = Path(dockerfile).read_text().splitlines()
        self.assertNotIn("None", lines)
        self.assertNotIn("RUN", [line.strip() for line in lines])
        self.assertEqual(
            1, len([line for line in lines if line.startswith("RUN album install")])
        )

    @unittest.mock.patch("album.docker_plugin.build_image.docker")
    def test_build_image_saves_tagged_archive(self, docker_mock):
        # prepare
        client = docker_mock.from_env.return_value
        image = unittest.mock.MagicMock()
        image.save.return_value = iter([b"image", b"data"])
        client.images.build.return_value = (image, iter([{"stream": "Step 1/8"}]))
        output = Path(self.tmp_dir.name)
        expected_tag = "album_import_unittest_0.1.0"
        expected_tar = output.joinpath("album_import_unittest_0.1.0_image.tar")

        # call
        with self.assertLogs(get_active_logger(), level="INFO") as logs:
            returned_tar = build_image(
                Coordinates("Album", "Import_Unittest", "0.1.0"), "context", output
            )

        # assert
        client.images.build.assert_called_once_with(
            path="context", tag=expected_tag, rm=True
        )
        image.save.assert_called_once_with(named="album_import_unittest_0.1.0:latest")
        self.assertEqual(expected_tar, returned_tar)
        self.assertEqual(b"imagedata", expected_tar.read_bytes())
        log_output = " ".join(logs.output)
        self.assertIn("Docker image tag: %s" % expected_tag, log_output)
        self.assertIn("Docker image archive: %s" % expected_tar, log_output)

    @unittest.mock.patch("album.docker_plugin.build_image.docker")
    def test_build_image_logs_build_output_on_error(self, docker_mock):
        # prepare: docker raises a BuildError as soon as the build output contains an error
        client = docker_mock.from_env.return_value
        build_log = iter(
            [
                {"stream": "Step 6/8 : RUN album install /solution"},
                {"error": "The command returned a non-zero code: 1"},
            ]
        )
        client.images.build.side_effect = BuildError(
            "The command returned a non-zero code: 1", build_log
        )
        output = Path(self.tmp_dir.name)

        # call
        with self.assertLogs(get_active_logger(), level="INFO") as logs:
            with self.assertRaises(BuildError) as raised:
                build_image(
                    Coordinates("album", "import_unittest", "0.1.0"), "context", output
                )

        # assert
        log_output = " ".join(logs.output)
        self.assertIn("Step 6/8 : RUN album install /solution", log_output)
        self.assertIn("ERROR", log_output)
        self.assertIn("The command returned a non-zero code: 1", log_output)
        # the error message repeats the build output, so the cause is visible without album's log
        message = str(raised.exception)
        self.assertIn("The command returned a non-zero code: 1", message)
        self.assertIn("docker build output (last 2 lines)", message)
        self.assertIn("Step 6/8 : RUN album install /solution", message)
        self.assertEqual([], list(output.glob("*_image.tar")))

    def _create_solution_package(self):
        package = Path(self.tmp_dir.name).joinpath("package")
        package.joinpath("data").mkdir(parents=True)
        shutil.copy(
            Path(files("test_docker.resources.test_solution") / "solution.py"), package
        )
        package.joinpath("helper.py").write_text("HELPER = True")
        package.joinpath("data", "model.txt").write_text("weights")
        return package

    def test_get_solution_info_coordinates_returns_solution_folder(self):
        # prepare
        package = self._create_solution_package()
        self.resolve_result.path.return_value = package.joinpath("solution.py")
        test_target = Path(self.tmp_dir.name).joinpath("test_target")
        test_target.mkdir()

        # call
        returned_path, returned_coordinates = get_solution_info(
            self.album_mock, "album:import_unittest:0.1.0"
        )
        copy_to_context(returned_path, test_target)

        # assert
        self.album_mock.resolve.assert_called_once_with("album:import_unittest:0.1.0")
        self.assertEqual(package, returned_path)
        self.assertEqual("album:import_unittest:0.1.0", str(returned_coordinates))
        self.assertTrue(test_target.joinpath("solution.py").is_file())
        self.assertTrue(test_target.joinpath("helper.py").is_file())
        self.assertTrue(test_target.joinpath("data", "model.txt").is_file())
        self.assertTrue(test_target.joinpath("solution_entrypoint.sh").is_file())

    def test_get_solution_info_resolved_single_file(self):
        # prepare: a single solution file downloaded from a URL is stored under an arbitrary name
        downloaded = Path(self.tmp_dir.name).joinpath("tmp1234")
        shutil.copy(
            Path(files("test_docker.resources.test_solution") / "solution.py"),
            downloaded,
        )
        self.resolve_result.path.return_value = downloaded

        # call
        with self.assertNoLogs(get_active_logger(), level="WARNING"):
            returned_path, _ = get_solution_info(
                self.album_mock, "https://example.org/solution.py"
            )

        # assert
        self.assertEqual(downloaded, returned_path)

    def test_get_solution_info_local_file_warns(self):
        # prepare
        test_path = Path(files("test_docker.resources.test_solution") / "solution.py")

        # call
        with self.assertLogs(get_active_logger(), level="WARNING") as logs:
            returned_path, _ = get_solution_info(self.album_mock, test_path)

        # assert
        self.assertEqual(test_path, returned_path)
        self.assertIn("sibling files", " ".join(logs.output))
        self.assertIn("Pass the folder instead", " ".join(logs.output))
        self.album_mock.resolve.assert_called_once_with(str(test_path))

    def test_get_solution_info_local_zip_returns_extracted_folder(self):
        # prepare: a zipped solution folder, Album extracts it when resolving it
        package = self._create_solution_package()
        archive = Path(self.tmp_dir.name).joinpath("my_solution.zip")
        with zipfile.ZipFile(archive, "w") as zip_file:
            for file in package.rglob("*"):
                zip_file.write(file, file.relative_to(package))
        extracted = Path(self.tmp_dir.name).joinpath("download_cache", "a1b2c3d4")
        with zipfile.ZipFile(archive) as zip_file:
            zip_file.extractall(extracted)
        self.resolve_result.path.return_value = extracted.joinpath("solution.py")
        test_target = Path(self.tmp_dir.name).joinpath("test_target")
        test_target.mkdir()

        # call
        with self.assertNoLogs(get_active_logger(), level="WARNING"):
            returned_path, _ = get_solution_info(self.album_mock, str(archive))
        copy_to_context(returned_path, test_target)

        # assert
        self.album_mock.resolve.assert_called_once_with(str(archive))
        self.assertEqual(extracted, returned_path)
        self.assertTrue(zipfile.is_zipfile(archive))
        self.assertFalse(zipfile.is_zipfile(test_target.joinpath("solution.py")))
        self.assertEqual(
            package.joinpath("solution.py").read_bytes(),
            test_target.joinpath("solution.py").read_bytes(),
        )
        self.assertTrue(test_target.joinpath("helper.py").is_file())
        self.assertTrue(test_target.joinpath("data", "model.txt").is_file())
        self.assertFalse(test_target.joinpath("my_solution.zip").exists())

    def test_copy_to_context_file_names_solution_file(self):
        # prepare
        test_file = Path(self.tmp_dir.name).joinpath("my_solution.py")
        shutil.copy(
            Path(files("test_docker.resources.test_solution") / "solution.py"),
            test_file,
        )
        test_target = Path(self.tmp_dir.name).joinpath("test_target")
        test_target.mkdir()

        # call
        with self.assertLogs(get_active_logger(), level="INFO") as logs:
            copy_to_context(test_file, test_target)

        # assert
        self.assertIn("as solution.py", " ".join(logs.output))
        self.assertTrue(test_target.joinpath("solution.py").is_file())
        self.assertFalse(test_target.joinpath("my_solution.py").exists())

    def test_copy_to_context_dir_skips_image_archives_in_output_dir(self):
        # prepare: the output directory is the solution folder itself (e.g. "--solution . --output .")
        package = self._create_solution_package()
        package.joinpath("album_import_unittest_0.1.0_image.tar").write_bytes(b"old")
        test_target = Path(self.tmp_dir.name).joinpath("test_target")
        test_target.mkdir()

        # call
        copy_to_context(package, test_target, package)

        # assert
        self.assertTrue(test_target.joinpath("solution.py").is_file())
        self.assertTrue(test_target.joinpath("helper.py").is_file())
        self.assertTrue(test_target.joinpath("data", "model.txt").is_file())
        self.assertTrue(test_target.joinpath("solution_entrypoint.sh").is_file())
        self.assertFalse(
            test_target.joinpath("album_import_unittest_0.1.0_image.tar").exists()
        )

    def test_copy_to_context_dir_skips_image_archives_in_nested_output_dir(self):
        # prepare: the output directory is a sub folder of the solution folder
        package = self._create_solution_package()
        output = package.joinpath("dist")
        output.mkdir()
        output.joinpath("album_import_unittest_0.1.0_image.tar").write_bytes(b"old")
        output.joinpath("notes.txt").write_text("keep")
        # an archive outside the output directory belongs to the solution
        package.joinpath("data", "example_image.tar").write_bytes(b"data")
        test_target = Path(self.tmp_dir.name).joinpath("test_target")
        test_target.mkdir()

        # call
        copy_to_context(package, test_target, output)

        # assert
        self.assertTrue(test_target.joinpath("solution.py").is_file())
        self.assertTrue(test_target.joinpath("dist", "notes.txt").is_file())
        self.assertFalse(
            test_target.joinpath(
                "dist", "album_import_unittest_0.1.0_image.tar"
            ).exists()
        )
        self.assertTrue(test_target.joinpath("data", "example_image.tar").is_file())

    @unittest.mock.patch("album.docker_plugin.build_image.build_image")
    def test_run_creates_nested_output_dir(self, build_image_mock):
        # prepare
        output = Path(self.tmp_dir.name).joinpath("not", "existing")
        solution_folder = Path(
            files("test_docker.resources.test_solution") / "solution.py"
        ).parent

        # call
        run(
            self.album_mock,
            Namespace(
                install_flags="",
                install_deps="",
                solution=solution_folder,
                output=output,
            ),
        )

        # assert
        self.assertTrue(output.is_dir(), "Output directory was not created.")
        build_image_mock.assert_called_once()
        self.assertEqual(output, build_image_mock.call_args[0][2])

    @unittest.mock.patch("album.docker_plugin.build_image.build_image")
    def test_run_does_not_create_output_dir_if_resolving_fails(self, build_image_mock):
        # prepare
        output = Path(self.tmp_dir.name).joinpath("not", "existing")
        self.album_mock.resolve.side_effect = LookupError("Solution not found.")

        # call
        with self.assertRaises(LookupError):
            run(
                self.album_mock,
                Namespace(
                    install_flags="",
                    install_deps="",
                    solution="album:not_existing:0.1.0",
                    output=output,
                ),
            )

        # assert
        self.assertFalse(Path(self.tmp_dir.name).joinpath("not").exists())
        build_image_mock.assert_not_called()

    @unittest.mock.patch("album.docker_plugin.build_image.build_image")
    def test_run_does_not_copy_earlier_image_archives(self, build_image_mock):
        # prepare: "--solution <folder> --output <folder>" after an earlier run
        package = self._create_solution_package()
        package.joinpath("album_import_unittest_0.1.0_image.tar").write_bytes(b"old")
        context_files = []
        build_image_mock.side_effect = lambda coordinates, context, output: (
            context_files.extend(
                str(file.relative_to(context)) for file in Path(context).rglob("*")
            )
        )

        # call
        run(
            self.album_mock,
            Namespace(
                install_flags="",
                install_deps="",
                solution=str(package),
                output=str(package),
            ),
        )

        # assert
        build_image_mock.assert_called_once()
        self.assertIn("solution.py", context_files)
        self.assertIn("helper.py", context_files)
        self.assertIn("Dockerfile", context_files)
        self.assertNotIn("album_import_unittest_0.1.0_image.tar", context_files)


if __name__ == "__main__":
    unittest.main()
