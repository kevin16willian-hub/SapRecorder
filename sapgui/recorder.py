import ctypes
import re
import time
from collections import deque

import comtypes.client
import pythoncom
import pywintypes
from comtypes import COMObject, IUnknown

from .labels import label_for
from .model import Script, Step

_SAP_OCX = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\sapfewse.ocx"
_EVENTS_IID = "{67A71FA4-9381-4061-B3BB-74A545C75874}"  # ISapSessionEvents
_ID_PREFIX = re.compile(r"^/app/con\[\d+\]/ses\[\d+\]/")
_TITLE_PREFIX = re.compile(r"^\w+\(\d+\)/\d+\s+")  # "Q11(1)/200 " in the window title
_TABLE_CELL = re.compile(r"/tbl[^/]+/[^/]+\[\d+,\d+\]$")

comtypes.client.GetModule(_SAP_OCX)
import comtypes.gen.SAPFEWSELib as _lib  # noqa: E402


def command_to_step(component_id: str, command) -> Step:
    """Convert one CommandArray entry, e.g. ('SP', 'text', 'me23n') or ('M', 'press')."""
    tag, member, *args = command
    kind = {"SP": "set", "GP": "get"}.get(tag, "call")
    return Step(_ID_PREFIX.sub("", component_id), member, kind, args)


# Methods SAP records as a getter whose result the next command acts on.
_CHAIN_METHODS = {"getAbsoluteRow", "getCell"}


class _Chainer:
    """Joins getter commands with the command that acts on their result, e.g.
    ('M','getAbsoluteRow',2) + ('SP','selected',True) -> .getAbsoluteRow(2).selected = True."""

    def __init__(self):
        self.pending = None  # (component_id, [[name, args or None], ...])

    def feed(self, component_id: str, command) -> list[Step]:
        out = []
        if self.pending and self.pending[0] != component_id:
            out.append(self.flush())
        tag, member, *args = command
        if tag == "GP" or (tag == "M" and member in _CHAIN_METHODS):
            chain = self.pending[1] if self.pending else []
            self.pending = (component_id, chain + [[member, list(args) if tag == "M" else None]])
            return out
        step = command_to_step(component_id, command)
        if self.pending:
            step.chain = self.pending[1]
            self.pending = None
        out.append(step)
        return out

    def flush(self) -> Step | None:
        if not self.pending:
            return None
        component_id, chain = self.pending
        self.pending = None
        *head, (name, args) = chain
        step = Step(_ID_PREFIX.sub("", component_id), name, "get" if args is None else "call", args or [])
        step.chain = head
        return step


class _Sink(COMObject):
    # pywin32 cannot sink this typelib (makepy fails), so the sink is a comtypes object.
    # Callbacks only queue data; screen reads happen later in Recorder.poll() on the main loop.
    _com_interfaces_ = [_lib.ISapSessionEvents]

    def __init__(self, session, cell_clicks=True):
        super().__init__()
        self.session = session
        self.cell_clicks = cell_clicks
        self._last_click = None
        self.queue: deque = deque()
        self.chainer = _Chainer()
        self.active = False

    def Change(self, Session, Component, CommandArray):
        component_id = Component.Id
        # SAP delivers field edits together with the request that leaves the screen, so the
        # label must be read now, while the component still exists. The event's own component is a
        # comtypes lazy object that cannot walk Children, so it is re-fetched through pywin32.
        try:
            label = label_for(self.session, component_id) or ""
        except Exception:
            label = ""
        for command in CommandArray:
            for step in self.chainer.feed(component_id, command):
                if self.active:
                    if not step.chain:
                        step.comment = label
                    self.queue.append(step)

    def EndRequest(self, Session):
        if self.active:
            self.queue.append(None)  # screen may have changed

    def FocusChanged(self, Session, NewFocusedControl):
        # A single click on a cell only raises FocusChanged; no Change follows until it is edited.
        if not (self.active and self.cell_clicks):
            return
        try:
            steps = self._click_steps(NewFocusedControl.Id)
        except Exception:
            return
        self.queue.extend(steps)

    def _click_steps(self, component_id: str) -> list[Step]:
        relative = _ID_PREFIX.sub("", component_id)
        if _TABLE_CELL.search(component_id):
            if relative == self._last_click:
                return []
            self._last_click = relative
            node = self.session.findById(relative)
            title = label_for(self.session, relative)
            step = Step(relative, "setFocus", "call")
            step.comment = f"{title}: {node.Text}" if title else node.Text
            return [step]
        node = self.session.findById(relative)
        if node.Type != "GuiShell" or getattr(node, "SubType", "") != "GridView":
            return []
        row, column = node.CurrentCellRow, node.CurrentCellColumn
        if (relative, row, column) == self._last_click:
            return []
        self._last_click = (relative, row, column)
        column_step = Step(relative, "currentCellColumn", "set", [column])
        try:
            column_step.comment = f"{node.GetColumnTitles(column)[0]}: {node.GetCellValue(row, column)}"
        except Exception:
            column_step.comment = ""
        return [Step(relative, "currentCellRow", "set", [row]), column_step]

    def __getattr__(self, name):
        # comtypes looks up "ISapSessionEvents_<event>" before "<event>"; the prefixed name must miss
        # so that Change resolves to the real method. Other events (StartRequest, ...) are ignored.
        if name.startswith(("_", "ISapSessionEvents_")):
            raise AttributeError(name)
        return lambda *args: None


class Recorder:
    def __init__(self, session, on_step=None, cell_clicks=True):
        self.session = session
        self._on_step = on_step
        self.cell_clicks = cell_clicks
        self.steps: list[Step] = []
        self._cp = None
        self._cookie = None
        self._sink = None
        self._screen = None

    def start(self) -> None:
        self._sink = _Sink(self.session, self.cell_clicks)
        pointer = self._sink.QueryInterface(IUnknown)
        address = ctypes.cast(pointer, ctypes.c_void_p).value
        unknown = pythoncom.ObjectFromAddress(address, pythoncom.IID_IUnknown)
        container = self.session._oleobj_.QueryInterface(pythoncom.IID_IConnectionPointContainer)
        self._cp = container.FindConnectionPoint(pywintypes.IID(_EVENTS_IID))
        self._cookie = self._cp.Advise(unknown)
        self.session.Record = True
        # SAP emits a maximize Change as soon as recording is switched on; discard it.
        self.pump(0.5)
        self.steps.clear()
        self._sink.queue.clear()
        self._sink.active = True
        self._check_screen()

    def _emit(self, step: Step) -> None:
        last = self.steps[-1] if self.steps else None
        # A click already recorded as setFocus can be followed by SAP's own setFocus Change.
        if (last and step.member == "setFocus" and last.member == "setFocus"
                and last.component_id == step.component_id and not step.chain):
            return
        self.steps.append(step)
        if self._on_step:
            self._on_step(step)

    def _check_screen(self) -> None:
        try:
            title = _TITLE_PREFIX.sub("", self.session.ActiveWindow.Text).strip()
            info = self.session.Info
            key = (info.Program, info.ScreenNumber, title)
        except Exception:
            return
        if key != self._screen:
            self._screen = key
            self._emit(Step("", f"Tela atual: {title}", "comment"))

    def poll(self) -> None:
        """Emit queued steps and detect screen changes; call from the thread that started the recorder."""
        queue = self._sink.queue
        while queue:
            item = queue.popleft()
            if item is None:
                self._check_screen()
            else:
                self._emit(item)

    def pump(self, seconds: float) -> None:
        """Process COM messages so events are delivered, then resolve them."""
        end = time.time() + seconds
        while time.time() < end:
            pythoncom.PumpWaitingMessages()
            if self._sink and self._sink.active:
                self.poll()
            time.sleep(0.02)

    def stop(self, name: str) -> Script:
        self.pump(0.3)
        self.session.Record = False
        self._cp.Unadvise(self._cookie)
        leftover = self._sink.chainer.flush()
        if leftover:
            self.steps.append(leftover)
        return Script(name, list(self.steps))
