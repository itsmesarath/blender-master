"""Geometry Nodes modifier inputs (5.2 API: ``mod.properties.inputs``)."""
from __future__ import annotations


def input_identifier(mod, name: str) -> str:
    for item in mod.node_group.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == name:
            return item.identifier
    raise KeyError(f"{mod.node_group.name} has no input named {name!r}")


def set_input(mod, name: str, value=None, attribute: str | None = None) -> None:
    """Set a GN modifier input by its display name; ``attribute`` switches it to attribute mode."""
    item = getattr(mod.properties.inputs, input_identifier(mod, name))
    if attribute is not None:
        item.type = "ATTRIBUTE"
        item.attribute_name = attribute
    else:
        item.value = value


def get_input(mod, name: str):
    return getattr(mod.properties.inputs, input_identifier(mod, name)).value
