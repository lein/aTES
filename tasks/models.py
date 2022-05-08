from enum import Enum
from uuid import uuid4, UUID
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class TaskStatus(str, Enum):
    open = "Open"
    done = "Done"


class Tasks(models.Model):
    """
    The Task model
    """
    id: int = fields.IntField(pk=True)
    public_id: UUID = fields.UUIDField(default=uuid4)
    description: str = fields.CharField(max_length=1000)
    status: TaskStatus = fields.CharEnumField(TaskStatus, default=TaskStatus.open)
    user_id: UUID = fields.UUIDField()


Task_Pydantic = pydantic_model_creator(Tasks, name="Task")
TaskIn_Pydantic = pydantic_model_creator(Tasks, name="TaskIn", include=("description",))
