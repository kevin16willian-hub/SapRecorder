import win32com.client


def _engine():
    return win32com.client.GetObject("SAPGUI").GetScriptingEngine


def get_session(connection: int = 0, session: int = 0):
    """Attach to a running SAP GUI and return the GuiSession."""
    return _engine().Children(connection).Children(session)


def list_sessions() -> list[tuple[str, int, int]]:
    """Return (label, connection index, session index) for every open session."""
    engine = _engine()
    found = []
    for c in range(engine.Children.Count):
        connection = engine.Children(c)
        for s in range(connection.Children.Count):
            info = connection.Children(s).Info
            found.append((f"/app/con[{c}]/ses[{s}] = {info.SystemName}({info.SessionNumber})", c, s))
    return found
