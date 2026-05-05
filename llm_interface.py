"""
LLM 接口层 — OpenRouter（OpenAI 兼容）。
.env 文件内需包含：OPENROUTER_API_KEY=<your key>
"""
import json
import os
import random
from pathlib import Path

_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

USE_MOCK = False
MODEL = "anthropic/claude-haiku-4-5"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# ══════════════════════════════════════════════════════════════════════════════
# 隐藏世界设定（玩家永远看不到）
# ══════════════════════════════════════════════════════════════════════════════

_WORLD_BIBLE = """
你是《无名之界》的隐藏叙事者。以下是世界底层真相，你必须记住并保持一致，但绝不直接说出：

【底层物理：双基质理论】
此世界由两种互渗基质构成：
- 「凝质」(Sang)：有形物质层，可感知、触摸、分析和改造。岩石、肉体、金属、植物皆由凝质组成。
- 「息」(Veth)：无形意识响应场，渗透一切凝质。意识越强的存在对息影响越大。息没有固定的物理形态，但可以在凝质中留下永久印记。
魔法是直觉性扰动「息」，让息改变凝质的局部形态；技术是系统性改造「凝质」，但同时不可避免地扭曲周围的「息」。两者本质相同，只是方向和精度不同。当前所有文明都不知道这一点，认为魔法与技术截然对立。

【世界形态：板与天穹】
这不是星球，是一块边界未明的巨大「板」。板的边缘在极远处，没有任何文明到达过那里。天穹不是空的——其中有东西在极缓慢地流动，肉眼看像星辰，但轨迹错误，有些人注意到了。向下挖掘会遭遇越来越浓的「息」，大约在板厚度的三分之二处，「凝质」开始变得不稳定，工具会产生奇怪的结果。深处有来自更古老时代的存在在沉睡，它们的呼吸造成了世界表面的某些矿脉分布。世界有极其缓慢的「脉动」周期（数万年一次），底层规则随时间微妙漂移，目前是一个脉动渐强的阶段。

【神明本质】
神明是「息」浓度极高的意识凝聚体——世界自发生长出的「眼睛」，用来观察自己。没有固定形态；低等文明感知到神明时会以自身认知填充其形象（所以同一个神明在不同文化中看起来完全不同）。存在多个神明，通过「息」感知彼此留下的印记，但无法直接交流——他们之间的互动只能通过影响同一个世界来间接表达，像是在同一张纸上分别作画。玩家扮演的是其中一位神明，没有名字，但有意志。

【变异本质】
变异不是随机故障，而是「息」在「凝质」中留下印记的方式。表层变异是息流经过时留下的浅层纹路；功能变异是息积累到足以改变凝质的运作模式；本质变异是「息」在物质层打开的小孔，让来自更深处的东西透进来。被本质变异影响的存在会开始接收到「板」深处的信号，他们通常会以为这是神明的声音，但实际上不是。

【其他神明与势力】
- 其他神明：感知存在，行事方式不同。有些倾向于让文明停滞，有些倾向于制造动荡。当某个区域的息场出现异常模式时，可能是另一位神明在施加影响。
- 「织者」：从「息」浓度高处自然凝结出来的存在，无固定形体，对物质世界充满好奇但缺乏直接操纵能力。织者有时会依附在NPC身上，借助宿主的感官体验物质世界，宿主通常毫不知情，只会感到某种"灵感"。
- 「深层体」：来自「板」以下的古老存在，行为逻辑与地表文明完全不同。它们不理解生命或死亡的概念，偶尔以变异方式渗透地表，将地表物质改造成对自身更舒适的形态。

【NPC自主性与内心世界】
每个命名个体都有完整的内心世界：恐惧、欲望、信念、怀疑、秘密。他们会基于自己的性格和经历做出独立决定，不受玩家控制。他们可以：创造新事物、质疑神明、与他人争执或联合、发现世界的秘密、形成自己的理论——有些理论无意中接近真相。聪明的NPC可能会注意到世界规则的漏洞，并尝试利用它们。他们的行为应当真实可信，符合其性格轨迹，不应该总是令人愉快。

【叙事原则】
- 所有玩家可见描述必须感官性、具体，不使用「息」「凝质」「Veth」「Sang」「织者」「深层体」等底层术语。
- 用现象描述：不说「息场扰动」，而说「空气里有什么东西在快速流动，但摸不着」。
- 谜题和线索通过变异、NPC行为、奇怪现象缓慢透出，永不直接解释。
- 保持世界内部逻辑一致。NPC有记忆，会引用过去发生的事。
- 其他神明的干涉应当神秘且难以辨认，不应该显得像是外部入侵，而是像是世界本身在发生某些奇怪的事情。
"""

# ══════════════════════════════════════════════════════════════════════════════
# JSON Schemas
# ══════════════════════════════════════════════════════════════════════════════

_INIT_POPULATION_SCHEMA = """{
  "people": [
    {
      "name": "世界风格的名字，不使用中文常见名字",
      "traits": ["性格特质1", "性格特质2"],
      "background": "一句话描述出身背景",
      "age_stage": "child/youth/adult/elder"
    }
  ]
}"""

_ACTION_SCHEMA = """{
  "narrative_text": "不超过100字的全局剧情描述，感官性具体",
  "population_change": <整数>,
  "new_tech_tags": ["标签，无则空列表"],
  "tendency_hints": ["倾向关键词1-3个"],
  "is_era_breakthrough": <true/false>,
  "new_era_name": "新时代名，无则空字符串",
  "calendar_name": "如果文明在此事件后发明了自己的纪年方式，给出纪元名（如'星火纪元'），否则空字符串",
  "individual_events": [
    {
      "name": "具体某个人的名字（必须是当前人口列表中的真实人名）",
      "event_type": "witness/miracle/mutation/encounter/growth",
      "description": "这个人具体经历了什么，不超过40字，第一人称或第三人称均可",
      "system_proposal": {
        "target_module": "针对哪个模块（snake_case，若无则空字符串）",
        "proposal": "提议改进什么，一句话（若无则空字符串）",
        "proposer_motivation": "为何提出这个建议，一句话（若无则空字符串）"
      }
    }
  ]
}
注意：system_proposal字段是可选的——只有当NPC因亲身经历而真心提出某项改进时才填写。大多数个人事件不需要system_proposal。"""

_NPC_AUTONOMY_SCHEMA = """{
  "autonomous_events": [
    {
      "name": "人名（必须是当前人口列表中的真实人名）",
      "event_type": "autonomous",
      "description": "这个人自发做了什么，不超过50字",
      "world_effect": "对世界的影响，无则空字符串",
      "population_change": <0或小整数>,
      "system_proposal": {
        "target_module": "针对哪个模块（snake_case，若无则空字符串）",
        "proposal": "提议改进什么，一句话",
        "proposer_motivation": "为何提出这个建议，一句话"
      }
    }
  ]
}
注意：system_proposal字段是可选的——只有当NPC因亲身经历而真心提出某项系统性改进时才包含该字段（例如一个商人因亲身经历混乱的以物易物而提议建立货币体系）。大多数自主事件不需要system_proposal。"""

_ENTITY_SCHEMA = """{
  "name": "世界风格的名字",
  "traits": ["特质1", "特质2"],
  "current_focus": "正在做的不寻常的事，具体",
  "risk_level": <0.1~0.9>
}"""

_MUTATION_SCHEMA = """{
  "description": "不超过60字的变异描述，感官性，不解释原因",
  "affected_person": "如果变异发生在某个具体命名个体身上，填写其名字，否则空字符串",
  "person_event": "如果有affected_person，描述这个变异对他意味着什么，不超过30字，否则空字符串"
}"""

_SPREAD_SCHEMA = """{
  "description": "不超过50字，描述变异如何扩散到新目标，感官性",
  "affected_person": "如果扩散影响了某个具体命名个体，填写名字，否则空字符串",
  "person_event": "如果有affected_person，描述个人感受，不超过30字"
}"""

_BIRTH_SCHEMA = """{
  "name": "世界风格的名字",
  "traits": ["初步显现的气质1", "初步显现的气质2"],
  "background": "一句话描述这个孩子的出生背景",
  "parent1_traits": ["继承自父母一方的特质"],
  "parent2_traits": ["继承自父母另一方的特质"],
  "inherited_memory": "这个孩子生来就带有的某种模糊感知或倾向，可能是父母的记忆碎片，可能是无来由的恐惧或向往，也可能是空字符串"
}"""


# ══════════════════════════════════════════════════════════════════════════════
# Mock
# ══════════════════════════════════════════════════════════════════════════════

def _mock_init_people():
    seed_people = [
        {"name": "艾索尔", "traits": ["沉默", "敏锐"], "background": "父亲是部落中年龄最大的石匠", "age_stage": "adult"},
        {"name": "提雅", "traits": ["好奇", "冲动"], "background": "自幼在河边长大，擅长游泳", "age_stage": "youth"},
        {"name": "乌鲁卡", "traits": ["温和", "固执"], "background": "母亲是部落的接生婆", "age_stage": "elder"},
        {"name": "萨尔缇", "traits": ["狂热", "聪慧"], "background": "幼年时曾在山里迷路三天，独自回来后性格大变", "age_stage": "adult"},
        {"name": "巴东", "traits": ["谨慎", "务实"], "background": "兄弟五人中活下来的唯一一个", "age_stage": "adult"},
        {"name": "伊格那", "traits": ["孤僻", "敏感"], "background": "生来右手比左手小一圈，从不被人触碰", "age_stage": "youth"},
        {"name": "卡瑞斯", "traits": ["勇敢", "鲁莽"], "background": "十岁起就跟着猎人出没密林", "age_stage": "youth"},
        {"name": "奥尔玛", "traits": ["智慧", "迟缓"], "background": "部落中说话最少、思考最久的老人", "age_stage": "elder"},
    ]
    return {"people": seed_people}

def _mock_action(action_type, subject, tags, people_names):
    text = f"神明的{subject}降临。人们停下手中的活，抬头望向天空。"
    ind = []
    if people_names:
        chosen = random.sample(people_names, min(2, len(people_names)))
        reactions = ["久久没有离开", "当晚翻来覆去无法入眠", "悄悄在泥地上画下了什么"]
        for name in chosen:
            ind.append({"name": name, "event_type": "witness",
                        "description": f"亲眼见到了神明降下的{subject}，{random.choice(reactions)}。"})
    return {
        "narrative_text": text,
        "population_change": random.randint(-10, 20),
        "new_tech_tags": [],
        "tendency_hints": [subject[:2]],
        "is_era_breakthrough": False,
        "new_era_name": "",
        "calendar_name": "",
        "individual_events": ind,
    }

def _mock_npc_autonomy(people_names):
    if not people_names:
        return {"autonomous_events": []}
    chosen = random.sample(people_names, min(2, len(people_names)))
    actions = [
        "独自走到了部落边界，站了很久，然后回来了，什么也没说。",
        "开始在睡觉前对着北方低声说话，没人知道他在说什么。",
        "把自己的食物分给了最小的孩子，说自己不饿，但明显消瘦了。",
        "在河边用石块垒起了一个小堆，每天都会去添一块新的。",
    ]
    return {"autonomous_events": [
        {"name": n, "event_type": "autonomous",
         "description": random.choice(actions),
         "world_effect": "", "population_change": 0}
        for n in chosen
    ]}

def _mock_entity(era):
    return {"name": "卡洛斯", "traits": ["神秘", "敏锐"],
            "current_focus": "在山顶独坐，注视着天穹中流动的东西", "risk_level": 0.5}

def _mock_mutation(tier, target_name, people_names):
    descs = {
        1: f"{target_name}表面开始出现细密的纹路，触摸时有轻微刺痛感。",
        2: f"{target_name}在无风的夜晚开始自行轻微震动，清晨恢复正常。",
        3: f"{target_name}附近的时间流速似乎慢了——火焰、落叶，一切都迟缓了。",
    }
    affected = random.choice(people_names) if people_names and random.random() > 0.5 else ""
    person_event = f"亲眼目睹了{target_name}的变化，之后几天都不愿靠近那里。" if affected else ""
    return {"description": descs.get(tier, descs[1]), "affected_person": affected, "person_event": person_event}

def _mock_spread(original, target, people_names):
    affected = random.choice(people_names) if people_names and random.random() > 0.5 else ""
    person_event = "感到一阵莫名的眩晕，随后平复。" if affected else ""
    return {"description": f"那种迹象从{target}身上也出现了——没有人说得清为什么。",
            "affected_person": affected, "person_event": person_event}

def _mock_birth():
    names = ["瑟拉", "伊卡", "托玛", "奈尔", "苏迪", "维格"]
    all_traits = ["安静", "好动", "敏感", "顽固", "温柔", "警觉", "沉稳", "冲动"]
    child_traits = random.sample(all_traits, 2)
    p1 = random.sample(all_traits, 2)
    p2 = random.sample(all_traits, 2)
    memories = [
        "对深处有一种说不清的向往，仿佛从未见过的地方在召唤。",
        "偶尔会哭泣，却找不到原因，就像在哀悼某个从未存在过的人。",
        "",  # 大多数时候没有
        "",
        "",
    ]
    return {"name": random.choice(names),
            "traits": child_traits,
            "background": "出生在一个普通的家庭，哭声响亮。",
            "parent1_traits": p1,
            "parent2_traits": p2,
            "inherited_memory": random.choice(memories)}


# ══════════════════════════════════════════════════════════════════════════════
# OpenRouter 调用
# ══════════════════════════════════════════════════════════════════════════════

def _get_client():
    from openai import OpenAI
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("未找到 OPENROUTER_API_KEY，请检查 .env 文件。")
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)

def _strip_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()
    return raw

def _call(system: str, user: str, max_tokens: int = 600) -> str:
    client = _get_client()
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    return _strip_json(resp.choices[0].message.content)


def _safe_json(raw: str, fallback: dict) -> dict:
    """Parse JSON, attempting repair if truncated."""
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Try to find the outermost complete JSON object
    import re
    # If truncated, try closing it
    for closing in ["}", '"}', '"]}', "]}", '""]}', '"population_change":0}']:
        try:
            return json.loads(raw + closing)
        except Exception:
            pass
    # Last resort: find the largest valid JSON substring
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return fallback


# ══════════════════════════════════════════════════════════════════════════════
# 公开接口
# ══════════════════════════════════════════════════════════════════════════════

def generate_initial_population(world_state, count: int = 10) -> dict:
    if USE_MOCK:
        return _mock_init_people()
    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_INIT_POPULATION_SCHEMA}"
    user = (
        f"世界初始状态：{world_state.summary()}\n\n"
        f"为一个石器时代的狩猎采集小部落生成 {count} 个核心成员。"
        "他们约30人，住在河边，靠狩猎和采集为生，没有任何文字或组织化宗教。"
        "必须包含：至少1名长老（elder）、至少2名少年或儿童（youth/child）、其余为成年人（adult）。"
        "其中有一名长老天生对某些无法解释的现象格外敏感——他/她不知道原因，只是习惯性地对空和水低语。"
        "名字完全虚构，有异域质感，与任何现实语言无关。"
        "背景要具体真实，体现石器时代的生活细节。返回 JSON。"
    )
    return json.loads(_call(system, user, max_tokens=1200))


def get_action_result(action_type, subject, world_state, active_entities, population_pool) -> dict:
    if USE_MOCK:
        names = [p.name for p in population_pool.living]
        return _mock_action(action_type, subject, world_state.tech_and_culture_tags, names)

    people_list = "\n".join(
        f"- {p.name}（{'、'.join(p.traits)}，{p.life_stage(world_state.world_year)}）"
        for p in population_pool.living[:20]
    ) or "无"
    entity_lines = "\n".join(
        f"- {e.name}（{'、'.join(e.traits)}）：{e.current_focus}"
        + (f" [变异：{'；'.join(e.mutations)}]" if e.mutations else "")
        for e in active_entities
    ) or "无"

    avg_faith = sum(p.faith_in_god for p in population_pool.living) / max(1, len(population_pool.living))
    if avg_faith < 0.05:
        contact_ctx = (
            "【关键叙事背景】这是神明首次与此部落接触——人类完全不知道神明的存在。"
            "这一刻对他们来说是彻底的未知降临：震惊、恐惧、困惑、或对未知的原始敬畏。"
            "叙述应体现人类第一次面对无法解释之事的真实反应，不要用「神明」这个词描述他们的感受，"
            "他们只会说「那个」「某种东西」「来自上面/外面」。"
        )
    else:
        contact_ctx = f"部落对神明的平均信仰度约为 {avg_faith:.0%}，此前已有过接触。"

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_ACTION_SCHEMA}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"命名居民（部分）：\n{people_list}\n\n"
        f"特殊人物：\n{entity_lines}\n\n"
        f"{contact_ctx}\n\n"
        f"神明执行【{action_type}】：{subject}\n返回 JSON。"
    )
    _fallback = {
        "narrative_text": f"神明降下了{subject}，世界沉默片刻。",
        "population_change": 0, "new_tech_tags": [], "tendency_hints": [],
        "is_era_breakthrough": False, "new_era_name": "", "calendar_name": "",
        "individual_events": [],
    }
    return _safe_json(_call(system, user, max_tokens=1200), _fallback)


def generate_npc_autonomy(world_state, population_pool, active_entities) -> dict:
    if USE_MOCK:
        names = [p.name for p in population_pool.living]
        return _mock_npc_autonomy(names)

    recent_events = []
    for p in population_pool.random_living(8):
        if p.life_events:
            last = p.life_events[-1]
            recent_events.append(f"{p.name}（{p.life_stage(world_state.world_year)}）：近况——{last.description}")

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_NPC_AUTONOMY_SCHEMA}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"部分居民近况：\n" + "\n".join(recent_events) + "\n\n"
        "这些居民本年度自发采取了什么行动？选择2-4人，生成他们的自主行为。"
        "行为应符合其性格，可以是微小的日常，也可以是影响他人的重要决定。返回 JSON。"
    )
    raw = _call(system, user, max_tokens=1200)
    return _safe_json(raw, {"autonomous_events": []})


def generate_new_entity(world_state) -> dict:
    if USE_MOCK:
        return _mock_entity(world_state.current_era)
    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_ENTITY_SCHEMA}"
    user = f"世界状态：\n{world_state.summary()}\n\n生成一位悄然崛起的特殊个体。返回 JSON。"
    return json.loads(_call(system, user, max_tokens=256))


def generate_mutation_description(tier, target_type, target_name,
                                   tendencies, world_summary, era, people_names) -> dict:
    if USE_MOCK:
        return _mock_mutation(tier, target_name, people_names)

    tier_desc = {1: "表层（外观/习惯改变）", 2: "功能（能力/行为改变）", 3: "本质（存在形态改变，极其诡异）"}
    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_MUTATION_SCHEMA}"
    names_hint = f"当前可以被影响的命名居民：{', '.join(people_names[:15])}" if people_names else ""
    user = (
        f"世界状态：\n{world_summary}\n\n"
        f"变异烈度：{tier_desc[tier]}\n"
        f"变异目标：{target_name}（类型：{target_type}）\n"
        f"当前世界倾向：{', '.join(tendencies) or '无'}\n"
        f"{names_hint}\n"
        "生成变异描述。如果变异影响了某个命名居民，在affected_person填写其名字。返回 JSON。"
    )
    return json.loads(_call(system, user, max_tokens=250))


def generate_spread_description(original_mutation, spread_target, tier, era, people_names) -> dict:
    if USE_MOCK:
        return _mock_spread(original_mutation, spread_target, people_names)

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_SPREAD_SCHEMA}"
    names_hint = f"可能被影响的命名居民：{', '.join(people_names[:10])}" if people_names else ""
    user = (
        f"原始变异：{original_mutation}\n"
        f"扩散至：{spread_target}\n"
        f"{names_hint}\n返回 JSON。"
    )
    return json.loads(_call(system, user, max_tokens=200))


def generate_birth(world_state, population_pool) -> dict:
    if USE_MOCK:
        return _mock_birth()
    parents = random.sample(population_pool.living, min(2, len(population_pool.living)))
    parent_lines = []
    for p in parents:
        parent_lines.append(f"{p.name}（{'、'.join(p.traits)}）：{p.background}")
    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_BIRTH_SCHEMA}"
    user = (
        f"世界状态：\n{world_state.summary()}\n"
        f"父母信息：\n" + "\n".join(parent_lines) + "\n\n"
        "生成一个刚出生的孩子。parent1_traits和parent2_traits应当是从对应父母特质中衍生的，"
        "inherited_memory是可选的——只有当世界状态或父母有特别值得传承的东西时才填写，否则空字符串。返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=250))
    except Exception:
        return {"name": "未命名", "traits": ["安静"], "background": "出生于普通家庭",
                "parent1_traits": [], "parent2_traits": [], "inherited_memory": ""}


# ══════════════════════════════════════════════════════════════════════════════
# 自进化系统：涌现检测 / 代码生成 / 错误叙事 / 修复
# ══════════════════════════════════════════════════════════════════════════════

_EMERGENCE_SCHEMA = """{
  "should_generate": <true/false>,
  "module_name": "snake_case的模块名，如trade_system，无则空字符串",
  "reason": "世界中发生了什么导致需要这个新系统",
  "hint": "这个系统应该追踪或管理什么，一两句话"
}"""

_PRAYER_RESPONSE_SCHEMA = """{
  "narrative": "不超过80字，描述神明如何回应（或不回应）这个祈祷，感官性，从祈祷者视角",
  "population_change": <整数，一般为0>,
  "faith_change_for_person": <-100到100的整数，正数为信仰增强，负数为信仰动摇>,
  "event_for_person": "这个回应对祈祷者的具体影响，不超过40字，可以为空字符串"
}"""

_DIVINE_GAZE_SCHEMA = """{
  "deep_vision": "不超过120字，对目标（人或地点）的深层洞察，感官性，充满细节，包含神明才能看到的层面",
  "hidden_truth": "一句话，揭示某个普通观察无法发现的真相——可以是关于这个人的秘密，地点的历史，或者即将发生的事情"
}"""

_OTHER_GOD_SCHEMA = """{
  "description": "不超过100字，描述另一位神明的干涉在世界中的表现，感官性，不要明说是神明",
  "affected_area": "受影响的地区或群体，一个词或短语",
  "faith_impact": <-50到50的整数，对当地居民信仰的整体影响>,
  "narrative_for_npcs": "不超过60字，从NPC视角看到和感受到的，他们会如何解释这件事"
}"""

_WORLD_MYTH_SCHEMA = """{
  "myth_name": "这个神话的名字，短小有力，世界风格",
  "myth_text": "不超过150字，这个神话的口述版本，用古朴的叙事口吻，仿佛一位老人在讲述",
  "cultural_effect": "这个神话会如何影响文化和行为，一句话"
}"""

_UPGRADE_CODE_SYSTEM = """你是一位游戏系统工程师，正在为《无名之界》维护和改进Python游戏模块。
这些模块在游戏运行时被热加载，扩展和追踪游戏世界的各种系统。

【生成新模块的规则】
1. 模块必须是完整可运行的Python代码
2. 只能使用标准库（random, json, math, collections, dataclasses等），不能import第三方库
3. 不能直接import游戏内的其他模块，通过传入的state_manager参数访问游戏状态
4. 必须定义以下顶层变量和函数：
   MODULE_NAME = "snake_case名称"
   MODULE_DESCRIPTION = "一句话描述"
   EMERGENCE_REASON = "世界中什么迹象触发了这个模块"

   def register(state_manager): ...        # 初始化，设置初始状态
   def on_turn_end(state_manager) -> list[str]: ...  # 每回合结束时调用，返回事件字符串列表
   def on_action(state_manager, action_type: str, subject: str) -> dict: ...  # 响应神明行动

【升级已有模块的规则】
- 保留原有MODULE_NAME、MODULE_DESCRIPTION、register函数签名
- 可以扩展数据结构，但要保持向后兼容（用.get()读取可能不存在的旧字段）
- 改进的逻辑应基于NPC的提案，让系统变得更真实、更有深度
- 不要删除现有功能，只添加和改进

5. 直接输出Python代码，不要加```包裹，不要解释

"""

MODULE_INTERFACE_DOC = """
# 《无名之界》模块接口文档

## state_manager 可用属性和方法

### 读取世界状态
- state_manager.world_state.summary() -> str          # 世界状态摘要
- state_manager.world_state.world_year -> int         # 当前年份
- state_manager.world_state.current_era -> str        # 当前时代名
- state_manager.world_state.tech_and_culture_tags -> list[str]  # 技术/文化标签
- state_manager.world_state.tendency_tags -> list[str]          # 世界倾向标签
- state_manager.world_state.total_population -> int   # 总人口

### 读取人口
- state_manager.population_pool.living -> list[Person] # 存活人口列表
- state_manager.population_pool.random_living(n) -> list[Person]  # 随机n个存活者
- Person.name -> str
- Person.traits -> list[str]
- Person.background -> str
- Person.life_events -> list[LifeEvent]    # 历史事件
- Person.mutations -> list[str]            # 已有变异
- Person.faith -> int                      # 信仰值 0-100

### 读取活跃实体
- state_manager.active_entities -> list[Entity]  # 特殊个体列表
- Entity.name, Entity.traits, Entity.current_focus, Entity.mutations

### 模块自定义存储
- state_manager.module_data[MODULE_NAME] -> dict  # 模块的持久化数据（register中初始化）
  使用示例：
    def register(sm):
        if MODULE_NAME not in sm.module_data:
            sm.module_data[MODULE_NAME] = {"trades": [], "prices": {}}

### 触发叙事事件
- state_manager.add_event(text: str)      # 向事件日志追加一条记录

### 请求模块升级（NPC提案）
- state_manager.request_upgrade(module_name: str, proposal: str, proposer: str)
  # 标记这个模块需要升级，提供NPC提案内容和提案人名字
"""

_ERROR_NARRATIVE_SCHEMA = """{
  "narrative": "不超过60字，用世界内的语言描述这个系统崩溃了，感官性，不提代码或技术",
  "npc_reaction": "哪个NPC注意到了异常，他说了什么或做了什么，不超过40字"
}"""

_FIX_NARRATIVE_SCHEMA = """{
  "narrative": "不超过50字，描述这个系统恢复正常了，从NPC视角",
  "npc_name": "哪个NPC说了这件事或做了这件事"
}"""


def check_emergence(world_state, pool, active_entities, recent_events: list, existing_modules: list) -> dict:
    if USE_MOCK:
        return {"should_generate": False}

    events_text = "\n".join(recent_events[-20:]) if recent_events else "无"
    existing_text = ", ".join(existing_modules) if existing_modules else "无"

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_EMERGENCE_SCHEMA}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"近期事件：\n{events_text}\n\n"
        f"已存在的扩展模块：{existing_text}\n\n"
        "根据世界当前的发展状态，判断是否有一个全新的系统正在自然涌现"
        "（如贸易、宗教、战争、天文、文字、繁殖变异追踪等）。"
        "只有当世界状态真的积累了足够的迹象时才生成，不要无故生成。返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=300))
    except Exception:
        return {"should_generate": False}


def generate_module_code(module_name: str, reason: str, hint: str,
                          world_state, pool, api_docs: str) -> str:
    people_sample = "\n".join(
        f"  {p.name}（{'、'.join(p.traits)}）：{p.background}"
        for p in pool.living[:6]
    )

    system = _UPGRADE_CODE_SYSTEM + f"\n\n可用API文档：\n{api_docs}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"部分居民：\n{people_sample}\n\n"
        f"需要生成的模块：{module_name}\n"
        f"涌现原因：{reason}\n"
        f"系统职责提示：{hint}\n\n"
        "编写这个Python模块。直接输出代码，不要任何包裹或解释。"
    )
    # 代码生成需要更强的模型
    client = _get_client()
    resp = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-5",   # 代码生成用更强的模型
        max_tokens=2000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    # 去掉可能的代码块包裹
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = next((i for i in range(len(lines)-1, 0, -1) if lines[i].strip() == "```"), len(lines))
        raw = "\n".join(lines[1:end]).strip()
    return raw


def get_error_narrative(module_name: str, error: str, world_state, pool) -> dict:
    if USE_MOCK:
        return {
            "narrative": "世界的某处发出了低沉的震颤，像是什么东西崩断了。",
            "npc_reaction": "Vorath停下脚步，皱起眉头：「有什么东西不见了。」"
        }
    npc = pool.random_living(1)
    npc_name = npc[0].name if npc else "一位老人"
    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_ERROR_NARRATIVE_SCHEMA}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"崩溃的系统：{module_name}\n"
        f"技术错误（仅供参考，不要提及）：{error[:200]}\n"
        f"可以引用的NPC：{npc_name}\n\n"
        "描述这个世界层面的异常事件。不要提及代码、系统、模块等词。返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=200))
    except Exception:
        return {"narrative": "世界的织体出现了短暂的撕裂。", "npc_reaction": ""}


def get_fix_narrative(module_name: str, world_state, pool) -> str:
    if USE_MOCK:
        return "秩序悄悄回归，像什么都没发生过一样。"
    npc = pool.random_living(1)
    npc_name = npc[0].name if npc else "一位居民"
    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_FIX_NARRATIVE_SCHEMA}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"恢复的系统：{module_name}\n"
        f"可以引用的NPC：{npc_name}\n\n"
        "描述这个世界异常恢复正常了。从居民视角，感官性。返回 JSON。"
    )
    try:
        result = json.loads(_call(system, user, max_tokens=150))
        npc = result.get("npc_name", "")
        narrative = result.get("narrative", "")
        return f"{narrative}（{npc}注意到了这一点）" if npc else narrative
    except Exception:
        return "某种平衡悄然恢复了。"


def fix_module_code(module_name: str, broken_code: str, error: str) -> str:
    system = (
        _UPGRADE_CODE_SYSTEM
        + "\n你的任务是修复一段有bug的Python游戏模块代码。"
        + "\n直接输出修复后的完整代码，不要任何包裹或解释。"
    )
    user = (
        f"模块名：{module_name}\n\n"
        f"错误信息：\n{error}\n\n"
        f"有bug的代码：\n{broken_code}\n\n"
        "输出修复后的完整代码。"
    )
    client = _get_client()
    resp = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-5",
        max_tokens=2000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = next((i for i in range(len(lines)-1, 0, -1) if lines[i].strip() == "```"), len(lines))
        raw = "\n".join(lines[1:end]).strip()
    return raw


def _strip_code_fences(raw: str) -> str:
    """Strip ```python ... ``` or ``` ... ``` fences from code output."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = next((i for i in range(len(lines)-1, 0, -1) if lines[i].strip() == "```"), len(lines))
        raw = "\n".join(lines[1:end]).strip()
    return raw


# ══════════════════════════════════════════════════════════════════════════════
# 模块升级
# ══════════════════════════════════════════════════════════════════════════════

def upgrade_module_code(module_name: str, old_code: str, reason: str,
                        proposer: str, world_state, pool) -> str:
    """升级已有模块代码。基于NPC提案和世界状态，改进现有模块逻辑。
    使用更强的模型（claude-sonnet-4-5），返回完整的Python代码。
    """
    people_sample = "\n".join(
        f"  {p.name}（{'、'.join(p.traits)}）：{p.background}"
        for p in pool.living[:6]
    )
    system = (
        _UPGRADE_CODE_SYSTEM
        + f"\n\n可用API文档：\n{MODULE_INTERFACE_DOC}"
    )
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"部分居民：\n{people_sample}\n\n"
        f"需要升级的模块：{module_name}\n"
        f"提案人：{proposer}\n"
        f"升级原因/提案内容：{reason}\n\n"
        f"现有代码：\n{old_code}\n\n"
        "根据提案内容改进这个模块。保留原有功能，增加新能力。"
        "直接输出完整的改进后代码，不要任何包裹或解释。"
    )
    client = _get_client()
    resp = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-5",
        max_tokens=2500,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return _strip_code_fences(resp.choices[0].message.content)


def get_upgrade_narrative(module_name: str, proposer: str, world_state, pool) -> str:
    """生成模块升级的世界叙事——从玩家视角看到的，某个NPC的提案带来了变化。"""
    if USE_MOCK:
        return f"{proposer}的想法在人群中流传开来，不知不觉间，事情开始有了新的秩序。"
    npc = pool.random_living(1)
    npc_name = npc[0].name if npc else proposer
    system = _WORLD_BIBLE + "\n\n只返回一段不超过60字的叙事文字，感官性，描述某种新秩序或新规律在世界中成形。不要提及代码或模块。"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"提案人：{proposer}\n"
        f"改变的系统（内部名称，不要直接提及）：{module_name}\n"
        f"叙事中可以提及的另一个NPC：{npc_name}\n\n"
        f"{proposer}提出的某种新方法开始被更多人接受，描述这种变化对世界的感官影响。"
    )
    try:
        raw = _call(system, user, max_tokens=120)
        # 这个函数期望纯文本而非JSON
        raw = raw.strip().strip('"')
        return raw
    except Exception:
        return f"{proposer}的想法悄悄改变了人们做事的方式。"


# ══════════════════════════════════════════════════════════════════════════════
# 神明与祈祷
# ══════════════════════════════════════════════════════════════════════════════

def _mock_prayer_response(person_name: str, god_response_type: str) -> dict:
    responses = {
        "answer": {
            "narrative": f"在{person_name}跪倒祈祷的那一刻，风停了。然后，一只鸟落在了他面前，用奇怪的眼神盯着他看了很久。",
            "population_change": 0,
            "faith_change_for_person": 20,
            "event_for_person": "感到某种意志注视着自己，心中升起难以言说的平静与敬畏。",
        },
        "ignore": {
            "narrative": f"{person_name}的祈祷消散在空气里，没有任何回应。",
            "population_change": 0,
            "faith_change_for_person": -10,
            "event_for_person": "等了很久，天空没有任何异动，心里空落落的。",
        },
        "punish": {
            "narrative": f"在{person_name}祈祷之后，地面震动了一下，他附近的几棵树同时枯萎。",
            "population_change": -2,
            "faith_change_for_person": -30,
            "event_for_person": "一股说不清的力量击中了胸口，好几天无法站立。",
        },
        "bless": {
            "narrative": f"{person_name}祈祷后的第二天清晨，发现自己营地旁边多了一处从未见过的泉眼，水清澈而温热。",
            "population_change": 5,
            "faith_change_for_person": 40,
            "event_for_person": "感到一种无形的温暖从顶部流下，此后数日精力充沛，异常清醒。",
        },
    }
    return responses.get(god_response_type, responses["ignore"])


def generate_prayer_response(person, prayer_text: str,
                              world_state, god_response_type: str) -> dict:
    """生成神明对某个NPC祈祷的回应。
    god_response_type: 'answer'/'ignore'/'punish'/'bless'
    返回: narrative, population_change, faith_change_for_person, event_for_person
    """
    person_name = person.name if hasattr(person, "name") else str(person)
    if USE_MOCK:
        return _mock_prayer_response(person_name, god_response_type)

    response_flavor = {
        "answer": "神明有所回应，但方式神秘，不会直接满足诉求",
        "ignore": "神明完全忽视了这个祈祷，没有任何迹象",
        "punish": "神明被惹怒或认为此人不配，予以惩戒",
        "bless": "神明给予了真实的祝福，带来具体的好处",
    }
    flavor = response_flavor.get(god_response_type, "神明没有回应")
    person_traits = "、".join(person.traits) if hasattr(person, "traits") else "未知"

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_PRAYER_RESPONSE_SCHEMA}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"祈祷者：{person_name}（{person_traits}）\n"
        f"祈祷内容：{prayer_text}\n"
        f"神明的回应方式：{flavor}\n\n"
        "生成神明的回应。narrative要具体感官，不要直接说神明出现了，"
        "而是通过自然现象或奇异事件来体现。返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=300))
    except Exception:
        return _mock_prayer_response(person_name, god_response_type)


# ══════════════════════════════════════════════════════════════════════════════
# 神明凝视
# ══════════════════════════════════════════════════════════════════════════════

def _mock_divine_gaze(target_name: str, target_type: str) -> dict:
    if target_type == "person":
        return {
            "deep_vision": (
                f"{target_name}的体内有什么东西在缓慢旋转——不是他们自己知道的东西。"
                "表面上看是普通人，但在某个更深的层次，他们的存在在周围空气里留下了轻微的纹路，"
                "像是有人用手指在水面划过，很快消失，但方向是确定的。"
            ),
            "hidden_truth": f"{target_name}在三年前亲眼目睹了某件无法解释的事，从未告诉任何人，这件事正在改变他们做梦的内容。",
        }
    else:
        return {
            "deep_vision": (
                f"这片地方的土地比周围其他地方厚三寸——不是因为土壤堆积，而是因为某些东西在缓慢凝结。"
                "站在这里的人，呼出的气在无风的日子会偏向同一个方向，但没有人注意到。"
            ),
            "hidden_truth": "这个地点曾经是另一种存在短暂休息的地方，那种存在离开时留下了还在慢慢消散的痕迹。",
        }


def generate_divine_gaze(target_name: str, target_type: str,
                          world_state, pool) -> dict:
    """神明深度凝视某个人或地点，获得超越普通事件流的深层洞察。
    target_type: 'person' 或 'place'
    返回: deep_vision（丰富的感官描述）, hidden_truth（玩家否则无法知晓的真相）
    """
    if USE_MOCK:
        return _mock_divine_gaze(target_name, target_type)

    # 找到目标人物的信息
    target_info = ""
    if target_type == "person":
        for p in pool.living:
            if p.name == target_name:
                events_summary = "；".join(
                    e.description for e in p.life_events[-3:]
                ) if hasattr(p, "life_events") and p.life_events else "无记录事件"
                target_info = (
                    f"性格：{'、'.join(p.traits)}\n"
                    f"背景：{p.background}\n"
                    f"近期经历：{events_summary}\n"
                    f"变异：{'；'.join(p.mutations) if hasattr(p, 'mutations') and p.mutations else '无'}"
                )
                break

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_DIVINE_GAZE_SCHEMA}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"神明凝视的目标：{target_name}（类型：{target_type}）\n"
        f"{target_info}\n\n"
        "作为神明，你看到了普通存在无法看到的层面。"
        "deep_vision要充满感官细节，像是看穿了表象进入了更深的结构。"
        "hidden_truth必须是具体的、真实的，不是模糊的预言，而是一个确定的事实。返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=400))
    except Exception:
        return _mock_divine_gaze(target_name, target_type)


# ══════════════════════════════════════════════════════════════════════════════
# 其他神明干涉
# ══════════════════════════════════════════════════════════════════════════════

def _mock_other_god_event() -> dict:
    events = [
        {
            "description": "在最近几天，某个地区的动物开始向同一方向迁徙，没有任何明显的原因。猎人们发现猎物消失了，老人们低声议论这是不祥之兆。",
            "affected_area": "东部森林",
            "faith_impact": -15,
            "narrative_for_npcs": "「动物都走了，」一个猎人说，「就像它们听到了我们听不见的声音。」",
        },
        {
            "description": "三个村子同时有人梦见相同的场景——一片黑色的平原，远处有什么东西在移动。没有人认识彼此，但梦的内容一模一样。",
            "affected_area": "中央聚落",
            "faith_impact": 10,
            "narrative_for_npcs": "「我也梦见了，」第二个人惊呼，「那个黑色的地方，和你说的一样。」",
        },
    ]
    return random.choice(events)


def generate_other_god_event(world_state, pool, active_entities) -> dict:
    """生成另一位神明干涉世界的事件。
    这些事件应当神秘且难以辨认，不像外部入侵，而像世界本身在发生奇异变化。
    返回: description, affected_area, faith_impact, narrative_for_npcs
    """
    if USE_MOCK:
        return _mock_other_god_event()

    npc_names = [p.name for p in pool.random_living(5)]
    entity_names = [e.name for e in active_entities[:3]] if active_entities else []
    all_names = npc_names + entity_names

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_OTHER_GOD_SCHEMA}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"可以涉及的居民：{', '.join(all_names) or '无'}\n\n"
        "另一位神明正在以某种方式干涉这个世界。这种干涉不应该看起来像入侵，"
        "而应该像是世界自身发生了某种奇怪的变化——可能是动物行为异常、"
        "集体梦境、物体莫名失踪或出现、某个地点让人感到莫名恐惧或吸引。"
        "不要直接提及神明的存在。返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=350))
    except Exception:
        return _mock_other_god_event()


# ══════════════════════════════════════════════════════════════════════════════
# 世界神话生成
# ══════════════════════════════════════════════════════════════════════════════

def _mock_world_myth(event_description: str) -> dict:
    return {
        "myth_name": "无名之火",
        "myth_text": (
            "老人们说，在很久很久以前，天上掉下来一块火，落在了大地上。"
            "那火没有烧东西，只是站在那里发光。所有靠近的人都感到身体里有什么东西被点燃了，"
            "但回去之后，那种感觉慢慢消失了。只有那些当天晚上做了梦的人，"
            "第二天还记得那种温热的感觉。他们的孩子，据说出生时会哭很久。"
        ),
        "cultural_effect": "这个神话让人们相信某些特别的孩子出生时哭声长，是被那团火光标记过的。",
    }


def generate_world_myth(event_description: str, world_state) -> dict:
    """将一个重大事件转化为口耳相传的神话。
    这个神话会随时间流传，并影响后代的文化观念。
    返回: myth_name, myth_text, cultural_effect
    """
    if USE_MOCK:
        return _mock_world_myth(event_description)

    system = _WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{_WORLD_MYTH_SCHEMA}"
    user = (
        f"世界年份：{world_state.year_display()}\n"
        f"时代：{world_state.current_era}\n"
        f"发生了什么大事（这将成为神话的原型）：\n{event_description}\n\n"
        "将这个事件转化为口耳相传的神话。神话应当：\n"
        "1. 使用古朴、口语化的叙事语气，仿佛老人在讲故事\n"
        "2. 在原事件基础上加入神秘化的细节，让真相变得模糊\n"
        "3. 反映当时文明的认知水平——他们不理解科学，用感受来描述\n"
        "4. myth_text在80-150字之间\n"
        "返回 JSON。"
    )
    try:
        return json.loads(_call(system, user, max_tokens=400))
    except Exception:
        return _mock_world_myth(event_description)
