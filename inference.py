import os
import json
import time
import requests
import sys
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL      = os.getenv("ENV_URL", "http://127.0.0.1:7860")

TASKS = ["task_easy", "task_medium", "task_hard"]

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def api(method, path, body=None):
    url = f"{ENV_URL}{path}"
    r = requests.request(method, url, json=body, timeout=30)
    r.raise_for_status()
    return r.json()

SYSTEM_PROMPT = """Return EXACTLY ONE action:
{"action_type": "deploy_crew", "x": int, "y": int}
{"action_type": "airdrop", "x": int, "y": int}
{"action_type": "build_break", "x": int, "y": int}
{"action_type": "evacuate_zone"}
{"action_type": "hold"}
No explanation. JSON only.
"""

def llm_decide(obs):
    msg = f"Grid: {obs['grid']} Burning: {obs['burning_cells']}"
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg}
            ],
            temperature=0.2,
            max_tokens=200
        )
        raw = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr, flush=True)
        return {"action_type": "hold"}
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"action_type": "hold"}

def fix_action(a):
    if isinstance(a, list):
        a = a[0]
    if "action" in a:
        if isinstance(a["action"], dict):
            a = a["action"]
        else:
            return {"action_type": "hold"}
    if "target" in a:
        t = a["target"]
        if isinstance(t, list) and len(t) == 2:
            return {
                "action_type": a.get("type") or "hold",
                "x": t[1],
                "y": t[0]
            }
    if "action_type" in a:
        return a
    return {"action_type": "hold"}

def run_task(task_id):
    print(f"[START] task={task_id}", flush=True)
    try:
        data = api("POST", "/reset", {"task_id": task_id})
        obs = data["observation"]
        steps = 0

        while not obs["done"]:
            raw = llm_decide(obs)
            action = fix_action(raw)
            result = api("POST", "/step", action)
            obs = result["observation"]
            reward = result["reward"]["total"]
            steps += 1
            print(f"[STEP] step={steps} reward={reward:.4f}", flush=True)
            time.sleep(0.2)

        grade_result = api("POST", "/grader", {"task_id": task_id})
        score = grade_result["final_score"]
        print(f"[END] task={task_id} score={score:.4f} steps={steps}", flush=True)

    except Exception as e:
        print(f"[END] task={task_id} score=0.0000 steps=0", flush=True)
        print(f"Error in {task_id}: {e}", file=sys.stderr, flush=True)

if __name__ == "__main__":
    for t in TASKS:
        run_task(t)
