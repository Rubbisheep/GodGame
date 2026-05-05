"""变异滚动与扩散 tick（整合原 mutation_system.py）。"""
import random
from llm import generate_mutation_description, generate_spread_description
from core.models import Mutation

_BASE_PROB = {1: 0.18, 2: 0.06, 3: 0.012}
_TARGET_TYPES = ["entity", "terrain", "object", "event"]
_TARGET_WEIGHTS = [0.35, 0.30, 0.20, 0.15]
_TERRAIN_NAMES = ["北方的山岭", "部落边缘的密林", "河流入海口", "中央的石台", "枯树林", "西边的沼泽"]
_OBJECT_NAMES  = ["最古老的石斧", "神殿的供台", "长者的权杖", "祭火的灰烬", "部落的水井"]
_EVENT_NAMES   = ["本季的丰收仪式", "昨夜的暴风雨", "每日的祭祀", "孩子们的游戏", "集会的篝火"]


def tick(sm) -> list[str]:
    notices = []
    people_names = [p.name for p in sm.pool.living]

    for m in _roll(sm.world, sm.active_entities, people_names):
        sm.world.active_mutations.append(m)
        tier_label = {1: "◈ 表层变异", 2: "◉ 功能变异", 3: "⬡ 本质变异"}[m.tier]
        notices.append(f"\n  [{tier_label}] {m.target_name}\n    {m.description}")
        if m.affected_person:
            p = sm.pool.get_by_name(m.affected_person)
            if p and p.is_alive():
                p.add_event(sm.world.world_year, "mutation", m.person_event or m.description)
        if m.tier == 3:
            sm._maybe_generate_myth(m.description)

    for s in _spread(sm.world, sm.active_entities, people_names):
        notices.append(f"\n  [变异扩散] {s['description']}")
        if s.get("affected_person"):
            p = sm.pool.get_by_name(s["affected_person"])
            if p and p.is_alive():
                p.add_event(sm.world.world_year, "mutation",
                            s.get("person_event", s["description"]))

    # 清理过期变异（本质变异永久保留）
    sm.world.active_mutations = [
        m for m in sm.world.active_mutations
        if m.tier == 3 or (sm.world.world_year - m.turn_appeared) < 15
    ]
    return notices


def _mutation_prob(tier: int, tendency_strength: float) -> float:
    return min(_BASE_PROB[tier] * (1 + tendency_strength * 2), 0.5)


def _pick_target(world, entities: list, tier: int) -> tuple[str, str]:
    target_type = random.choices(_TARGET_TYPES, weights=_TARGET_WEIGHTS)[0]
    if target_type == "entity" and entities:
        return "entity", random.choice(entities).name
    if target_type == "entity":
        target_type = "terrain"
    names_map = {"terrain": _TERRAIN_NAMES, "object": _OBJECT_NAMES, "event": _EVENT_NAMES}
    return target_type, random.choice(names_map.get(target_type, ["未知之物"]))


def _roll(world, entities: list, people_names: list) -> list:
    new_mutations = []
    top_strength = max(world.tendency_vectors.values(), default=0.0)
    for tier in [1, 2, 3]:
        if random.random() > _mutation_prob(tier, top_strength):
            continue
        target_type, target_name = _pick_target(world, entities, tier)
        result = generate_mutation_description(
            tier=tier, target_type=target_type, target_name=target_name,
            tendencies=world.dominant_tendencies(), world_summary=world.summary(),
            era=world.current_era, people_names=people_names,
        )
        if not isinstance(result, dict):
            result = {"description": str(result), "affected_person": "", "person_event": ""}
        m = Mutation(
            target_name=target_name, target_type=target_type, tier=tier,
            description=result["description"], turn_appeared=world.world_year,
            tendency_tags=world.dominant_tendencies(),
            affected_person=result.get("affected_person", ""),
            person_event=result.get("person_event", ""),
        )
        if target_type == "entity" and tier >= 2:
            for e in entities:
                if e.name == target_name:
                    e.mutations.append(m.description)
                    break
        new_mutations.append(m)
    return new_mutations


def _spread(world, entities: list, people_names: list) -> list[dict]:
    spread_notices = []
    for mutation in list(world.active_mutations):
        if not mutation.can_spread():
            continue
        if random.random() > mutation.spread_prob():
            continue
        _, spread_target = _pick_target(world, entities, mutation.tier)
        result = generate_spread_description(
            original_mutation=mutation.description, spread_target=spread_target,
            tier=mutation.tier, era=world.current_era, people_names=people_names,
        )
        mutation.spread_count += 1
        if not isinstance(result, dict):
            result = {"description": str(result), "affected_person": "", "person_event": ""}
        spread_notices.append(result)
    return spread_notices
