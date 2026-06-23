import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from forelius.plotting import PlotRenderingError, open_plot_file


def test_open_plot_file_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PlotRenderingError, match="does not exist"):
        open_plot_file(tmp_path / "missing.png")


def test_open_plot_file_uses_macos_open_command(tmp_path: Path) -> None:
    path = tmp_path / "plot.png"
    path.write_bytes(b"plot")

    with (
        patch("platform.system", return_value="Darwin"),
        patch("subprocess.run") as run,
    ):
        open_plot_file(path)

    run.assert_called_once_with(["open", str(path)], check=True)


def test_open_plot_file_uses_linux_xdg_open_command(tmp_path: Path) -> None:
    path = tmp_path / "plot.png"
    path.write_bytes(b"plot")

    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run") as run,
    ):
        open_plot_file(path)

    run.assert_called_once_with(["xdg-open", str(path)], check=True)


def test_open_plot_file_uses_windows_startfile(tmp_path: Path) -> None:
    path = tmp_path / "plot.png"
    path.write_bytes(b"plot")

    with (
        patch("platform.system", return_value="Windows"),
        patch("os.startfile", create=True) as startfile,
    ):
        open_plot_file(path)

    startfile.assert_called_once_with(path)


def test_open_plot_file_raises_when_opener_fails(tmp_path: Path) -> None:
    path = tmp_path / "plot.png"
    path.write_bytes(b"plot")

    with (
        patch("platform.system", return_value="Linux"),
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "xdg-open")),
    ):
        with pytest.raises(PlotRenderingError, match="Could not open"):
            open_plot_file(path)
