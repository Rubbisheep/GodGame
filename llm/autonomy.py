"""NPC 自主行为生成。"""
from .client import call, safe_json, USE_MOCK
from .bible import WORLD_BIBLE
from .schemas import NPC_AUTONOMY, mock_npc_autonomy


def generate_npc_autonomy(world_state, population_pool) -> dict:
    if USE_MOCK:
        names = [p.name for p in population_pool.living]
        return mock_npc_autonomy(names)

    recent_events = []
    for p in population_pool.random_living(8):
        if p.life_events:
            last = p.life_events[-1]
            recent_events.append(
                f"{p.name}（{p.life_stage(world_state.world_year)}）：近况——{last.description}"
            )

    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{NPC_AUTONOMY}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"部分居民近况：\n" + "\n".join(recent_events) + "\n\n"
        "这些居民本年度自发采取了什么行动？选择2-4人，生成他们的自主行为。"
        "行为应符合其性格，可以是微小的日常，也可以是影响他人的重要决定。返回 JSON。"
    )
    return safe_json(call(system, user, max_tokens=1200), {"autonomous_events": []})
