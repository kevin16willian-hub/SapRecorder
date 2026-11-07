import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pythoncom

if not __package__:  # launched as a plain script (e.g. VS Code Run button)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "sapgui"

from .codegen import step_to_python
from .connection import get_session, list_sessions
from .model import Step
from .recorder import Recorder


class RecorderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("SAP Script Recorder")
        root.geometry("900x560")
        self.recorder: Recorder | None = None
        self.sessions: list[tuple[str, int, int]] = []

        bar = ttk.Frame(root, padding=6)
        bar.pack(fill="x")
        self.record_btn = ttk.Button(bar, text="Record", command=self.start)
        self.stop_btn = ttk.Button(bar, text="Stop", command=self.stop, state="disabled")
        self.clear_btn = ttk.Button(bar, text="Clear", command=self.clear)
        self.copy_btn = ttk.Button(bar, text="Copy", command=self.copy)
        self.save_btn = ttk.Button(bar, text="Save .py", command=self.save)
        for button in (self.record_btn, self.stop_btn, self.clear_btn, self.copy_btn, self.save_btn):
            button.pack(side="left", padx=2)
        self.session_box = ttk.Combobox(bar, state="readonly", width=40)
        self.session_box.pack(side="left", padx=8)
        ttk.Button(bar, text="Refresh", command=self.refresh_sessions).pack(side="left")
        self.cell_clicks = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Cell clicks", variable=self.cell_clicks).pack(side="left", padx=8)

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)
        self.gutter = tk.Text(body, width=4, padx=4, takefocus=0, state="disabled", background="#fffbd0", font=("Consolas", 10))
        self.editor = tk.Text(body, wrap="none", font=("Consolas", 10), undo=True)
        scroll = ttk.Scrollbar(body, command=self._scroll)
        self.editor.configure(yscrollcommand=lambda *a: (scroll.set(*a), self.gutter.yview_moveto(a[0])))
        self.gutter.pack(side="left", fill="y")
        self.editor.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.status = ttk.Label(root, text="Ready", relief="sunken", anchor="w", padding=3)
        self.status.pack(fill="x")

        self.refresh_sessions()

    def _scroll(self, *args):
        self.editor.yview(*args)
        self.gutter.yview(*args)

    def refresh_sessions(self):
        try:
            self.sessions = list_sessions()
        except Exception as exc:
            self.sessions = []
            self.status.config(text=f"SAP GUI not found: {exc}")
        self.session_box["values"] = [label for label, _, _ in self.sessions]
        if self.sessions:
            self.session_box.current(0)

    def _append(self, step: Step):
        self.editor.insert("end", step_to_python(step) + "\n")
        self.editor.see("end")
        self._number_lines()
        self.status.config(text=f"Recording - {len(self.recorder.steps)} steps")

    def _number_lines(self):
        lines = int(self.editor.index("end-1c").split(".")[0])
        self.gutter.config(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(str(n) for n in range(1, lines + 1)))
        self.gutter.config(state="disabled")
        self.gutter.yview_moveto(self.editor.yview()[0])

    def start(self):
        index = self.session_box.current()
        if index < 0:
            messagebox.showwarning("SAP", "No SAP session available.")
            return
        _, connection, session = self.sessions[index]
        try:
            self.recorder = Recorder(
                get_session(connection, session), on_step=self._append, cell_clicks=self.cell_clicks.get()
            )
            self.recorder.start()
        except Exception as exc:
            self.recorder = None
            messagebox.showerror("SAP", f"Could not start recording:\n{exc}")
            return
        self.record_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Recording - 0 steps")

    def stop(self):
        if self.recorder:
            self.recorder.stop("recorded")
            self.recorder = None
        self.record_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.config(text="Stopped")

    def clear(self):
        self.editor.delete("1.0", "end")
        if self.recorder:
            self.recorder.steps.clear()
        self._number_lines()

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.editor.get("1.0", "end-1c"))

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python", "*.py")])
        if path:
            Path(path).write_text(self.editor.get("1.0", "end-1c") + "\n", encoding="utf-8")


def main():
    root = tk.Tk()
    app = RecorderApp(root)
    closed = False

    def close():
        nonlocal closed
        closed = True

    root.protocol("WM_DELETE_WINDOW", close)
    # Tk's own mainloop crashes (GIL error) once SAP events arrive through COM, so drive both loops here.
    while not closed:
        root.update()
        pythoncom.PumpWaitingMessages()
        if app.recorder:
            app.recorder.poll()
        time.sleep(0.01)
    app.stop()
    root.destroy()


if __name__ == "__main__":
    main()
