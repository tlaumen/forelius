"""Manual end-to-end check for prompt_for_report.

This script is intentionally outside tests/ because it prompts in the terminal
and may call real BAML/LLM generation. Real generation may require
ANTHROPIC_API_KEY.
"""

from forelius import initialize, prompt_for_report


if __name__ == "__main__":
    initialize()
    markdown = prompt_for_report()
    print(markdown)
