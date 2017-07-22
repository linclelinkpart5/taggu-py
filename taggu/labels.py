import typing as typ
import os.path

LabelExtractor = typ.Callable[[str], str]


def default_label_extractor(item_file_name: str) -> str:
    item_stub, _ = os.path.splitext(item_file_name)
    return item_stub.rstrip('0123456789')
