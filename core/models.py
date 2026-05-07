from dataclasses import dataclass, field


# ── 世界状态 ───────────────────────────────────────────────────────────────

@dataclass
class WorldState:
    population: int = 30
    faith: int = 20
    current_era: str = "混沌黎明"
    tech_and_culture_tags: list[str] = field(default_factory=list)
    world_year: int = 1
    calendar_name: str = ""
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
            f"  已掌握: {tags}  世界倾向: {tend}"
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
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        # 忽略旧存档中已废弃的字段
        d.pop("active_mutations", None)
        return cls(**d)


# ── 常量 ───────────────────────────────────────────────────────────────────

MIRACLE_COST = 50
GIFT_COST = 10
