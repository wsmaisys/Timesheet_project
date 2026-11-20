"""AI orchestration boundary (SRS §3.3 & §19).

Any future AI assistant must invoke scoped application services with explicit
user confirmation and audit attribution — never write directly to database tables.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SuggestedEntryDraft:
    work_date: str
    project_id: str
    task_id: str
    duration_minutes: int
    description: str
    requires_user_confirmation: bool = True


class AIServiceBoundary(Protocol):
    def suggest_draft_entries(self, actor_id: str, period_start: str) -> list[SuggestedEntryDraft]:
        ...
