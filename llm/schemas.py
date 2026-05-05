"""所有 JSON schema 常量 + 对应的 mock 数据函数。"""
import random

# ── Schema 定义 ────────────────────────────────────────────────────────────

INIT_POPULATION = """{
  "people": [
    {
      "name": "世界风格的名字，不使用中文常见名字",
      "traits": ["性格特质1", "性格特质2"],
      "background": "一句话描述出身背景",
      "age_stage": "child/youth/adult/elder"
    }
  ]
}"""

ACTION = """{
  "narrative_text": "不超过100字的全局剧情描述，感官性具体",
  "population_change": <整数>,
  "new_tech_tags": ["标签，无则空列表"],
  "tendency_hints": ["倾向关键词1-3个"],
  "is_era_breakthrough": <true/false>,
  "new_era_name": "新时代名，无则空字符串",
  "calendar_name": "如果文明发明了纪年法，给出纪元名，否则空字符串",
  "individual_events": [
    {
      "name": "具体某人的名字（必须是当前人口列表中的真实人名）",
      "event_type": "witness/miracle/mutation/encounter/growth",
      "description": "这个人具体经历了什么，不超过40字",
      "system_proposal": {
        "target_module": "针对哪个模块（snake_case，若无则空字符串）",
        "proposal": "提议改进什么，一句话（若无则空字符串）",
        "proposer_motivation": "为何提出这个建议（若无则空字符串）"
      }
    }
  ]
}
注意：system_proposal 是可选的，只有当NPC真心提出改进时才填写。"""

NPC_AUTONOMY = """{
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
        "proposer_motivation": "为何提出这个建议"
      }
    }
  ]
}
注意：system_proposal 是可选的，只有NPC真正提出系统性改进时才包含。"""

ENTITY = """{
  "name": "世界风格的名字",
  "traits": ["特质1", "特质2"],
  "current_focus": "正在做的不寻常的事，具体",
  "risk_level": <0.1~0.9>
}"""

MUTATION = """{
  "description": "不超过60字的变异描述，感官性，不解释原因",
  "affected_person": "如果变异发生在某个具体命名个体身上，填写其名字，否则空字符串",
  "person_event": "如果有affected_person，描述这个变异对他意味着什么，不超过30字，否则空字符串"
}"""

SPREAD = """{
  "description": "不超过50字，描述变异如何扩散到新目标，感官性",
  "affected_person": "如果扩散影响了某个具体命名个体，填写名字，否则空字符串",
  "person_event": "如果有affected_person，描述个人感受，不超过30字"
}"""

BIRTH = """{
  "name": "世界风格的名字",
  "traits": ["初步显现的气质1", "初步显现的气质2"],
  "background": "一句话描述这个孩子的出生背景",
  "parent1_traits": ["继承自父母一方的特质"],
  "parent2_traits": ["继承自父母另一方的特质"],
  "inherited_memory": "这个孩子生来带有的某种模糊感知或倾向，可以是空字符串"
}"""

EMERGENCE = """{
  "should_generate": <true/false>,
  "module_name": "snake_case的模块名，如trade_system，无则空字符串",
  "reason": "世界中发生了什么导致需要这个新系统",
  "hint": "这个系统应该追踪或管理什么，一两句话"
}"""

PRAYER_RESPONSE = """{
  "narrative": "不超过80字，描述神明如何回应这个祈祷，感官性，从祈祷者视角",
  "population_change": <整数，一般为0>,
  "faith_change_for_person": <-100到100的整数>,
  "event_for_person": "这个回应对祈祷者的具体影响，不超过40字"
}"""

DIVINE_GAZE = """{
  "deep_vision": "不超过120字，对目标的深层洞察，感官性，包含神明才能看到的层面",
  "hidden_truth": "一句话，揭示某个普通观察无法发现的真相"
}"""

OTHER_GOD = """{
  "description": "不超过100字，描述另一位神明的干涉在世界中的表现，感官性，不要明说是神明",
  "affected_area": "受影响的地区或群体，一个词或短语",
  "faith_impact": <-50到50的整数>,
  "narrative_for_npcs": "不超过60字，从NPC视角看到和感受到的"
}"""

WORLD_MYTH = """{
  "myth_name": "这个神话的名字，短小有力，世界风格",
  "myth_text": "不超过150字，这个神话的口述版本，用古朴的叙事口吻",
  "cultural_effect": "这个神话会如何影响文化和行为，一句话"
}"""

ERROR_NARRATIVE = """{
  "narrative": "不超过60字，用世界内的语言描述这个系统崩溃了，感官性，不提代码或技术",
  "npc_reaction": "哪个NPC注意到了异常，他说了什么或做了什么，不超过40字"
}"""

FIX_NARRATIVE = """{
  "narrative": "不超过50字，描述这个系统恢复正常了，从NPC视角",
  "npc_name": "哪个NPC说了这件事或做了这件事"
}"""


# ── Mock 数据 ──────────────────────────────────────────────────────────────

def mock_init_people() -> dict:
    return {"people": [
        {"name": "艾索尔", "traits": ["沉默", "敏锐"],   "background": "父亲是部落中年龄最大的石匠",           "age_stage": "adult"},
        {"name": "提雅",   "traits": ["好奇", "冲动"],   "background": "自幼在河边长大，擅长游泳",             "age_stage": "youth"},
        {"name": "乌鲁卡", "traits": ["温和", "固执"],   "background": "母亲是部落的接生婆",                   "age_stage": "elder"},
        {"name": "萨尔缇", "traits": ["狂热", "聪慧"],   "background": "幼年迷路三天独自回来后性格大变",       "age_stage": "adult"},
        {"name": "巴东",   "traits": ["谨慎", "务实"],   "background": "兄弟五人中活下来的唯一一个",           "age_stage": "adult"},
        {"name": "伊格那", "traits": ["孤僻", "敏感"],   "background": "生来右手比左手小一圈，从不被人触碰",   "age_stage": "youth"},
        {"name": "卡瑞斯", "traits": ["勇敢", "鲁莽"],   "background": "十岁起就跟着猎人出没密林",             "age_stage": "youth"},
        {"name": "奥尔玛", "traits": ["智慧", "迟缓"],   "background": "部落中说话最少、思考最久的长者",       "age_stage": "elder"},
        {"name": "代尔",   "traits": ["温顺", "勤劳"],   "background": "每天最早起来重新点燃营地的火",         "age_stage": "child"},
        {"name": "费罗卡", "traits": ["好动", "粗心"],   "background": "手上总有新伤口，说不清是怎么来的",     "age_stage": "child"},
    ]}


def mock_action(action_type: str, subject: str, people_names: list) -> dict:
    ind = []
    if people_names:
        for name in random.sample(people_names, min(2, len(people_names))):
            ind.append({"name": name, "event_type": "witness",
                        "description": f"亲眼见到了神明降下的{subject}，久久无法平静。"})
    return {
        "narrative_text": f"神明的{subject}降临。人们停下手中的活，抬头望向天空——那里有什么东西他们以前从未见过。",
        "population_change": random.randint(-5, 15),
        "new_tech_tags": [], "tendency_hints": [subject[:2]],
        "is_era_breakthrough": False, "new_era_name": "", "calendar_name": "",
        "individual_events": ind,
    }


def mock_npc_autonomy(people_names: list) -> dict:
    if not people_names:
        return {"autonomous_events": []}
    actions = [
        "独自走到了部落边界，站了很久，然后回来了，什么也没说。",
        "开始在睡觉前对着北方低声说话，没人知道他在说什么。",
        "把自己的食物分给了最小的孩子，说自己不饿，但明显消瘦了。",
        "在河边用石块垒起了一个小堆，每天都会去添一块新的。",
        "发现了一种用石头划出深纹路的方法，开始在洞口刻下奇怪的符号。",
    ]
    return {"autonomous_events": [
        {"name": n, "event_type": "autonomous",
         "description": random.choice(actions),
         "world_effect": "", "population_change": 0}
        for n in random.sample(people_names, min(2, len(people_names)))
    ]}


def mock_entity(era: str) -> dict:
    return {"name": "卡洛斯", "traits": ["神秘", "敏锐"],
            "current_focus": "在山顶独坐，注视着天穹中流动的东西", "risk_level": 0.5}


def mock_mutation(tier: int, target_name: str, people_names: list) -> dict:
    descs = {
        1: f"{target_name}表面开始出现细密的纹路，触摸时有轻微刺痛感。",
        2: f"{target_name}在无风的夜晚开始自行轻微震动，清晨恢复正常。",
        3: f"{target_name}附近的时间流速似乎慢了——火焰、落叶，一切都迟缓了。",
    }
    affected = random.choice(people_names) if people_names and random.random() > 0.5 else ""
    return {"description": descs.get(tier, descs[1]), "affected_person": affected,
            "person_event": f"亲眼目睹了变化，之后几天都不愿靠近那里。" if affected else ""}


def mock_spread(original: str, target: str, people_names: list) -> dict:
    affected = random.choice(people_names) if people_names and random.random() > 0.5 else ""
    return {"description": f"那种迹象从{target}身上也出现了——没有人说得清为什么。",
            "affected_person": affected,
            "person_event": "感到一阵莫名的眩晕，随后平复。" if affected else ""}


def mock_birth() -> dict:
    names = ["瑟拉", "伊卡", "托玛", "奈尔", "苏迪", "维格", "阿尔", "依莱"]
    all_traits = ["安静", "好动", "敏感", "顽固", "温柔", "警觉", "沉稳", "冲动"]
    memories = ["对深处有一种说不清的向往，仿佛从未见过的地方在召唤。",
                "偶尔会哭泣，却找不到原因，就像在哀悼某个从未存在过的人。",
                "", "", ""]
    return {"name": random.choice(names), "traits": random.sample(all_traits, 2),
            "background": "出生在部落营地边，哭声响亮。",
            "parent1_traits": random.sample(all_traits, 2),
            "parent2_traits": random.sample(all_traits, 2),
            "inherited_memory": random.choice(memories)}


def mock_prayer_response(person_name: str, response_type: str) -> dict:
    responses = {
        "answer": {"narrative": f"在{person_name}跪倒祈祷的那一刻，风停了。然后，一只鸟落在了他面前，用奇怪的眼神盯着他看了很久。",
                   "population_change": 0, "faith_change_for_person": 20,
                   "event_for_person": "感到某种意志注视着自己，心中升起难以言说的敬畏。"},
        "ignore": {"narrative": f"{person_name}的祈祷消散在空气里，没有任何回应。",
                   "population_change": 0, "faith_change_for_person": -10,
                   "event_for_person": "等了很久，天空没有任何异动，心里空落落的。"},
        "punish": {"narrative": f"在{person_name}祈祷之后，地面震动了一下，他附近的几棵树同时枯萎。",
                   "population_change": -2, "faith_change_for_person": -30,
                   "event_for_person": "一股说不清的力量击中了胸口，好几天无法站立。"},
        "bless":  {"narrative": f"{person_name}祈祷后清晨，发现营地旁多了一处从未见过的泉眼，水清澈而温热。",
                   "population_change": 5, "faith_change_for_person": 40,
                   "event_for_person": "感到一种无形的温暖从顶部流下，此后数日精力充沛。"},
    }
    return responses.get(response_type, responses["ignore"])


def mock_divine_gaze(target_name: str, target_type: str) -> dict:
    if target_type == "person":
        return {
            "deep_vision": f"{target_name}的体内有什么东西在缓慢旋转——不是他们自己知道的东西。表面上看是普通人，但在某个更深的层次，他们的存在在周围空气里留下了轻微的纹路，像是有人用手指在水面划过，方向是确定的。",
            "hidden_truth": f"{target_name}在三年前亲眼目睹了某件无法解释的事，从未告诉任何人，这件事正在改变他们做梦的内容。",
        }
    return {
        "deep_vision": "这片地方的土地比周围其他地方厚三寸——不是因为土壤堆积，而是因为某些东西在缓慢凝结。站在这里的人，呼出的气在无风的日子会偏向同一个方向，但没有人注意到。",
        "hidden_truth": "这个地点曾经是另一种存在短暂休息的地方，那种存在离开时留下了还在慢慢消散的痕迹。",
    }


def mock_other_god() -> dict:
    events = [
        {"description": "最近几天，某个地区的动物开始向同一方向迁徙，没有任何明显原因。猎人们发现猎物消失了，老人们低声议论。",
         "affected_area": "东部森林", "faith_impact": -15,
         "narrative_for_npcs": "「动物都走了，」一个猎人说，「就像它们听到了我们听不见的声音。」"},
        {"description": "三个不同营地的人同时梦见相同的场景——一片黑色的平原，远处有什么东西在移动。",
         "affected_area": "中央聚落", "faith_impact": 10,
         "narrative_for_npcs": "「我也梦见了，」第二个人惊呼，「那个黑色的地方，和你说的一样。」"},
    ]
    return random.choice(events)
