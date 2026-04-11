---
title: Wildfire Containment Coordinator
emoji: 🔥
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
license: mit
---

# 🔥 Wildfire Containment Coordinator

An **LLM-powered autonomous agent** that coordinates wildfire containment in real-time using a grid-based simulation environment — built for the **OpenEnv Hackathon by Scaler × Meta**.

---

## 🧠 What It Does

The agent observes a live wildfire grid and autonomously decides containment actions at each timestep using `Qwen/Qwen2.5-72B-Instruct` via the HuggingFace Router API. It is evaluated across three difficulty levels — **easy**, **medium**, and **hard** — and scored on how effectively it contains the fire.

---

## ⚙️ Architecture

```
┌─────────────────────────────────────────┐
│              inference.py               │
│   (LLM Agent — Qwen2.5-72B-Instruct)   │
└────────────────────┬────────────────────┘
                     │ HTTP (POST /reset, /step, /grader)
┌────────────────────▼────────────────────┐
│         FastAPI Server (main.py)        │
│  ┌─────────────┐   ┌─────────────────┐  │
│  │   env.py    │   │   grader.py     │  │
│  │ WildfireEnv │   │  Scoring Logic  │  │
│  └─────────────┘   └─────────────────┘  │
│         ┌─────────────────┐             │
│         │    tasks.py     │             │
│         │ Task Definitions│             │
│         └─────────────────┘             │
└─────────────────────────────────────────┘
         Deployed via Docker on HF Spaces
              (port 7860, uvicorn)
```

---

## 🕹️ Agent Actions

At each step, the LLM agent picks exactly one action:

| Action | Description |
|---|---|
| `deploy_crew` | Send a firefighting crew to grid cell (x, y) |
| `airdrop` | Drop fire retardant at coordinates (x, y) |
| `build_break` | Build a firebreak at location (x, y) |
| `evacuate_zone` | Evacuate the current danger zone |
| `hold` | Wait and observe (no intervention) |

---

## 🔄 Evaluation Flow

```
for each task in [task_easy, task_medium, task_hard]:
    POST /reset  →  get initial grid observation
    loop until done:
        LLM observes grid + burning_cells
        LLM returns action (JSON)
        POST /step  →  get reward + updated observation
    POST /grader  →  get final_score
    print [END] task=... score=... steps=...
```

The validator expects `[START]`, `[STEP]`, and `[END]` blocks printed to **stdout** with `flush=True`.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| LLM | `Qwen/Qwen2.5-72B-Instruct` via `router.huggingface.co` |
| Agent | Python + OpenAI-compatible client |
| API Server | FastAPI + Uvicorn |
| Environment | Custom WildfireEnv (OpenEnv format) |
| Containerization | Docker (Python 3.11-slim) |
| Deployment | HuggingFace Spaces |

---

## 🚀 Running Locally

```bash
# Clone the space
git clone https://huggingface.co/spaces/ixanami/wildfire-containment-coordinator
cd wildfire-containment-coordinator

# Install dependencies
pip install -r requirements.txt

# Start the environment server
uvicorn main:app --host 0.0.0.0 --port 7860

# In another terminal, run the agent
HF_TOKEN=your_token_here ENV_URL=http://127.0.0.1:7860 python inference.py
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/reset` | Initialize a task `{"task_id": "task_easy"}` |
| POST | `/step` | Execute an action `{"action_type": "...", "x": int, "y": int}` |
| POST | `/grader` | Get final score `{"task_id": "..."}` |

---

**Team Toronto** 
