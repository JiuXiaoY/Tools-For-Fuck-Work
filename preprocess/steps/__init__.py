"""Preprocess steps registry — ordered list of steps applied to source files."""

from preprocess.steps.remove_header import RemoveHeaderPreStep
# from preprocess.steps.remove_empty_j import RemoveEmptyJStep
from preprocess.steps.dedup_filled_rows import DedupFilledRowsStep


def get_preprocess_steps():
    return [
        RemoveHeaderPreStep(),
        # RemoveEmptyJStep(),
        # DedupFilledRowsStep(),
    ]
