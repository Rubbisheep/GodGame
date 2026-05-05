"""人口生命周期 tick：老化/死亡、出生、祈祷生成。"""
import random
from llm import generate_birth


def tick(sm) -> list[str]:
    notices = []
    notices.extend(_tick_aging(sm))
    notices.extend(_tick_births(sm))
    notices.extend(_tick_prayers(sm))
    return notices


def _tick_aging(sm) -> list[str]:
    notices = []
    for person, cause in sm.pool.tick_aging(sm.world.world_year):
        sm.pool.kill(person, sm.world.world_year, cause)
        notices.append(
            f"  [{person.name}离世] {cause}，享年{person.age(sm.world.world_year)}岁"
        )
    return notices


def _tick_births(sm) -> list[str]:
    notices = []
    birth_prob = min(0.15 + len(sm.pool.living) / 120, 0.45)
    if sm.pool.can_add_birth() and random.random() < birth_prob:
        data = generate_birth(sm.world, sm.pool)
        parents = random.sample(sm.pool.living, min(2, len(sm.pool.living)))
        from core.population import Person
        baby = Person(
            name=data["name"], birth_year=sm.world.world_year,
            traits=data.get("traits", ["未知"]),
            background=data.get("background", ""),
            parent_names=[p.name for p in parents],
            inherited_memory=data.get("inherited_memory", ""),
        )
        if data.get("inherited_memory"):
            baby.add_event(sm.world.world_year, "memory", data["inherited_memory"])
        baby.add_event(sm.world.world_year, "birth", data.get("background", "出生。"))
        for parent in parents:
            parent.children_names.append(baby.name)
        sm.pool.add(baby)
        notices.append(f"  [新生] {baby.name}：{data.get('background', '')}")
    return notices


def _tick_prayers(sm) -> list[str]:
    """随机产生新的祈祷者（信仰高者更易祈祷）。"""
    notices = []
    for p in sm.pool.living:
        if p.prayer_pending:
            continue
        pray_prob = p.faith_in_god * 0.12
        if random.random() < pray_prob:
            prayers = [
                "祈求庇护，不知道往哪里走才是对的。",
                "祈求孩子平安出生，或者至少能活下来。",
                "祈求冬天快一点过去，食物快要撑不住了。",
                "不知道该向谁倾诉，就向天空开口了。",
                "把今天的食物留了一半放在石头上，不知道是不是该这样做。",
            ]
            p.prayer_pending = random.choice(prayers)
            notices.append(f"  [祈祷] {p.name}：{p.prayer_pending}")
    return notices
