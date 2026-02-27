"""Task model matching the specification in docs/tasks.md."""

from pydantic import BaseModel, ConfigDict, Field

from agentic_patterns.core.tasks.task_status import TaskStatus


class Task(BaseModel):
    """A unit of work with dependencies and ownership."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = ""
    subject: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    active_form: str | None = Field(default=None, alias="activeForm")
    owner: str | None = None
    blocks: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default=[], alias="blockedBy")
    metadata: dict = Field(default_factory=dict)

    def model_dump_json_file(self) -> str:
        """Serialize to JSON using camelCase field names for file storage."""
        return self.model_dump_json(by_alias=True, indent=2)

    @classmethod
    def from_json_file(cls, data: str) -> "Task":
        return cls.model_validate_json(data)

    def __str__(self) -> str:
        parts = [f"#{self.id} [{self.status.value}] {self.subject}"]
        if self.owner:
            parts.append(f"  owner: {self.owner}")
        if self.blocked_by:
            parts.append(f"  blockedBy: {self.blocked_by}")
        if self.blocks:
            parts.append(f"  blocks: {self.blocks}")
        return "\n".join(parts)
