import os
from typing import List

import httpx
from pydantic import BaseModel
from fastapi import Depends, FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from tortoise.contrib.fastapi import register_tortoise
from models import Task_Pydantic, TaskIn_Pydantic, Tasks


app = FastAPI(title="Tasks Service")
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="http://0.0.0.0:3000/oauth/authorize",
    tokenUrl="/oauth/token", scopes={"tasks": "tasks"})


class Status(BaseModel):
    message: str


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
            "http://0.0.0.0:3000/oauth/token",
            headers={"content-type": "application/x-www-form-urlencoded"},
            data=args)
        return JSONResponse(content=r.json(), status_code=r.status_code)


@app.get("/get_tasks", response_model=List[Task_Pydantic])
async def get_tasks(token: str=Depends(oauth2_scheme)):
    return await Task_Pydantic.from_queryset(Tasks.all())


@app.post("/add_task")
async def add_task(task: TaskIn_Pydantic):
    pass


@app.post("/shuffle_tasks")
async def shuffle_tasks(task_id: int):
    pass


register_tortoise(
    app,
    db_url=os.environ.get("DATABASE_URL", "postgres://postgres:password@localhost:5432/postgres"),
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
