# """
# Wildfire Grader — Continuous Scoring 0.0 → 1.0
# ================================================
# Multi-factor evaluation with partial credit.
# No binary pass/fail — every dimension scored independently.

# score = (containment * 0.35)
#       + (asset_protection * 0.30)
#       + (efficiency * 0.20)
#       + (speed * 0.15)
# """

# from env import Cell


# def grade(env, task: dict) -> dict:
#     """
#     Grade a completed episode. Returns full breakdown + final score.
#     env: WildfireEnv instance (after episode ends)
#     task: task config dict
#     """
#     grid      = env.grid
#     g         = env.grid_size
#     max_steps = task["max_steps"]
#     step      = env._step_count

#     # ── 1. CONTAINMENT SCORE (0–1) ─────────────
#     burning       = env._count(Cell.BURNING)
#     total_cells   = g * g
#     veg_original  = env._initial_veg
#     cells_burned  = env._cells_burned_this_ep

#     if veg_original == 0:
#         containment_score = 1.0
#     else:
#         # Fraction of original vegetation that survived
#         veg_now    = env._count(Cell.VEG)
#         survived   = veg_now / veg_original
#         containment_score = round(min(1.0, max(0.0, survived)), 4)

#     # ── 2. ASSET PROTECTION SCORE (0–1) ────────
#     assets_total = task.get("asset_cells", [])
#     total_assets = len(assets_total)
#     if total_assets == 0:
#         asset_score = 1.0
#     else:
#         assets_lost  = env._assets_lost
#         assets_saved = max(0, total_assets - assets_lost)
#         asset_score  = round(assets_saved / total_assets, 4)

#     # ── 3. EFFICIENCY SCORE (0–1) ───────────────
#     # Rewards using fewer resources to achieve same containment
#     crews_used     = task["crews"]     - env.resources.crews
#     aircraft_used  = task["aircraft"]  - env.resources.aircraft
#     breaks_used    = task["firebreaks"]- env.resources.firebreaks

#     max_possible   = task["crews"] + task["aircraft"] + task["firebreaks"]
#     total_used     = crews_used + aircraft_used + breaks_used

#     if max_possible == 0:
#         raw_efficiency = 1.0
#     else:
#         # Scale: using 0% resources while fire is contained = 1.0
#         # Using 100% resources = 0.3 (still gets partial credit)
#         usage_ratio    = total_used / max_possible
#         raw_efficiency = 1.0 - (usage_ratio * 0.7)

#     # Efficiency is meaningful only if containment was achieved
#     efficiency_score = round(raw_efficiency * containment_score, 4)

#     # ── 4. SPEED SCORE (0–1) ────────────────────
#     if burning == 0:
#         # Contained early = bonus
#         speed_score = round(1.0 - (step / max_steps) * 0.5, 4)
#     else:
#         # Didn't contain — partial credit for how far we got
#         speed_score = round(max(0.0, 0.5 - (step / max_steps) * 0.3), 4)

#     # ── COMPOSITE SCORE ─────────────────────────
#     weights = {
#         "containment":  0.35,
#         "asset_protection": 0.30,
#         "efficiency":   0.20,
#         "speed":        0.15
#     }
#     final_score = (
#         containment_score  * weights["containment"]  +
#         asset_score        * weights["asset_protection"] +
#         efficiency_score   * weights["efficiency"]   +
#         speed_score        * weights["speed"]
#     )
#     final_score = round(min(1.0, max(0.0, final_score)), 4)

#     # ── OUTCOME LABEL ───────────────────────────
#     threshold = task.get("success_threshold", 0.75)
#     if final_score >= threshold:
#         outcome = "success"
#     elif final_score >= threshold * 0.6:
#         outcome = "partial"
#     else:
#         outcome = "failure"

#     return {
#         "final_score": final_score,
#         "outcome": outcome,
#         "threshold": threshold,
#         "breakdown": {
#             "containment": {
#                 "score": containment_score,
#                 "weight": weights["containment"],
#                 "weighted": round(containment_score * weights["containment"], 4),
#                 "detail": f"{env._count(Cell.VEG)} veg cells survived of {veg_original} original"
#             },
#             "asset_protection": {
#                 "score": asset_score,
#                 "weight": weights["asset_protection"],
#                 "weighted": round(asset_score * weights["asset_protection"], 4),
#                 "detail": f"{max(0,total_assets - env._assets_lost)}/{total_assets} assets protected"
#             },
#             "efficiency": {
#                 "score": efficiency_score,
#                 "weight": weights["efficiency"],
#                 "weighted": round(efficiency_score * weights["efficiency"], 4),
#                 "detail": f"{total_used}/{max_possible} resource units used"
#             },
#             "speed": {
#                 "score": speed_score,
#                 "weight": weights["speed"],
#                 "weighted": round(speed_score * weights["speed"], 4),
#                 "detail": f"Finished in {step}/{max_steps} steps"
#             }
#         },
#         "stats": {
#             "steps_taken": step,
#             "cells_burned": cells_burned,
#             "assets_lost": env._assets_lost,
#             "assets_total": total_assets,
#             "burning_at_end": burning,
#             "episode_reward": round(env._episode_reward, 3),
#             "resources_remaining": {
#                 "crews": env.resources.crews,
#                 "aircraft": env.resources.aircraft,
#                 "firebreaks": env.resources.firebreaks
#             }
#         }
#     }


"""
Wildfire Grader — Continuous Scoring 0.0 → 1.0
================================================
Multi-factor evaluation with partial credit.
No binary pass/fail — every dimension scored independently.

score = (containment * 0.35)
      + (asset_protection * 0.30)
      + (efficiency * 0.20)
      + (speed * 0.15)
"""

from env import Cell


def grade(env, task: dict) -> dict:
    """
    Grade a completed episode. Returns full breakdown + final score.
    env: WildfireEnv instance (after episode ends)
    task: task config dict
    """
    grid      = env.grid
    g         = env.grid_size
    max_steps = task["max_steps"]
    step      = env._step_count

    # ── 1. CONTAINMENT SCORE (0–1) ─────────────
    burning      = env._count(Cell.BURNING)
    total_cells  = g * g

    # Measure: how much of grid is NOT on fire at end (fire-stopped metric)
    # This rewards stopping the spread, not just saving every tree
    non_burning  = total_cells - burning
    containment_score = round(min(1.0, non_burning / total_cells), 4)

    # ── 2. ASSET PROTECTION SCORE (0–1) ────────
    assets_total = task.get("asset_cells", [])
    total_assets = len(assets_total)
    if total_assets == 0:
        asset_score = 1.0
    else:
        assets_lost  = env._assets_lost
        assets_saved = max(0, total_assets - assets_lost)
        asset_score  = round(assets_saved / total_assets, 4)

    # ── 3. EFFICIENCY SCORE (0–1) ───────────────
    # Rewards using fewer resources to achieve same containment
    crews_used     = task["crews"]     - env.resources.crews
    aircraft_used  = task["aircraft"]  - env.resources.aircraft
    breaks_used    = task["firebreaks"]- env.resources.firebreaks

    max_possible   = task["crews"] + task["aircraft"] + task["firebreaks"]
    total_used     = crews_used + aircraft_used + breaks_used

    if max_possible == 0:
        raw_efficiency = 1.0
    else:
        # Scale: using 0% resources while fire is contained = 1.0
        # Using 100% resources = 0.3 (still gets partial credit)
        usage_ratio    = total_used / max_possible
        raw_efficiency = 1.0 - (usage_ratio * 0.7)

    # Efficiency is meaningful only if containment was achieved
    efficiency_score = round(raw_efficiency * containment_score, 4)

    # ── 4. SPEED SCORE (0–1) ────────────────────
    if burning == 0:
        # Contained early = bonus
        speed_score = round(1.0 - (step / max_steps) * 0.5, 4)
    else:
        # Didn't contain — partial credit for how far we got
        speed_score = round(max(0.0, 0.5 - (step / max_steps) * 0.3), 4)

    # ── COMPOSITE SCORE ─────────────────────────
    weights = {
        "containment":      0.30,
        "asset_protection": 0.40,
        "efficiency":       0.15,
        "speed":            0.15
    }
    final_score = (
        containment_score  * weights["containment"]  +
        asset_score        * weights["asset_protection"] +
        efficiency_score   * weights["efficiency"]   +
        speed_score        * weights["speed"]
    )
    final_score = round(min(1.0, max(0.0, final_score)), 4)

    # ── OUTCOME LABEL ───────────────────────────
    threshold = task.get("success_threshold", 0.75)
    if final_score >= threshold:
        outcome = "success"
    elif final_score >= threshold * 0.6:
        outcome = "partial"
    else:
        outcome = "failure"

    return {
        "final_score": final_score,
        "outcome": outcome,
        "threshold": threshold,
        "breakdown": {
            "containment": {
                "score": containment_score,
                "weight": weights["containment"],
                "weighted": round(containment_score * weights["containment"], 4),
                "detail": f"{env._count(Cell.VEG)} veg cells remaining, {burning} still burning of {total_cells} total"
            },
            "asset_protection": {
                "score": asset_score,
                "weight": weights["asset_protection"],
                "weighted": round(asset_score * weights["asset_protection"], 4),
                "detail": f"{max(0,total_assets - env._assets_lost)}/{total_assets} assets protected"
            },
            "efficiency": {
                "score": efficiency_score,
                "weight": weights["efficiency"],
                "weighted": round(efficiency_score * weights["efficiency"], 4),
                "detail": f"{total_used}/{max_possible} resource units used"
            },
            "speed": {
                "score": speed_score,
                "weight": weights["speed"],
                "weighted": round(speed_score * weights["speed"], 4),
                "detail": f"Finished in {step}/{max_steps} steps"
            }
        },
        "stats": {
            "steps_taken": step,
            "cells_burned": env._cells_burned_this_ep,
            "assets_lost": env._assets_lost,
            "assets_total": total_assets,
            "burning_at_end": burning,
            "episode_reward": round(env._episode_reward, 3),
            "resources_remaining": {
                "crews": env.resources.crews,
                "aircraft": env.resources.aircraft,
                "firebreaks": env.resources.firebreaks
            }
        }
    }