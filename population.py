"""
人口系统。每个被追踪的个体有完整的生命时间线。
支持血脉追踪：父母→孩子的特质/记忆碎片继承。
"""
from dataclasses import dataclass, field
from typing import Optional
import uuid
import random


@dataclass
class LifeEvent:
    year: int
    event_type: str   # birth/witness/mutation/encounter/autonomous/death/growth/prayer/miracle
    description: str

    def display(self) -> str:
        labels = {
            "birth": "出生", "witness": "见证", "mutation": "变异",
            "encounter": "相遇", "autonomous": "自发", "death": "离世",
            "growth": "成长", "prayer": "祈祷", "miracle": "神迹",
            "divine": "神明感知", "memory": "记忆碎片",
        }
        return f"  [{labels.get(self.event_type, self.event_type)}] {self.description}"


@dataclass
class Person:
    name: str
    birth_year: int
    traits: list[str]
    background: str
    max_age: int = field(default_factory=lambda: random.randint(35, 75))
    life_events: list[LifeEvent] = field(default_factory=list)
    death_year: Optional[int] = None
    death_cause: Optional[str] = None
    is_notable: bool = False
    person_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    relationships: list[str] = field(default_factory=list)

    # 血脉
    parent_names: list[str] = field(default_factory=list)   # 父/母名字
    children_names: list[str] = field(default_factory=list)
    inherited_memory: str = ""   # 从父母那继承的记忆碎片（一句话）

    # 信仰状态
    faith_in_god: float = 0.0    # 0=不信  1=狂热信徒
    prayer_pending: str = ""     # 如果非空，说明此人正在向神明祈祷

    def age(self, current_year: int) -> int:
        if self.death_year:
            return self.death_year - self.birth_year
        return max(0, current_year - self.birth_year)

    def is_alive(self) -> bool:
        return self.death_year is None

    def add_event(self, year: int, event_type: str, description: str):
        self.life_events.append(LifeEvent(year, event_type, description))

    def life_stage(self, current_year: int) -> str:
        a = self.age(current_year)
        if a < 5:   return "幼年"
        if a < 15:  return "少年"
        if a < 30:  return "青年"
        if a < 55:  return "中年"
        return "暮年"

    def display_timeline(self, current_year: int) -> str:
        status = "已故" if self.death_year else f"{self.life_stage(current_year)}·{self.age(current_year)}岁"
        faith_bar = "█" * int(self.faith_in_god * 5) + "░" * (5 - int(self.faith_in_god * 5))
        header = (
            f"【{self.name}】  {status}\n"
            f"  性格：{'、'.join(self.traits)}\n"
            f"  出身：{self.background}\n"
            f"  对神明的信仰：[{faith_bar}]"
        )
        if self.parent_names:
            header += f"\n  父母：{', '.join(self.parent_names)}"
        if self.children_names:
            header += f"\n  子女：{', '.join(self.children_names)}"
        if self.inherited_memory:
            header += f"\n  继承的记忆：{self.inherited_memory}"
        if not self.life_events:
            return header + "\n  （暂无记录）"

        by_year: dict[int, list[LifeEvent]] = {}
        for ev in self.life_events:
            by_year.setdefault(ev.year, []).append(ev)

        lines = [header]
        for yr in sorted(by_year):
            lines.append(f"\n  ── 第{yr}年 ──")
            for ev in by_year[yr]:
                lines.append(ev.display())
        return "\n".join(lines)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["life_events"] = [e.__dict__ for e in self.life_events]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Person":
        events_raw = d.pop("life_events", [])
        p = cls(**d)
        p.life_events = [LifeEvent(**e) for e in events_raw]
        return p


class PopulationPool:
    MAX_POOL = 80

    def __init__(self):
        self.living: list[Person] = []
        self.archived: list[Person] = []

    def all_named(self) -> list[Person]:
        return self.living + self.archived

    def get_by_name(self, name: str) -> Optional[Person]:
        for p in self.living + self.archived:
            if p.name == name or name in p.name:
                return p
        return None

    def add(self, person: Person):
        self.living.append(person)

    def kill(self, person: Person, year: int, cause: str):
        person.death_year = year
        person.death_cause = cause
        person.add_event(year, "death", cause)
        if person in self.living:
            self.living.remove(person)
        self.archived.append(person)

    def can_add_birth(self) -> bool:
        return len(self.living) < self.MAX_POOL

    def random_living(self, n: int = 3) -> list[Person]:
        return random.sample(self.living, min(n, len(self.living)))

    def pending_prayers(self) -> list[Person]:
        return [p for p in self.living if p.prayer_pending]

    def tick_aging(self, current_year: int) -> list[tuple["Person", str]]:
        deceased = []
        for p in list(self.living):
            if p.age(current_year) >= p.max_age:
                deceased.append((p, "寿终正寝"))
            elif random.random() < 0.004:
                deceased.append((p, "因故意外离世"))
        return deceased

    def summary_list(self, current_year: int) -> str:
        if not self.living:
            return "  （无）"
        lines = []
        for p in sorted(self.living, key=lambda x: x.birth_year):
            stage = p.life_stage(current_year)
            age = p.age(current_year)
            notable = " ★" if p.is_notable else ""
            prayer = " 🙏" if p.prayer_pending else ""
            bg = p.background[:22] + "…" if len(p.background) > 22 else p.background
            lines.append(f"  · {p.name}  {stage}·{age}岁{notable}{prayer}  {bg}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "living": [p.to_dict() for p in self.living],
            "archived": [p.to_dict() for p in self.archived],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PopulationPool":
        pool = cls()
        pool.living = [Person.from_dict(p) for p in d.get("living", [])]
        pool.archived = [Person.from_dict(p) for p in d.get("archived", [])]
        return pool
