import re

_BUTTON_LIKE = {"GuiButton", "GuiRadioButton", "GuiCheckBox", "GuiTab", "GuiMenu"}
_FIELDS = {"GuiCTextField", "GuiTextField", "GuiComboBox", "GuiPasswordField", "GuiFormattedTextField"}
_PREFIX = re.compile(r"^(ctxt|txt|cmb|pwd)")
_CELL = re.compile(r"\[(\d+),\d+\]$")


def _clean(text) -> str | None:
    return " ".join((text or "").split()).rstrip(":").strip() or None


def _sibling_label(node) -> str | None:
    parent = node.Parent
    try:
        # SAP names the label after the field: ctxtEINA-LIFNR <-> lblEINA-LIFNR.
        return _clean(parent.FindByName("lbl" + _PREFIX.sub("", node.Name), "GuiLabel").Text)
    except Exception:
        pass
    best = None
    for i in range(parent.Children.Count):
        child = parent.Children(i)
        if child.Type == "GuiLabel" and abs(child.Top - node.Top) <= 3 and child.Left < node.Left:
            if best is None or child.Left > best.Left:
                best = child
    return _clean(best.Text) if best else None


def _column_title(node, component_id: str) -> str | None:
    column = int(_CELL.search(component_id).group(1))
    return _clean(node.Parent.Columns.ElementAt(column).Title)


def label_for(session, component_id: str) -> str | None:
    return label_of(session.findById(component_id), component_id)


def label_of(node, component_id: str) -> str | None:
    """Human-readable name of a screen element (field label, button text, column title)."""
    kind = node.Type
    if kind in _BUTTON_LIKE:
        return _clean(node.Text) or _clean(node.Tooltip)
    if kind in _FIELDS:
        if "/tbl" in component_id and _CELL.search(component_id):
            return _column_title(node, component_id)
        return _sibling_label(node) or _clean(node.Tooltip)
    return None
