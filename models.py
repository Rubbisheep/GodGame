from dataclasses import dataclass, field
from typing import Optional
import uuid
import random


# ── 变异 ───────────────────────────────────────────────────────────────────

@dataclass
class Mutation:
    target_name: str
    target_type: str          # "entity" / "terrain" / "object" / "event"
    tier: int                 # 1=表层  2=功能  3=本质
    description: str
    turn_appeared: int
    tendency_tags: list[str] = field(default_factory=list)
    spread_count: int = 0
    affected_person: str = ""   # 具体影响的命名个体（可为空）
    person_event: str = ""      # 该个体的个人事件描述
    mutation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def can_spread(self) -> bool:
        limits = {1: 1, 2: 3, 3: 8}
        return self.spread_count < limits[self.tier]

    def spread_prob(self) -> float:
        return {1: 0.05, 2: 0.12, 3: 0.25}[self.tier]


# ── 特殊个体 ───────────────────────────────────────────────────────────────

@dataclass
class SpecialEntity:
    name: str
    traits: list[str]
    current_focus: str
    risk_level: float
    age: int = 0
    max_age: int = field(default_factory=lambda: random.randint(3, 7))
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    legacy_tags: list[str] = field(default_factory=list)
    mutations: list[str] = field(default_factory=list)

    def tick(self) -> tuple[bool, str]:
        self.age += 1
        if self.age >= self.max_age:
            return False, f"{self.name}寿终正寝，走完了他的一生。"
        risk = self.risk_level * (1.5 if self.mutations else 1.0)
        if random.random() < risk * 0.3:
            return False, f"{self.name}因{self.current_focus}而遭遇意外，离世。"
        return True, ""


# ── 世界状态 ───────────────────────────────────────────────────────────────

@dataclass
class WorldState:
    population: int = 30
    faith: int = 20
    current_era: str = "混沌黎明"
    tech_and_culture_tags: list[str] = field(default_factory=list)
    world_year: int = 1
    calendar_name: str = ""
    active_mutations: list[Mutation] = field(default_factory=list)
    tendency_vectors: dict = field(default_factory=dict)

    def can_afford(self, cost: int) -> bool:
        return self.faith >= cost

    def spend_faith(self, cost: int):
        self.faith -= cost

    def apply_population_change(self, delta: int):
        self.population = max(0, self.population + delta)

    def tick_resources(self, faith_bonus: int = 0):
        self.world_year += 1
        self.faith += max(1, self.population // 30) + faith_bonus

    def year_display(self) -> str:
        if self.calendar_name:
            return f"{self.calendar_name}第{self.world_year}年"
        return f"第{self.world_year}年"

    def accumulate_tendency(self, tags: list[str], strength: float = 0.15):
        for tag in tags:
            cur = self.tendency_vectors.get(tag, 0.0)
            self.tendency_vectors[tag] = min(1.0, cur + strength * (1 - cur))

    def dominant_tendencies(self, top_n: int = 3) -> list[str]:
        s = sorted(self.tendency_vectors.items(), key=lambda x: x[1], reverse=True)
        return [t for t, v in s[:top_n] if v > 0.1]

    def summary(self) -> str:
        tags = "、".join(self.tech_and_culture_tags) if self.tech_and_culture_tags else "无"
        tend = "、".join(self.dominant_tendencies()) or "无"
        return (
            f"[{self.year_display()} | {self.current_era}]\n"
            f"  人口: {self.population}  神力: {self.faith}\n"
            f"  已掌握: {tags}\n"
            f"  活跃变异: {len(self.active_mutations)}处  世界倾向: {tend}"
        )

    def to_dict(self) -> dict:
        return {
            "population": self.population,
            "faith": self.faith,
            "current_era": self.current_era,
            "tech_and_culture_tags": self.tech_and_culture_tags,
            "world_year": self.world_year,
            "calendar_name": self.calendar_name,
            "tendency_vectors": self.tendency_vectors,
            "active_mutations": [
                {k: v for k, v in m.__dict__.items()}
                for m in self.active_mutations
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        muts = [Mutation(**m) for m in d.pop("active_mutations", [])]
        ws = cls(**d)
        ws.active_mutations = muts
        return ws


# ── 常量 ───────────────────────────────────────────────────────────────────

MIRACLE_COST = 50
GIFT_COST = 10
