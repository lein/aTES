import os
import json
import random
import asyncio
from uuid import UUID
from typing import List

import httpx
import aiokafka
from fastapi import Depends, FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from tortoise.contrib.fastapi import register_tortoise

from models import (
    Task_Pydantic, TaskIn_Pydantic, Tasks, TaskStatus, UserIn_Pydantic, Users)


auth_url = os.environ.get("AUTH_URL", "http://0.0.0.0:3000")
kafka_url = os.environ.get("KAFKA_URL", "localhost:9092")
tasks_lifecycle_topic = "tasks-lifecycle"


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)


ev_serializer = lambda x: json.dumps(x, cls=UUIDEncoder).encode("ascii")
ev_deserializer = lambda x: json.loads(x.decode("utf-8"))


app = FastAPI(title="Tasks Service")
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{auth_url}/oauth/authorize",
    tokenUrl="/oauth/token", scopes={"tasks": "tasks"})

consumer_users = aiokafka.AIOKafkaConsumer(
    "accounts-stream",
    bootstrap_servers=kafka_url,
    value_deserializer=ev_deserializer)
consumer_users_roles = aiokafka.AIOKafkaConsumer(
    "accounts",
    bootstrap_servers=kafka_url,
    value_deserializer=ev_serializer)
producer = aiokafka.AIOKafkaProducer(
    bootstrap_servers=kafka_url,
    value_serializer=ev_serializer)


async def consume_users():
    try:
        async for msg in consumer_users:
            if msg.value["event_name"] == "AccountCreated":
                user = UserIn_Pydantic(
                    email=msg.value["data"]["email"],
                    public_id=msg.value["data"]["public_id"]
                )
                await Users.get_or_create(**user.dict(exclude_unset=True))
            elif msg.value["event_name"] == "AccountUpdated":
                user = UserIn_Pydantic(
                    email=msg.value["data"]["email"],
                    public_id=msg.value["data"]["public_id"]
                )
                await Users.get_or_create(**user.dict(exclude_unset=True))
            elif msg.value["event_name"] == "AccountDeleted":
                await Users.filter(public_id=msg.value["data"]["public_id"]).delete()
            else:
                pass
    finally:
        await consumer_users.stop()


async def consume_user_roles():
    try:
        async for msg in consumer_users_roles:
            if msg.value["event_name"] == "AccountRoleChanged":
                await Users.filter(public_id=msg.value["data"]["public_id"]).update(role=msg.value["data"]["role"])
            else:
                pass
    finally:
        await consumer_users_roles.stop()


@app.on_event("startup")
async def startup_event():
    await consumer_users.start()
    await consumer_users_roles.start()
    await producer.start()
    asyncio.create_task(consume_users())
    asyncio.create_task(consume_user_roles())


@app.on_event("shutdown")
async def shutdown_event():
    await consumer_users.stop()
    await consumer_users_roles.stop()
    await producer.stop()


@app.post("/oauth/token")
async def token(
    grant_type: str=Form(...), code: str=Form(...),
    client_id: str=Form(...), client_secret: str=Form(...),
    redirect_uri: str=Form(...)
):
    """Proxy method to oauth service for Swagger UI"""
    args = {
        "grant_type": grant_type,
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{auth_url}/oauth/token",
            headers={"content-type": "application/x-www-form-urlencoded"},
            data=args)
        return JSONResponse(content=r.json(), status_code=r.status_code)


@app.get("/get_tasks", response_model=List[Task_Pydantic])
async def get_tasks(token: str=Depends(oauth2_scheme)):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{auth_url}/accounts/current.json",
            headers={"authorization": f"bearer {token}"})
        user = r.json()
    if user["role"] in ["admin", "accountant"]:
        return await Task_Pydantic.from_queryset(Tasks.all())
    elif user["role"] == "worker":
        return await Task_Pydantic.from_queryset(
            Task_Pydantic.from_queryset(Tasks.filter(user_public_id=user["public_id"])))


@app.post("/add_task")
async def add_task(task: TaskIn_Pydantic):
    task_obj = await Tasks.create(**task.dict(exclude_unset=True))
    ev1 = {
        "event_name": "NewTaskAdded",
        "data": {
            "public_id": task_obj.public_id,
            "user_public_id": task_obj.user_public_id
        }
    }
    await producer.send(tasks_lifecycle_topic, ev1)
    ev2 = {
        "event_name": "TaskAssigned",
        "data": {
            "public_id": task_obj.public_id,
            "user_public_id": task_obj.user_public_id
        }
    }
    await producer.send(tasks_lifecycle_topic, ev2)
    return await Task_Pydantic.from_tortoise_orm(task_obj)


@app.post("/shuffle_tasks")
async def shuffle_tasks():
    tasks = await Tasks.filter(status=TaskStatus.open)
    users_public_ids = [user.public_id for user in await Users.all()]
    batch = producer.create_batch()
    for task_obj in tasks:
        task_obj.user_public_id = random.choice(users_public_ids)
        await task_obj.save()
        ev = {
            "event_name": "TaskAssigned",
            "data": {
                "public_id": task_obj.public_id,
                "user_public_id": task_obj.user_public_id
            }
        }
        batch.append(key=None, value=ev_serializer(ev), timestamp=None)
    partitions = await producer.partitions_for(tasks_lifecycle_topic)
    partition = random.choice(tuple(partitions))
    await producer.send_batch(batch, tasks_lifecycle_topic, partition=partition)
    return {"msg": "OK"}


@app.post("/complete_task")
async def complete_task(task_id: int):
    task_obj = await Tasks.get(id=task_id)
    task_obj.status = TaskStatus.done
    await task_obj.save()
    ev = {
        "event_name": "TaskCompleted",
        "data": {
            "public_id": task_obj.public_id,
            "user_public_id": task_obj.user_public_id
        }
    }
    await producer.send(tasks_lifecycle_topic, ev)
    return await Task_Pydantic.from_tortoise_orm(task_obj)


register_tortoise(
    app,
    db_url=os.environ.get("DATABASE_URL", "postgres://postgres:password@localhost:5432/postgres"),
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
