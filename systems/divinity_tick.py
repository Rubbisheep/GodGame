"""神明相关 tick：其他神明干涉、NPC 自主行为。"""
import random
from llm import generate_npc_autonomy, generate_other_god_event


def tick(sm) -> list[str]:
    notices = []
    notices.extend(_tick_npc_autonomy(sm))
    notices.extend(_tick_other_god(sm))
    return notices


def _tick_npc_autonomy(sm) -> list[str]:
    if not sm.pool.living:
        return []
    data = generate_npc_autonomy(sm.world, sm.pool, sm.active_entities)
    notices = []
    for ev in data.get("autonomous_events", []):
        p = sm.pool.get_by_name(ev.get("name", ""))
        if p and p.is_alive():
            desc = ev.get("description", "")
            p.add_event(sm.world.world_year, "autonomous", desc)
            notices.append(f"  [自主] {p.name}：{desc}")
        effect = ev.get("world_effect", "")
        if effect:
            notices.append(f"    → {effect}")
        pop = ev.get("population_change", 0)
        if pop:
            sm.world.apply_population_change(pop)
        sp = ev.get("system_proposal") or {}
        if sp.get("target_module") and sp.get("proposal"):
            sm._upgrade_requests.append((sp["target_module"], sp["proposal"], ev.get("name", "")))
    return notices


def _tick_other_god(sm) -> list[str]:
    sm._other_god_cooldown -= 1
    if sm._other_god_cooldown > 0:
        return []
    if random.random() > 0.03:
        return []
    sm._other_god_cooldown = random.randint(8, 20)
    result = generate_other_god_event(sm.world, sm.pool, sm.active_entities)
    faith_impact = result.get("faith_impact", 0)
    sm.world.faith = max(0, sm.world.faith + faith_impact)
    for p in sm.pool.random_living(2):
        p.add_event(sm.world.world_year, "witness",
                    result.get("narrative_for_npcs", "感到某种无法解释的异样。"))
    return [f"\n  [异常现象] {result.get('description', '')}"]
