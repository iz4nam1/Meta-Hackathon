"""
Wildfire Containment Coordinator — Core Environment
====================================================
OpenEnv-compliant simulation of wildfire suppression.
A grid-based environment where an AI agent deploys resources
to contain spreading wildfires under dynamic wind conditions.
"""

import random
import math
import copy
from enum import IntEnum
from typing import Optional
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────
# CELL TYPES
# ─────────────────────────────────────────────
class Cell(IntEnum):
    EMPTY    = 0   # Bare ground / rock — won't burn
    VEG      = 1   # Vegetation — can burn
    BURNING  = 2   # Actively on fire
    BURNED   = 3   # Already burned out
    FIREBREAK= 4   # Crew-built firebreak — blocks spread
    WATER    = 5   # Water body — blocks spread
    ASSET    = 6   # Protected asset (structure/town)
    ASSET_BURNED = 7  # Asset lost to fire

# ─────────────────────────────────────────────
# PYDANTIC MODELS (OpenEnv Spec)
# ─────────────────────────────────────────────
class WindState(BaseModel):
    direction: float = Field(..., description="Degrees 0-360, 0=North")
    speed: float     = Field(..., description="Speed multiplier 0.5–3.0")

class Resources(BaseModel):
    crews: int     = Field(..., description="Available crew teams")
    aircraft: int  = Field(..., description="Available aircraft sorties")
    firebreaks: int= Field(..., description="Remaining firebreak segments")

class Observation(BaseModel):
    grid: list[list[int]]       = Field(..., description="2D grid of Cell enum values")
    wind: WindState
    resources: Resources
    time_step: int
    total_steps: int
    containment_pct: float      = Field(..., description="0.0–1.0 fraction of fire contained")
    assets_lost: int
    assets_total: int
    burning_cells: int
    veg_remaining: int
    done: bool

class Action(BaseModel):
    action_type: str = Field(..., description="deploy_crew | airdrop | build_break | evacuate_zone | hold")
    x: Optional[int] = Field(None, description="Grid column (0-indexed)")
    y: Optional[int] = Field(None, description="Grid row (0-indexed)")
    zone: Optional[str] = Field(None, description="Zone ID for evacuate_zone")

class Reward(BaseModel):
    total: float
    containment_bonus: float
    burn_penalty: float
    asset_penalty: float
    efficiency_bonus: float
    info: str

# ─────────────────────────────────────────────
# WILDFIRE ENVIRONMENT
# ─────────────────────────────────────────────
class WildfireEnv:
    VALID_ACTIONS = ["deploy_crew", "airdrop", "build_break", "evacuate_zone", "hold"]

    def __init__(self, task: dict):
        self.task = task
        self.grid_size   = task.get("grid_size", 15)
        self.max_steps   = task.get("max_steps", 50)
        self.seed        = task.get("seed", 42)
        self._rng        = random.Random(self.seed)
        self._step_count = 0
        self._done       = False
        self._prev_burning = 0
        self._cells_burned_this_ep = 0
        self.grid        = []
        self.wind        = WindState(direction=0.0, speed=1.0)
        self.resources   = Resources(
            crews=task.get("crews", 3),
            aircraft=task.get("aircraft", 2),
            firebreaks=task.get("firebreaks", 20)
        )
        self._assets_total  = 0
        self._assets_lost   = 0
        self._initial_veg   = 0
        self._episode_reward= 0.0

    # ── reset ──────────────────────────────────
    def reset(self) -> Observation:
        self._rng        = random.Random(self.seed)
        self._step_count = 0
        self._done       = False
        self._cells_burned_this_ep = 0
        self._assets_lost = 0
        self._episode_reward = 0.0
        self.resources   = Resources(
            crews=self.task.get("crews", 3),
            aircraft=self.task.get("aircraft", 2),
            firebreaks=self.task.get("firebreaks", 20)
        )
        self._build_grid()
        self._init_wind()
        self._prev_burning = self._count(Cell.BURNING)
        self._initial_veg  = self._count(Cell.VEG) + self._count(Cell.BURNING)
        self._assets_total = self._count(Cell.ASSET) + self._count(Cell.ASSET_BURNED)
        return self._observe()

    def _build_grid(self):
        g = self.grid_size
        layout = self.task.get("layout", "random")
        self.grid = [[Cell.VEG]*g for _ in range(g)]

        # Water bodies
        for (r,c) in self.task.get("water_cells", []):
            if 0<=r<g and 0<=c<g:
                self.grid[r][c] = Cell.WATER

        # Empty / rock
        for (r,c) in self.task.get("empty_cells", []):
            if 0<=r<g and 0<=c<g:
                self.grid[r][c] = Cell.EMPTY

        # Protected assets
        for (r,c) in self.task.get("asset_cells", []):
            if 0<=r<g and 0<=c<g:
                self.grid[r][c] = Cell.ASSET

        # Ignition points
        for (r,c) in self.task.get("ignition_points", [(g//2, g//2)]):
            if 0<=r<g and 0<=c<g:
                self.grid[r][c] = Cell.BURNING

        # Random noise for natural look
        if layout == "random":
            for r in range(g):
                for c in range(g):
                    if self.grid[r][c] == Cell.VEG and self._rng.random() < 0.08:
                        self.grid[r][c] = Cell.EMPTY

    def _init_wind(self):
        self.wind = WindState(
            direction=self.task.get("wind_direction", self._rng.uniform(0,360)),
            speed=self.task.get("wind_speed", self._rng.uniform(0.8, 1.5))
        )

    # ── step ───────────────────────────────────
    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        if self._done:
            obs = self._observe()
            return obs, Reward(total=0,containment_bonus=0,burn_penalty=0,
                               asset_penalty=0,efficiency_bonus=0,info="Episode done"), True, {}

        reward_parts = {"containment_bonus":0.0,"burn_penalty":0.0,
                        "asset_penalty":0.0,"efficiency_bonus":0.0}
        info = {}

        # 1. Apply agent action
        action_result = self._apply_action(action)
        info["action_result"] = action_result
        if action_result.get("efficient"):
            reward_parts["efficiency_bonus"] += 2.0

        # 2. Spread fire
        new_burns, asset_hits = self._spread_fire()
        reward_parts["burn_penalty"]  -= new_burns * 2.0
        reward_parts["asset_penalty"] -= asset_hits * 15.0
        self._assets_lost += asset_hits
        self._cells_burned_this_ep += new_burns

        # 3. Shift wind (stochastic, harder tasks)
        if self.task.get("dynamic_wind", False):
            self._shift_wind()

        # 4. Containment reward
        burning_now = self._count(Cell.BURNING)
        if burning_now < self._prev_burning:
            reward_parts["containment_bonus"] += (self._prev_burning - burning_now) * 5.0
        self._prev_burning = burning_now

        # 5. Check done
        self._step_count += 1
        if burning_now == 0 or self._step_count >= self.max_steps:
            self._done = True
            if burning_now == 0:
                reward_parts["containment_bonus"] += 100.0
                info["outcome"] = "contained"
            else:
                info["outcome"] = "timeout"

        total = sum(reward_parts.values())
        self._episode_reward += total
        reward = Reward(total=round(total,3), info=info.get("outcome","ongoing"), **{k:round(v,3) for k,v in reward_parts.items()})
        obs    = self._observe()
        return obs, reward, self._done, info

    def _apply_action(self, action: Action) -> dict:
        atype = action.action_type
        x, y  = action.x, action.y

        if atype == "hold":
            return {"ok": True, "msg": "held", "efficient": False}

        if atype in ("deploy_crew", "build_break"):
            if self.resources.crews <= 0:
                return {"ok":False,"msg":"no crews available","efficient":False}
            if x is None or y is None or not self._in_bounds(y,x):
                return {"ok":False,"msg":"invalid coords","efficient":False}
            cell = self.grid[y][x]
            efficient = False
            if atype == "deploy_crew":
                if cell == Cell.BURNING:
                    self.grid[y][x] = Cell.BURNED
                    efficient = True
                elif cell == Cell.VEG:
                    self.grid[y][x] = Cell.FIREBREAK
                    efficient = True
            elif atype == "build_break":
                if self.resources.firebreaks <= 0:
                    return {"ok":False,"msg":"no firebreak segments","efficient":False}
                if cell == Cell.VEG:
                    self.grid[y][x] = Cell.FIREBREAK
                    self.resources.firebreaks -= 1
                    efficient = True
            self.resources.crews -= 1
            return {"ok":True,"msg":f"{atype} at ({x},{y})","efficient":efficient}

        if atype == "airdrop":
            if self.resources.aircraft <= 0:
                return {"ok":False,"msg":"no aircraft available","efficient":False}
            if x is None or y is None or not self._in_bounds(y,x):
                return {"ok":False,"msg":"invalid coords","efficient":False}
            efficient = False
            # Douse 3x3 area around target
            for dr in [-1,0,1]:
                for dc in [-1,0,1]:
                    nr,nc = y+dr, x+dc
                    if self._in_bounds(nr,nc):
                        if self.grid[nr][nc] == Cell.BURNING:
                            self.grid[nr][nc] = Cell.BURNED
                            efficient = True
                        elif self.grid[nr][nc] == Cell.VEG:
                            self.grid[nr][nc] = Cell.FIREBREAK
            self.resources.aircraft -= 1
            return {"ok":True,"msg":f"airdrop at ({x},{y})","efficient":efficient}

        if atype == "evacuate_zone":
            # Protect assets: mark surrounding cells as firebreak
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self.grid[r][c] == Cell.ASSET:
                        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr,nc=r+dr,c+dc
                            if self._in_bounds(nr,nc) and self.grid[nr][nc]==Cell.VEG:
                                self.grid[nr][nc]=Cell.FIREBREAK
            return {"ok":True,"msg":"zone evacuated","efficient":True}

        return {"ok":False,"msg":"unknown action","efficient":False}

    def _spread_fire(self) -> tuple[int,int]:
        g = self.grid_size
        new_fires = []
        asset_hits = 0
        wd_rad = math.radians(self.wind.direction)
        wind_vec = (math.sin(wd_rad), -math.cos(wd_rad))  # (dc, dr) components

        for r in range(g):
            for c in range(g):
                if self.grid[r][c] != Cell.BURNING:
                    continue
                for dr,dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                    nr,nc = r+dr, c+dc
                    if not self._in_bounds(nr,nc):
                        continue
                    target = self.grid[nr][nc]
                    if target not in (Cell.VEG, Cell.ASSET):
                        continue
                    # Wind-adjusted spread probability
                    dot = dr*wind_vec[1] + dc*wind_vec[0]
                    prob = 0.3 + 0.15*dot*self.wind.speed
                    prob = max(0.05, min(0.95, prob))
                    if self._rng.random() < prob:
                        new_fires.append((nr,nc, target))

        for (nr,nc,orig) in new_fires:
            if self.grid[nr][nc] in (Cell.VEG, Cell.ASSET):
                if orig == Cell.ASSET:
                    self.grid[nr][nc] = Cell.ASSET_BURNED
                    asset_hits += 1
                else:
                    self.grid[nr][nc] = Cell.BURNING

        # Burn out old fire cells (stochastic)
        for r in range(g):
            for c in range(g):
                if self.grid[r][c] == Cell.BURNING and self._rng.random() < 0.15:
                    self.grid[r][c] = Cell.BURNED

        return len(new_fires), asset_hits

    def _shift_wind(self):
        shift = self._rng.gauss(0, 15)
        self.wind.direction = (self.wind.direction + shift) % 360
        speed_shift = self._rng.gauss(0, 0.2)
        self.wind.speed = max(0.5, min(3.0, self.wind.speed + speed_shift))

    # ── state ──────────────────────────────────
    def state(self) -> dict:
        obs = self._observe()
        return {
            "observation": obs.model_dump(),
            "step": self._step_count,
            "episode_reward": round(self._episode_reward, 3),
            "done": self._done
        }

    # ── helpers ────────────────────────────────
    def _observe(self) -> Observation:
        burning  = self._count(Cell.BURNING)
        total_veg= self._initial_veg if self._initial_veg > 0 else 1
        contained= 1.0 - (burning / total_veg)
        return Observation(
            grid=[[int(c) for c in row] for row in self.grid],
            wind=self.wind,
            resources=self.resources,
            time_step=self._step_count,
            total_steps=self.max_steps,
            containment_pct=round(max(0.0, min(1.0, contained)), 4),
            assets_lost=self._assets_lost,
            assets_total=self._assets_total,
            burning_cells=burning,
            veg_remaining=self._count(Cell.VEG),
            done=self._done
        )

    def _count(self, cell_type: Cell) -> int:
        return sum(1 for row in self.grid for c in row if c == cell_type)

    def _in_bounds(self, r:int, c:int) -> bool:
        return 0 <= r < self.grid_size and 0 <= c < self.grid_size

    def valid_actions(self) -> list[str]:
        return self.VALID_ACTIONS