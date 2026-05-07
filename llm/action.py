"""玩家行动结算：赐予 / 施放。"""
from .client import call, safe_json, USE_MOCK
from .bible import WORLD_BIBLE
from .schemas import ACTION, mock_action


def get_action_result(action_type: str, subject: str,
                      world_state, population_pool) -> dict:
    if USE_MOCK:
        names = [p.name for p in population_pool.living]
        return mock_action(action_type, subject, names)

    people_list = "\n".join(
        f"- {p.name}（{'、'.join(p.traits)}，{p.life_stage(world_state.world_year)}）"
        for p in population_pool.living[:20]
    ) or "无"

    avg_faith = sum(p.faith_in_god for p in population_pool.living) / max(1, len(population_pool.living))
    if avg_faith < 0.05:
        contact_ctx = (
            "【关键叙事背景】这是神明首次（或极早期）与此部落接触。"
            "人类完全不知道神明的存在。这一刻对他们来说是彻底的未知降临："
            "震惊、恐惧、困惑、对未知的原始敬畏。"
            "描述中不要用「神明」这个词描述人类的感受——他们只会说「那个」「某种东西」「来自上面的」。"
        )
    else:
        contact_ctx = f"部落对神明的平均信仰度约为 {avg_faith:.0%}，此前已有过接触。"

    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{ACTION}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"命名居民（部分）：\n{people_list}\n\n"
        f"{contact_ctx}\n\n"
        f"神明执行【{action_type}】：{subject}\n返回 JSON。"
    )
    fallback = {
        "narrative_text": f"神明降下了{subject}，世界沉默片刻。",
        "population_change": 0, "new_tech_tags": [], "tendency_hints": [],
        "is_era_breakthrough": False, "new_era_name": "", "calendar_name": "",
        "individual_events": [],
    }
    return safe_json(call(system, user, max_tokens=1200), fallback)
