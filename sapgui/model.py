import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Step:
    component_id: str
    member: str  # property or method name
    kind: str  # "set" assigns a property, "call" invokes a method, "get" reads a property, "comment" is a note (text in member)
    args: list = field(default_factory=list)
    label: str = ""  # user-facing name shown in the mapping UI
    chain: list = field(default_factory=list)  # [[name, args or None], ...] applied before member
    comment: str = ""  # trailing note, e.g. the field label
    parameter: str = ""  # when set, the value comes from this named input at play time


@dataclass
class Script:
    name: str
    steps: list[Step] = field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str | Path) -> "Script":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["name"], [Step(**s) for s in data["steps"]])
