"""Manual end-to-end check for generated plot creation.

This script is intentionally outside tests/ because it prompts in the terminal
and calls real BAML/LLM generation. Real generation requires ANTHROPIC_API_KEY.
The generated PNG is written directly under e2e/ while the script runs and is
removed before the script exits.
"""

from pathlib import Path

from forelius import initialize
from forelius.plotting import generate_plot_session, open_plot_file

OUTPUT_PATH = Path(__file__).with_name("manual_generated_plot.png")

DEFAULT_REQUEST = """
Maak een grafiek van zetting tegen diepte.

Diepte (m); Zetting (mm)
0; 0
1,5; 12,5
2,0; -
3,0; 22,1
"""


def main() -> None:
    try:
        initialize()
        request = _select_request()
        session = generate_plot_session(
            request,
            output_dir=OUTPUT_PATH.parent,
            filename_stem=OUTPUT_PATH.stem,
        )
        print(f"Generated plot: {session.plot.path}")
        open_plot_file(session.plot.path)

        while not _ask_yes_no("Is this plot good? [y/n]: "):
            feedback = _ask_non_empty("Revision feedback: ")
            session = session.revise(feedback)
            print(f"Revised plot: {session.plot.path}")
            open_plot_file(session.plot.path)

        _ask_yes_no("Are you done inspecting the generated plot file? [y/n]: ")
    finally:
        OUTPUT_PATH.unlink(missing_ok=True)
        print(f"Removed temporary plot file: {OUTPUT_PATH}")


def _select_request() -> str:
    if _ask_yes_no("Do you want to provide your own plot request and data? [y/n]: "):
        return _read_multiline_request()
    return DEFAULT_REQUEST


def _read_multiline_request() -> str:
    while True:
        print("Paste your plot request and data. Finish with a line containing only END:")
        lines: list[str] = []
        while True:
            line = input()
            if line == "END":
                break
            lines.append(line)

        request = "\n".join(lines).strip()
        if request:
            return request
        print("Request and data must not be empty.")


def _ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt).strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")


def _ask_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Feedback must not be empty.")


if __name__ == "__main__":
    main()
