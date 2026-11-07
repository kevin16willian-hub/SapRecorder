from .model import Script, Step


class StepError(RuntimeError):
    def __init__(self, index: int, step: Step, cause: Exception):
        super().__init__(f"step {index} ({step.component_id} .{step.member}) failed: {cause}")
        self.index = index
        self.step = step


def _run(session, step: Step, inputs: dict) -> None:
    if step.kind == "comment":
        return
    args = [inputs[step.parameter]] if step.parameter else step.args
    owner = session.findById(step.component_id)
    for name, chain_args in step.chain:
        owner = getattr(owner, name) if chain_args is None else getattr(owner, name)(*chain_args)
    if step.kind == "set":
        setattr(owner, step.member, args[0])
    elif step.kind == "get":
        getattr(owner, step.member)
    else:
        getattr(owner, step.member)(*args)


def play(session, script: Script, inputs: dict | None = None) -> None:
    inputs = inputs or {}
    for index, step in enumerate(script.steps):
        try:
            _run(session, step, inputs)
        except Exception as exc:
            raise StepError(index, step, exc) from exc
