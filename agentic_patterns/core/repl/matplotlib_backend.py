"""Custom matplotlib backend for capturing figures in the notebook."""

import matplotlib.pyplot as plt

from agentic_patterns.core.repl.cell_output import CellOutput


def capture_matplotlib_figures() -> list[CellOutput]:
    """Capture all current matplotlib figures and convert them to CellOutput objects."""
    outputs = []
    for fig_num in plt.get_fignums():
        fig = plt.figure(fig_num)
        outputs.append(CellOutput.from_matplotlib_figure(fig))
    plt.close("all")
    return outputs


def configure_matplotlib():
    """Configure matplotlib for non-interactive use in the notebook."""
    plt.switch_backend("agg")
    original_show = plt.show

    def custom_show(*args, **kwargs):
        pass

    plt.show = custom_show
    return original_show


def reset_matplotlib(original_show) -> None:
    """Reset matplotlib to its original configuration."""
    plt.show = original_show
