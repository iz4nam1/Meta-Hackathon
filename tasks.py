"""
Wildfire Tasks — Easy → Medium → Hard
======================================
Each task defines a concrete scenario with increasing complexity.
"""

# ─────────────────────────────────────────────
# TASK REGISTRY
# ─────────────────────────────────────────────
TASKS = {

    # ══════════════════════════════════════════
    # TASK 1 — EASY
    # Single ignition point, calm wind, ample resources.
    # Optimal strategy: build firebreak ring, airdrop center.
    # ══════════════════════════════════════════
    "task_easy": {
        "id": "task_easy",
        "name": "Valley Grassfire",
        "difficulty": "easy",
        "description": (
            "A small grassfire has ignited in an open valley. "
            "Wind is calm and predictable. You have ample crews and aircraft. "
            "Contain the fire before it reaches the forest edge."
        ),
        "grid_size": 12,
        "max_steps": 30,
        "seed": 42,
        "crews": 4,
        "aircraft": 3,
        "firebreaks": 25,
        "wind_direction": 45.0,   # NE, steady
        "wind_speed": 0.8,        # calm
        "dynamic_wind": False,
        "ignition_points": [(6, 6)],
        "water_cells": [(0,0),(0,1),(1,0),(1,1)],
        "empty_cells": [],
        "asset_cells": [(2, 9), (3, 9)],
        "layout": "random",
        "success_threshold": 0.85,
        "objectives": [
            "Contain fire to fewer than 10% of grid cells burning",
            "Protect assets at (9,2) and (9,3)",
            "Complete within 30 steps"
        ]
    },

    # ══════════════════════════════════════════
    # TASK 2 — MEDIUM
    # Multiple ignition points, moderate wind, limited aircraft.
    # Requires triage: which fire to tackle first?
    # ══════════════════════════════════════════
    "task_medium": {
        "id": "task_medium",
        "name": "Canyon Multi-Front",
        "difficulty": "medium",
        "description": (
            "Lightning has started three separate fires in a canyon system. "
            "Wind is moderate and occasionally gusts. Aircraft sorties are limited. "
            "A small town on the eastern edge must be protected at all costs."
        ),
        "grid_size": 16,
        "max_steps": 45,
        "seed": 99,
        "crews": 3,
        "aircraft": 2,
        "firebreaks": 18,
        "wind_direction": 270.0,   # West → East (toward town)
        "wind_speed": 1.4,
        "dynamic_wind": True,
        "ignition_points": [(4,4), (8,2), (12,6)],
        "water_cells": [(0,8),(0,9),(1,8),(1,9),(2,8),(2,9)],
        "empty_cells": [(7,7),(8,7),(7,8)],
        "asset_cells": [
            (14,5),(14,6),(14,7),   # Town buildings
            (15,5),(15,6),(15,7)
        ],
        "layout": "random",
        "success_threshold": 0.75,
        "objectives": [
            "Contain all fire fronts within 45 steps",
            "Preserve all 6 town assets",
            "Use fewer than 80% of available resources"
        ]
    },

    # ══════════════════════════════════════════
    # TASK 3 — HARD
    # Mass ignition event, shifting winds, extreme scarcity.
    # Requires adaptive strategy — no fixed plan survives wind shifts.
    # ══════════════════════════════════════════
    "task_hard": {
        "id": "task_hard",
        "name": "Firestorm — Red Flag Warning",
        "difficulty": "hard",
        "description": (
            "Red flag conditions: a firestorm has erupted across a large wilderness area "
            "with critically dry vegetation. Wind is shifting rapidly and intensifying. "
            "You have minimal resources. Two evacuation zones and critical infrastructure "
            "must be defended. Containment is secondary — survival of assets is primary."
        ),
        "grid_size": 20,
        "max_steps": 60,
        "seed": 777,
        "crews": 2,
        "aircraft": 1,
        "firebreaks": 12,
        "wind_direction": 315.0,   # NW initially
        "wind_speed": 2.2,         # Strong
        "dynamic_wind": True,
        "ignition_points": [
            (2,2),(2,10),(2,18),
            (10,5),(10,15),
            (5,1)
        ],
        "water_cells": [
            (10,10),(10,11),(11,10),(11,11),
            (9,10),(9,11)
        ],
        "empty_cells": [(10,9),(11,9),(12,10)],
        "asset_cells": [
            (18,1),(18,2),(19,1),(19,2),   # Evacuation zone A
            (18,17),(18,18),(19,17),(19,18),# Evacuation zone B
            (10,0),(11,0)                   # Water treatment plant
        ],
        "layout": "random",
        "success_threshold": 0.50,
        "objectives": [
            "Protect at least 6 of 10 critical assets",
            "Keep fire from reaching water treatment plant",
            "Achieve any containment within 60 steps under wind shifts"
        ]
    }
}


def get_task(task_id: str) -> dict:
    if task_id not in TASKS:
        raise ValueError(f"Unknown task: {task_id}. Available: {list(TASKS.keys())}")
    return TASKS[task_id]


def list_tasks() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "difficulty": t["difficulty"],
            "description": t["description"],
            "grid_size": t["grid_size"],
            "max_steps": t["max_steps"],
            "resources": {
                "crews": t["crews"],
                "aircraft": t["aircraft"],
                "firebreaks": t["firebreaks"]
            },
            "objectives": t["objectives"],
            "success_threshold": t["success_threshold"]
        }
        for t in TASKS.values()
    ]