"""NPC 自主行为 tick。每回合让一些居民自发做点什么。"""
from llm import generate_npc_autonomy


def tick(sm) -> list[str]:
    if not sm.pool.living:
        return []
    data = generate_npc_autonomy(sm.world, sm.pool)
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
            sm._upgrade_requests.append(
                (sp["target_module"], sp["proposal"], ev.get("name", ""))
            )
    return notices
