import json

from .model import Script, Step


def _literal(value) -> str:
    # Double quotes match what SAP's own recorder and Scripting Tracker emit.
    return json.dumps(value, ensure_ascii=False) if isinstance(value, str) else repr(value)


def step_to_python(step: Step) -> str:
    if step.kind == "comment":
        return f"# {step.member}"
    line = _call_to_python(step)
    return f"{line}  # {step.comment}" if step.comment else line


def _call_to_python(step: Step) -> str:
    path = "".join(
        "." + (name if args is None else f"{name}({', '.join(_literal(a) for a in args)})")
        for name, args in step.chain
    )
    target = f'session.findById("{step.component_id}"){path}.{step.member}'
    value = step.parameter or ", ".join(_literal(a) for a in step.args)
    if step.kind == "get":
        return target
    if step.kind == "set":
        return f"{target} = {value}"
    return f"{target}({value})"


def to_python(script: Script) -> str:
    body = "\n".join(f"    {step_to_python(s)}" for s in script.steps) or "    pass"
    return f"def {script.name}(session):\n{body}\n"
