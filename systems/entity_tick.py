"""特殊实体生命周期 tick。"""
import random
from llm import generate_new_entity


def tick(sm) -> list[str]:
    notices = []

    # 已有实体老化/退出
    survivors = []
    for e in sm.active_entities:
        alive, reason = e.tick()
        if alive:
            survivors.append(e)
        else:
            for tag in e.legacy_tags:
                if tag not in sm.world.tech_and_culture_tags:
                    sm.world.tech_and_culture_tags.append(tag)
            notice = f"  [{e.name}离世] {reason}"
            if e.legacy_tags:
                notice += f"\n    他留下了：{', '.join(e.legacy_tags)}"
            notices.append(notice)
    sm.active_entities = survivors

    # 低概率涌现新特殊个体
    prob = min(0.04 + sm.world.population / 100_000, 0.25)
    if random.random() < prob:
        data = generate_new_entity(sm.world)
        from core.models import SpecialEntity
        entity = SpecialEntity(
            name=data["name"], traits=data["traits"],
            current_focus=data["current_focus"], risk_level=float(data["risk_level"]),
        )
        sm.active_entities.append(entity)
        p = sm.pool.get_by_name(entity.name)
        if p:
            p.is_notable = True
        notices.append(
            f"\n  [异类出现] {entity.name}（{'、'.join(entity.traits)}）\n"
            f"    正在：{entity.current_focus}  危险度 {entity.risk_level}"
        )

    return notices
