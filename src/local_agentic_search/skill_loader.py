from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

SKILL_NAME = "local-web-search"


@dataclass(frozen=True)
class SkillLoadResult:
    skill_name: str
    destination: Path
    overwritten: bool

    def model_dump(self) -> dict[str, object]:
        return {
            "skill_name": self.skill_name,
            "destination": str(self.destination),
            "overwritten": self.overwritten,
        }


def load_skill(
    *,
    project_dir: str | Path | None = None,
    target_dir: str | Path | None = None,
    force: bool = False,
) -> SkillLoadResult:
    if project_dir is not None and target_dir is not None:
        raise ValueError("Pass either project_dir or target_dir, not both.")

    destination = _resolve_destination(project_dir=project_dir, target_dir=target_dir)
    existed = destination.exists()
    if existed and not force:
        raise FileExistsError(
            f"Skill already exists at {destination}. Re-run with --force to update it."
        )

    source = resources.files("local_agentic_search").joinpath("skills", SKILL_NAME)
    if not source.is_dir():
        raise RuntimeError("Packaged local-web-search skill is missing.")

    _copy_tree(source, destination)
    return SkillLoadResult(
        skill_name=SKILL_NAME,
        destination=destination.resolve(),
        overwritten=existed,
    )


def _resolve_destination(
    *,
    project_dir: str | Path | None,
    target_dir: str | Path | None,
) -> Path:
    if target_dir is not None:
        return Path(target_dir)
    return Path(project_dir or Path.cwd()) / ".agents" / "skills" / SKILL_NAME


def _copy_tree(source: Any, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        child_destination = destination / child.name
        if child.is_dir():
            _copy_tree(child, child_destination)
        else:
            child_destination.parent.mkdir(parents=True, exist_ok=True)
            child_destination.write_bytes(child.read_bytes())
