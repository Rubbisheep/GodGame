"""神明相关生成：祈祷回应、神明凝视、其他神明干涉、神话。"""
import json
from .client import call, USE_MOCK
from .bible import WORLD_BIBLE
from .schemas import (PRAYER_RESPONSE, DIVINE_GAZE, OTHER_GOD, WORLD_MYTH,
                       mock_prayer_response, mock_divine_gaze, mock_other_god)


def generate_prayer_response(person, prayer_text: str,
                              world_state, god_response_type: str) -> dict:
    person_name = person.name if hasattr(person, "name") else str(person)
    if USE_MOCK:
        return mock_prayer_response(person_name, god_response_type)

    flavor = {
        "answer":  "神明有所回应，但方式神秘，不会直接满足诉求",
        "ignore":  "神明完全忽视了这个祈祷，没有任何迹象",
        "punish":  "神明被惹怒或认为此人不配，予以惩戒",
        "bless":   "神明给予了真实的祝福，带来具体的好处",
    }.get(god_response_type, "神明没有回应")
    traits = "、".join(person.traits) if hasattr(person, "traits") else "未知"

    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{PRAYER_RESPONSE}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"祈祷者：{person_name}（{traits}）\n"
        f"祈祷内容：{prayer_text}\n"
        f"神明的回应方式：{flavor}\n\n"
        "生成神明的回应。narrative 要具体感官，通过自然现象或奇异事件体现，不要直接说神明出现了。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=300))
    except Exception:
        return mock_prayer_response(person_name, god_response_type)


def generate_divine_gaze(target_name: str, target_type: str,
                          world_state, pool) -> dict:
    if USE_MOCK:
        return mock_divine_gaze(target_name, target_type)

    target_info = ""
    if target_type == "person":
        for p in pool.living:
            if p.name == target_name:
                events_summary = "；".join(e.description for e in p.life_events[-3:]) or "无记录"
                target_info = (
                    f"性格：{'、'.join(p.traits)}\n背景：{p.background}\n"
                    f"近期经历：{events_summary}"
                )
                break

    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{DIVINE_GAZE}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"神明凝视的目标：{target_name}（类型：{target_type}）\n"
        f"{target_info}\n\n"
        "deep_vision 要充满感官细节，像是看穿了表象进入更深的结构。"
        "hidden_truth 必须是具体的、真实的确定事实，不是模糊预言。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=400))
    except Exception:
        return mock_divine_gaze(target_name, target_type)


def generate_other_god_event(world_state, pool, active_entities) -> dict:
    if USE_MOCK:
        return mock_other_god()

    npc_names = [p.name for p in pool.random_living(5)]
    entity_names = [e.name for e in active_entities[:3]]
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{OTHER_GOD}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"当前可引用的人物：{', '.join(npc_names + entity_names)}\n\n"
        "生成另一位神明的干涉事件。事件应当神秘难以辨认，像世界本身在发生奇异变化，而非外部入侵。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=350))
    except Exception:
        return mock_other_god()


def generate_life_snapshot(world_state, pool) -> str:
    """生成当下切片：3-5个具体的人正在做什么、想什么。流动叙事，不限于大事。"""
    import random
    sample = random.sample(pool.living, min(5, len(pool.living)))
    people_desc = "\n".join(
        f"- {p.name}（{p.life_stage(world_state.world_year)}·{p.age(world_state.world_year)}岁"
        f"  性格：{'、'.join(p.traits[:2])}  信仰：{p.faith_in_god:.0%}"
        + (f"  祈祷中：{p.prayer_pending}" if p.prayer_pending else "")
        + "）"
        for p in sample
    )
    system = (
        WORLD_BIBLE + "\n\n"
        "你是这个世界的隐形观察者。用第三人称、现在时、感官性的文字，写下你此刻看见的几个普通人正在做的事情。\n"
        "要求：\n"
        "· 写3-5个人，每人1-3句话，连成一段流动的叙事\n"
        "· 细节要具体：动作、表情、手里的东西、周围的声音气味\n"
        "· 可以写鸡毛蒜皮：捉虫、发呆、拌嘴、偷懒、胡思乱想\n"
        "· 可以偶尔透露一句内心独白，用斜体感觉（直接写，不加任何标记）\n"
        "· 不要写重大事件，不要升华，不要总结\n"
        "· 只输出叙事文字，不加任何标题或前缀"
    )
    user = (
        f"当前：{world_state.year_display()}  {world_state.current_era}\n\n"
        f"此刻你看见的人：\n{people_desc}\n\n"
        "写下他们此刻的样子。"
    )
    try:
        return call(system, user, max_tokens=500)
    except Exception:
        return "（世界在继续，但神明的目光此刻难以聚焦。）"


def generate_world_myth(event_text: str, world_state) -> dict:
    if USE_MOCK:
        return {"myth_name": "无名之事", "myth_text": "据说在那个年代，有些事情发生了，没有人知道为什么。",
                "cultural_effect": "人们开始在夜晚对着天空低语。"}
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{WORLD_MYTH}"
    user = (
        f"世界年份：{world_state.year_display()}  时代：{world_state.current_era}\n\n"
        f"触发神话的事件：{event_text}\n\n"
        "将这个事件转化为一个在人口中口耳相传的神话。"
        "myth_text 用古朴的叙事口吻，仿佛一位老人在讲述，不提「神明」或任何超自然词汇，而是通过现象描述。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=400))
    except Exception:
        return {}
