from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from forelius.plotting.errors import PlotRenderingError


def open_plot_file(path: Path) -> None:
    plot_path = Path(path)
    if not plot_path.exists():
        raise PlotRenderingError(f"Plot file does not exist: {plot_path}")

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(plot_path)  # type: ignore[attr-defined]
            return
        if system == "Darwin":
            subprocess.run(["open", str(plot_path)], check=True)
            return
        subprocess.run(["xdg-open", str(plot_path)], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PlotRenderingError(f"Could not open plot file: {plot_path}") from exc
