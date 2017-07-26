import typing as typ
import pathlib as pl
import os.path

LabelExtractor = typ.Callable[[pl.Path], str]


def default_label_extractor(item_file_name: pl.Path) -> str:
    item_stub, _ = os.path.splitext(item_file_name)
    return item_stub.rstrip('0123456789')
