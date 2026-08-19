"""Preprocess steps registry — ordered list of steps applied to source files."""

from preprocess.steps.remove_header import RemoveHeaderPreStep
from preprocess.steps.remove_empty_j import RemoveEmptyJStep
from preprocess.steps.dedup_filled_rows import DedupFilledRowsStep
from config import Config
from core import PipelineStep


def get_preprocess_steps(config: Config | None = None) -> list[PipelineStep]:
    config = config or Config()
    steps: list[PipelineStep] = [
        RemoveHeaderPreStep(config),
        DedupFilledRowsStep(config),
    ]
    if config.preprocess_remove_empty_j:
        steps.insert(1, RemoveEmptyJStep(config))
    return steps
