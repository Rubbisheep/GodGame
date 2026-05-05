import random
from models import WorldState, SpecialEntity, Mutation
from llm_interface import generate_mutation_description, generate_spread_description

_BASE_PROB = {1: 0.18, 2: 0.06, 3: 0.012}
_TARGET_TYPES = ["entity", "terrain", "object", "event"]
_TARGET_WEIGHTS = [0.35, 0.30, 0.20, 0.15]


def _mutation_prob(tier: int, tendency_strength: float) -> float:
    return min(_BASE_PROB[tier] * (1 + tendency_strength * 2), 0.5)


def _pick_target(world: WorldState, entities: list, tier: int) -> tuple[str, str]:
    target_type = random.choices(_TARGET_TYPES, weights=_TARGET_WEIGHTS)[0]
    if target_type == "entity" and entities:
        return "entity", random.choice(entities).name
    elif target_type == "entity":
        target_type = "terrain"
    names = {
        "terrain": ["北方的山岭", "部落边缘的密林", "河流入海口", "中央的石台", "枯树林", "西边的沼泽"],
        "object":  ["最古老的石斧", "神殿的供台", "长者的权杖", "祭火的灰烬", "部落的水井"],
        "event":   ["本季的丰收仪式", "昨夜的暴风雨", "每日的祭祀", "孩子们的游戏", "集会的篝火"],
    }
    return target_type, random.choice(names.get(target_type, ["未知之物"]))


def roll_mutations(world: WorldState, entities: list, people_names: list[str]) -> list:
    """返回本年新产生的 Mutation 列表（对象已附加 affected_person 和 person_event 字段）。"""
    new_mutations = []
    top_strength = max(world.tendency_vectors.values(), default=0.0)

    for tier in [1, 2, 3]:
        if random.random() > _mutation_prob(tier, top_strength):
            continue

        target_type, target_name = _pick_target(world, entities, tier)
        tendencies = world.dominant_tendencies()

        result = generate_mutation_description(
            tier=tier,
            target_type=target_type,
            target_name=target_name,
            tendencies=tendencies,
            world_summary=world.summary(),
            era=world.current_era,
            people_names=people_names,
        )

        mutation = Mutation(
            target_name=target_name,
            target_type=target_type,
            tier=tier,
            description=result["description"] if isinstance(result, dict) else result,
            turn_appeared=world.world_year,
            tendency_tags=tendencies,
        )
        # 附加个人信息（如果 LLM 返回了的话）
        mutation.affected_person = result.get("affected_person", "") if isinstance(result, dict) else ""
        mutation.person_event = result.get("person_event", "") if isinstance(result, dict) else ""
        new_mutations.append(mutation)

        if target_type == "entity" and tier >= 2:
            for e in entities:
                if e.name == target_name:
                    e.mutations.append(mutation.description)
                    break

    return new_mutations


def spread_mutations(world: WorldState, entities: list, people_names: list[str]) -> list[dict]:
    """返回扩散描述 dict 列表，每个含 description / affected_person / person_event。"""
    spread_notices = []
    for mutation in list(world.active_mutations):
        if not mutation.can_spread():
            continue
        if random.random() > mutation.spread_prob():
            continue

        _, spread_target = _pick_target(world, entities, mutation.tier)
        result = generate_spread_description(
            original_mutation=mutation.description,
            spread_target=spread_target,
            tier=mutation.tier,
            era=world.current_era,
            people_names=people_names,
        )
        mutation.spread_count += 1
        spread_notices.append(result if isinstance(result, dict) else {"description": result, "affected_person": "", "person_event": ""})

    return spread_notices
