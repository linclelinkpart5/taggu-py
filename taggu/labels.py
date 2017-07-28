import typing as typ
import pathlib as pl

LabelExtractor = typ.Callable[[pl.Path], str]


def default_label_extractor(rel_item_path: pl.Path) -> str:
    item_stem = rel_item_path.stem
    return item_stem.rstrip('0123456789')
