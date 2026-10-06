# Cleanup of scenario output folders on completion of the tests
# Local test:
#   conda activate RDRenv
#   cd C:/GitHub/RDR
#   pytest
# or to run just this file
#   python -m pytest metamodel_py/tests/tests_cleanup_test.py -v
# use pytest flag -rP for extra summary info for passed tests, -rx for failed tests

import os
import shutil
import stat
from pathlib import Path

def test_teardown_scenario_outputs():
    """Remove generated scenario outputs and SQLite sidecar files.

    :returns: None. The assertions fail if cleanup leaves generated files behind.
    :rtype: None
    """
    test_file_locations = ['qs1_files',
                           'qs2_files/Example_A',
                           'qs2_files/Example_B',
                           'qs2_files/Example_C',
                           'rs2_files',
                           'rs3_files',
                           'rs4_files']
    test_dir = os.path.dirname(os.path.realpath(__file__))

    output_dirs = []
    for f in test_file_locations:
        output_dirs.append(os.path.join(test_dir, f, 'Data', 'generated_files'))

    for d in output_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)

    target_name = "project_database.sqlite"

    def make_writable(path_obj: Path) -> None:
        """Ensure a file can be deleted on Windows.

        :param path_obj: Path object being made writable or deleted.
        :returns: None. The helper mutates file permissions in place.
        :rtype: None
        """
        try:
            path_obj.chmod(path_obj.stat().st_mode | stat.S_IWRITE)
        except FileNotFoundError:
            return

    def remove_sqlite_family(base_file: Path):
        """Delete the SQLite database and related journal files.

        :param base_file: Path to the SQLite database family that should be removed.
        :returns: The removed SQLite-family paths.
        :rtype: list[pathlib.Path]
        """
        removed = []
        for suffix in ("", "-shm", "-wal", "-journal"):
            candidate = base_file if suffix == "" else base_file.with_name(f"{base_file.name}{suffix}")
            if candidate.exists():
                make_writable(candidate)
                try:
                    candidate.unlink()
                except PermissionError:
                    make_writable(candidate)
                    candidate.unlink()
                removed.append(candidate)
        return removed

    removed_sqlite_files = []

    for path_str in test_file_locations:
        path_obj = Path(os.path.join(test_dir, path_str))
        if path_obj.is_dir():
            for file_path in list(path_obj.rglob(target_name)):
                print(file_path)
                removed_sqlite_files.extend(remove_sqlite_family(file_path))

    print([str(p) for p in removed_sqlite_files])

    for d in output_dirs:
        assert not os.path.exists(d)

    remaining_sqlite = []
    for path_str in test_file_locations:
        path_obj = Path(os.path.join(test_dir, path_str))
        if path_obj.is_dir():
            remaining_sqlite.extend(list(path_obj.rglob(target_name)))

    assert not remaining_sqlite, f"project_database.sqlite still present in: {[str(p) for p in remaining_sqlite]}"

    assert not os.path.exists(output_dirs[0])
    assert not os.path.exists(output_dirs[1])
    assert not os.path.exists(output_dirs[2])
    assert not os.path.exists(output_dirs[3])
    assert not os.path.exists(output_dirs[4])
    assert not os.path.exists(output_dirs[5])
    assert not os.path.exists(output_dirs[6])
  