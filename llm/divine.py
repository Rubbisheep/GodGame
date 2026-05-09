"""神明相关生成：祈祷回应、神明凝视、自询、生活切片、年度回望。"""
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


def generate_yearly_digest(world_state, raw_events: list[str]) -> str:
    """把当年的多条原始事件压成一段连贯叙事，让玩家读得懂。
    LLM 失败时返回空串，调用方应有兜底。"""
    cleaned = [e.strip() for e in raw_events if e and e.strip()]
    if not cleaned:
        return ""

    events_text = "\n".join(f"- {e}" for e in cleaned[-25:])
    schema = '''{
  "narrative": "一段不超过 100 字的叙事文字"
}'''
    system = (
        WORLD_BIBLE + "\n\n"
        "你是这个世界的叙事者。把这一年里发生的若干件事，压缩成一段连贯的散文，让玩家读得懂在发生什么。\n\n"
        "硬性要求：\n"
        "- 不超过 100 字\n"
        "- 散文体，感官化，像在讲故事\n"
        "- 抓 1-2 件最重要的事讲清楚；其余作为背景一笔带过；不重要的可以省略\n"
        "- 不要罗列事件——把它们融进叙事\n"
        "- 绝对禁止：方括号【】[]、书名号《》、数字参数（强度0.7）、英文术语 vocalization/symbol_sequence、"
        "模块名（mutation_system 之类）、「玩家」「神明」「世界」「模块」等元词汇\n"
        "- 避免重复同义事件——若多条事件描述同一类现象，融合成一句\n"
        "- 不解释为什么、不点评，只白描发生了什么\n\n"
        f"只返回如下 JSON：\n{schema}"
    )
    user = (
        f"年份：{world_state.year_display()}（{world_state.current_era}）\n"
        f"人口：{world_state.population}\n\n"
        f"这一年发生的原始事件：\n{events_text}\n\n"
        "压成一段叙事。"
    )
    try:
        result = json.loads(call(system, user, max_tokens=400))
        return (result.get("narrative") or "").strip()
    except Exception:
        return ""

