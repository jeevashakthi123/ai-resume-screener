"""
utils/visualizer.py
Generates bar-chart visualisations of candidate rankings.
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CHART_DIR = os.path.join("static", "charts")
os.makedirs(CHART_DIR, exist_ok=True)


def generate_chart(
    candidates: List[Dict[str, Any]],
    top_n: int = 10,
) -> Optional[str]:
    """
    Generate a horizontal bar chart of the top-N candidates.

    Parameters
    ----------
    candidates : list of dict
        Ranked candidate records (must contain ``name`` and ``match_pct``).
    top_n : int
        Maximum number of bars to display.

    Returns
    -------
    str or None
        Relative path to the saved PNG, or None on failure.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend (safe for Flask)
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        top = candidates[:top_n]
        if not top:
            return None

        names = [c["name"] for c in top]
        scores = [c["match_pct"] for c in top]
        tiers = [c.get("tier", "") for c in top]

        # Colour map by tier
        TIER_COLOURS = {
            "Excellent": "#22c55e",
            "Strong":    "#3b82f6",
            "Good":      "#f59e0b",
            "Fair":      "#f97316",
            "Low":       "#ef4444",
        }
        colours = [TIER_COLOURS.get(t, "#94a3b8") for t in tiers]

        fig, ax = plt.subplots(figsize=(10, max(4, len(top) * 0.65)))
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#1e293b")

        y_pos = np.arange(len(top))
        bars = ax.barh(y_pos, scores, color=colours, edgecolor="none", height=0.6)

        # Score labels
        for bar, score in zip(bars, scores):
            ax.text(
                min(score + 1, 98),
                bar.get_y() + bar.get_height() / 2,
                f"{score:.1f}%",
                va="center", ha="left",
                color="white", fontsize=9, fontweight="bold",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, color="white", fontsize=10)
        ax.set_xlabel("Match %", color="#94a3b8", fontsize=10)
        ax.set_title("Candidate Ranking", color="white", fontsize=14, fontweight="bold", pad=12)
        ax.set_xlim(0, 105)
        ax.tick_params(colors="white")
        ax.spines[:].set_visible(False)
        ax.xaxis.set_tick_params(colors="#64748b")
        ax.grid(axis="x", color="#334155", linestyle="--", alpha=0.5)
        ax.invert_yaxis()

        # Legend
        legend_patches = [
            mpatches.Patch(color=col, label=tier)
            for tier, col in TIER_COLOURS.items()
        ]
        ax.legend(
            handles=legend_patches,
            loc="lower right",
            framealpha=0.2,
            labelcolor="white",
            fontsize=8,
        )

        plt.tight_layout()

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_{timestamp}.png"
        chart_path = os.path.join(CHART_DIR, filename)
        plt.savefig(chart_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

        logger.info("Chart saved: %s", chart_path)
        return chart_path

    except ImportError:
        logger.warning("matplotlib not installed; skipping chart generation.")
        return None
    except Exception as exc:
        logger.error("Chart generation failed: %s", exc)
        return None
