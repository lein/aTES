from email.policy import default
from enum import Enum, unique
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
    user_public_id: UUID = fields.UUIDField()


class Users(models.Model):
    """
    The user model
    """
    id: int = fields.IntField(pk=True)
    public_id: UUID = fields.UUIDField(unique=True)
    role: str = fields.CharField(max_length=16, default="worker")
    email: str = fields.CharField(null=False, max_length=255)


Task_Pydantic = pydantic_model_creator(Tasks, name="Task")
TaskIn_Pydantic = pydantic_model_creator(Tasks, name="TaskIn", include=("description", "user_public_id"))
User_Pydantic = pydantic_model_creator(Users, name="User")
UserIn_Pydantic = pydantic_model_creator(Users, name="UserIn", exclude=("id", "role"))
