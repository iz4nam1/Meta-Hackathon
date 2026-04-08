from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

from env import WildfireEnv, Action
from tasks import get_task
from grader import grade

app = FastAPI()

_env: Optional[WildfireEnv] = None


class StepRequest(BaseModel):
    action_type: str
    x: Optional[int] = None
    y: Optional[int] = None
    zone: Optional[str] = None


class GraderRequest(BaseModel):
    task_id: str


@app.get("/")
def root():
    return {"status": "running"}


# 🔥 FINAL FIX — ACCEPT EMPTY BODY
@app.post("/reset")
def reset(req: dict = Body(default={"task_id": "task_easy"})):
    global _env

    try:
        task_id = req.get("task_id", "task_easy")

        task = get_task(task_id)
        _env = WildfireEnv(task)
        obs = _env.reset()

        return {
            "observation": obs.model_dump(),
            "task": {
                "id": task["id"],
                "name": task["name"],
                "difficulty": task["difficulty"],
                "max_steps": task["max_steps"],
                "objectives": task["objectives"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
def step(req: StepRequest):
    global _env

    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first")

    try:
        action = Action(
            action_type=req.action_type,
            x=req.x,
            y=req.y,
            zone=req.zone
        )

        obs, reward, done, info = _env.step(action)

        return {
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/grader")
def grader(req: GraderRequest):
    global _env

    if _env is None:
        raise HTTPException(status_code=400, detail="Run episode first")

    try:
        task = get_task(req.task_id)
        return grade(_env, task)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))