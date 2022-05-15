from enum import Enum, IntEnum
from pydantic import BaseModel, Field


class AccountsCreatedName(str, Enum):
    AccountCreated = "AccountCreated"


class AccountsCreatedv1EventData(BaseModel):
    public_id: str = Field()
    email: str = Field()
    full_name: str = Field()
    position: str = Field()


class AccountsCreatedv1(BaseModel):
    event_id: str = Field()
    event_version: IntEnum = Field()
    event_name: AccountsCreatedName = Field()
    event_time: str = Field()
    producer: str = Field()
    event_data: AccountsCreatedv1EventData
