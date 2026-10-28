"""Configuration: paths, settings, environment variables and service catalogues."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
KB_DIR = ROOT / "kb" / "sops"
RUNTIME_DIR = ROOT / "data" / "runtime"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines). Existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv()


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


@lru_cache
def settings() -> dict:
    return yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text(encoding="utf-8"))


@dataclass(eq=False)  # identity hash so that it can be used as a cache key
class Catalogue:
    """Service catalogue: categories, applications and their resolver groups."""

    name: str
    categories: list[dict]
    applications: list[dict]
    auto_categories: list[str] = field(default_factory=list)
    security_category: str | None = None
    security_group: str | None = None
    impact_keywords: dict = field(default_factory=dict)
    urgency_keywords: dict = field(default_factory=dict)

    @property
    def category_names(self) -> list[str]:
        return [c["name"] for c in self.categories]

    @property
    def application_names(self) -> list[str]:
        return [a["name"] for a in self.applications]

    @property
    def groups(self) -> list[str]:
        gs = [a["group"] for a in self.applications]
        if self.security_group:
            gs.append(self.security_group)
        return sorted(set(gs))

    def group_for(self, application: str) -> str | None:
        for a in self.applications:
            if a["name"] == application:
                return a["group"]
        return None

    def describe(self) -> str:
        """Text block given to the LLM."""
        cats = "\n".join(f"- {c['name']}: {c['description']}" for c in self.categories)
        apps = "\n".join(f"- {a['name']}: {a['description']}" for a in self.applications)
        return f"Categories:\n{cats}\n\nApplications:\n{apps}"


@lru_cache
def load_catalogue(name: str = "d3") -> Catalogue:
    data = yaml.safe_load((CONFIG_DIR / f"catalogue_{name}.yaml").read_text(encoding="utf-8"))
    return Catalogue(
        name=data["name"],
        categories=data["categories"],
        applications=data["applications"],
        auto_categories=data.get("auto_categories") or [],
        security_category=data.get("security_category"),
        security_group=data.get("security_group"),
        impact_keywords=data.get("impact_keywords") or {},
        urgency_keywords=data.get("urgency_keywords") or {},
    )
