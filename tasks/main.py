import os
from typing import List
from fastapi import FastAPI, HTTPException
from models import Task_Pydantic, TaskIn_Pydantic, Tasks
from pydantic import BaseModel
from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise


app = FastAPI(title="Tasks Service")


class Status(BaseModel):
    message: str


@app.get("/tasks", response_model=List[Task_Pydantic])
async def get_tasks():
    return await Task_Pydantic.from_queryset(Tasks.all())


@app.post("/add_task")
async def add_task(task: TaskIn_Pydantic):
    task_obj = await Tasks.create(**task.dict(exclude_unset=True))
    return await Task_Pydantic.from_tortoise_orm(task_obj)


@app.post("/shuffle_tasks")
async def shuffle_tasks(task_id: int):
    pass


@app.get("/get_tasks")
async def get_tasks(task_id: int, task: TaskIn_Pydantic):
    await Tasks.filter(id=task_id).update(**task.dict(exclude_unset=True))
    return await Task_Pydantic.from_queryset_single(Tasks.get(id=task_id))


@app.delete(
    "/task/{task_id}",
    response_model=Status,
    responses={404: {"model": HTTPNotFoundError}}
)
async def delete_task(task_id: int):
    deleted_count = await Tasks.filter(id=task_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail=f"User {task_id} not found")
    return Status(message=f"Deleted task {task_id}")


register_tortoise(
    app,
    db_url=os.environ.get("DATABASE_URL", "postgres://postgres:password@localhost:5432/postgres"),
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
