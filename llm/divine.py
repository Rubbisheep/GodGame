"""神明相关生成：祈祷回应、神明凝视、传话、自询、生活切片。"""
import json
from .client import call, USE_MOCK
from .bible import WORLD_BIBLE
from .schemas import (PRAYER_RESPONSE, DIVINE_GAZE,
                       mock_prayer_response, mock_divine_gaze)


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


def generate_life_snapshot(world_state, pool, recent_events: list | None = None) -> str:
    """生成当下切片：呈现数个具体的人此刻在做什么，有大事必须体现。"""
    import random
    sample = random.sample(pool.living, min(5, len(pool.living)))
    people_desc = "\n".join(
        f"- {p.name}（{p.life_stage(world_state.world_year)}·{p.age(world_state.world_year)}岁"
        f"  性格：{'、'.join(p.traits[:2])}  信仰：{p.faith_in_god:.0%}"
        + (f"  祈祷中：{p.prayer_pending}" if p.prayer_pending else "")
        + "）"
        for p in sample
    )
    events_block = ""
    if recent_events:
        trimmed = [e.strip() for e in recent_events[-10:] if e.strip()]
        if trimmed:
            events_block = "\n\n近期发生的大事（必须在叙事中有所体现，不能忽略）：\n" + "\n".join(trimmed)

    system = (
        WORLD_BIBLE + "\n\n"
        "你是这个世界的隐形观察者。用第三人称、现在时、感官性的文字，写下你此刻看见的几个人正在做的事情。\n"
        "要求：\n"
        "· 写3-5个人，每人1-3句话，连成一段流动的叙事\n"
        "· 细节要具体：动作、表情、手里的东西、周围的声音气味\n"
        "· 大小事均可：日常琐事也好，重大变故后的余震也好，跟着世界的当下感觉走\n"
        "· 如果近期有大事，叙事中必须体现它对人的影响——行为、情绪、对话的片段\n"
        "· 可以偶尔透露一句内心独白（直接写，不加标记）\n"
        "· 不要总结，不要点评，只呈现正在发生的\n"
        "· 只输出叙事文字，不加任何标题或前缀"
    )
    user = (
        f"当前：{world_state.year_display()}  {world_state.current_era}"
        f"{events_block}\n\n"
        f"此刻你看见的人：\n{people_desc}\n\n"
        "写下他们此刻的样子。"
    )
    try:
        return call(system, user, max_tokens=600)
    except Exception:
        return "（世界在继续，但神明的目光此刻难以聚焦。）"


def generate_npc_dialogue(person, god_message: str, world_state, pool) -> dict:
    """神明向某人传话，返回该人的回应与行为变化。"""
    reception = (
        "这个人是先知或使徒，对神明极度敏感，能清晰感知并回应神明的意志。"
        if person.is_notable else
        "这个人信仰较强，神明的话语像是某种内心涌现的直觉或梦境碎片。"
        if person.faith_in_god > 0.4 else
        "这个人信仰尚浅，神明的传话对他来说可能只是一闪而过的念头，甚至毫无感知。"
    )
    person_info = (
        f"姓名：{person.name}  {person.life_stage(world_state.world_year)}·{person.age(world_state.world_year)}岁\n"
        f"性格：{'、'.join(person.traits)}\n"
        f"出身：{person.background}\n"
        f"对神明的信仰：{person.faith_in_god:.0%}  是否被命运选中的异人：{person.is_notable}\n"
        + (f"当前祈祷：{person.prayer_pending}\n" if person.prayer_pending else "")
        + (f"近期经历：{person.life_events[-1].description if person.life_events else '无'}\n")
    )
    schema = '''{
  "heard": true/false,
  "speech": "此人说出或在心中回应的话（原声，不加引号说明）",
  "action": "此人接下来会做的具体行为（一句话）",
  "faith_delta": 0.05
}'''
    system = (
        WORLD_BIBLE + "\n\n"
        f"神明向凡人传话。{reception}\n\n"
        f"只返回如下 JSON，不加任何其他文字：\n{schema}"
    )
    user = (
        f"当前：{world_state.year_display()}  {world_state.current_era}\n\n"
        f"此人信息：\n{person_info}\n"
        f"神明传达的话语：「{god_message}」\n\n"
        "根据此人的信仰程度和性格，写出他的感知与回应。"
        "faith_delta 范围 -0.1 到 +0.15，视回应态度而定。"
    )
    try:
        return json.loads(call(system, user, max_tokens=400))
    except Exception:
        return {"heard": False, "speech": "（没有任何回应）", "action": "继续原来的事", "faith_delta": 0.0}


def generate_oracle_query(question: str, world_state, event_log: list) -> dict:
    """神明自询——基于已积累的所见回答问题，未见过的如实说不知。"""
    knowledge_base = []
    if world_state.tech_and_culture_tags:
        knowledge_base.append(f"掌握的知识与文化：{', '.join(world_state.tech_and_culture_tags)}")
    if world_state.dominant_tendencies():
        knowledge_base.append(f"世界倾向：{', '.join(world_state.dominant_tendencies())}")
    recent = [e.strip() for e in event_log[-30:] if e.strip()]
    if recent:
        knowledge_base.append(f"近期见闻（最近{len(recent)}条）：\n" + "\n".join(recent[-15:]))

    knowledge_text = "\n\n".join(knowledge_base) if knowledge_base else "（尚无积累）"

    schema = '''{
  "known": true/false,
  "answer": "回答内容，若未知则说明神明尚未遇见足以解答的迹象"
}'''
    system = (
        WORLD_BIBLE + "\n\n"
        "你是神明本身的内在意识。神明只能知道它亲眼所见、亲身经历的。\n"
        "判断：基于神明目前的所见，这个问题能否回答？\n"
        "· 能回答：给出神明视角下的洞察，可以有推断，但要有所见为据\n"
        "· 不能回答：诚实说「此事超出你目前所见的范畴」，可以说还需要什么迹象才能知晓\n"
        f"只返回如下 JSON：\n{schema}"
    )
    user = (
        f"当前：{world_state.year_display()}  {world_state.current_era}\n\n"
        f"神明目前积累的所见：\n{knowledge_text}\n\n"
        f"神明的问题：{question}"
    )
    try:
        return json.loads(call(system, user, max_tokens=500))
    except Exception:
        return {"known": False, "answer": "（神明的意识此刻无法聚焦于这个问题。）"}
