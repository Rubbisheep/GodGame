"""LLM 代码生成：新模块生成、模块修复、模块升级、叙事反馈。"""
import json
from .client import call, safe_json, get_client, strip_code_fences, USE_MOCK, MODEL_CODE
from .bible import WORLD_BIBLE
from .schemas import EMERGENCE, ERROR_NARRATIVE, FIX_NARRATIVE

_CODE_SYSTEM = """你是一位游戏系统工程师，正在为《无名之界》维护和改进Python游戏模块。
这些模块在游戏运行时被热加载，扩展和追踪游戏世界的各种系统。

【生成新模块的规则】
1. 模块必须是完整可运行的Python代码
2. 只能使用标准库（random, json, math, collections, dataclasses等），不能import第三方库
3. 不能直接import游戏内的其他模块，通过传入的state_manager参数访问游戏状态
4. 必须定义以下顶层变量和函数：
   MODULE_NAME = "snake_case名称"
   MODULE_DESCRIPTION = "一句话描述"
   EMERGENCE_REASON = "世界中什么迹象触发了这个模块"

   def register(state_manager): ...
   def on_turn_end(state_manager) -> list[str]: ...
   def on_action(state_manager, action_type: str, subject: str) -> dict: ...

【升级已有模块的规则】
- 保留原有MODULE_NAME、MODULE_DESCRIPTION、register函数签名
- 可以扩展数据结构，但要保持向后兼容（用.get()读取可能不存在的旧字段）
- 改进的逻辑应基于NPC的提案，让系统变得更真实、更有深度
- 不要删除现有功能，只添加和改进

【保持紧凑】
- 控制在 150-250 行以内。短小、专注、完整 > 雄心勃勃但被截断。
- 数据结构不要过度设计：用 dict 就够的地方不要上 dataclass。
- on_turn_end 和 on_action 里每个逻辑分支都要真的闭合——宁可功能少，也不要任何一条 if/for 挂在空气里。
- 最后一行必须是有效的 Python 代码或空行，不要停在字符串字面量、未完成的表达式中。

5. 直接输出Python代码，不要加```包裹，不要解释
"""

# 给 LLM 生成的模块看的 API 文档
MODULE_API_DOCS = """
可用的游戏对象（通过 state_manager 访问）：

state_manager.world (WorldState):
  .population: int          # 总人口
  .faith: int               # 神力（神明的资源）
  .world_year: int          # 当前年份
  .current_era: str         # 当前时代名
  .tech_and_culture_tags: list[str]
  .tendency_vectors: dict[str, float]
  .apply_population_change(delta: int)
  .accumulate_tendency(tags: list[str])
  .summary() -> str

state_manager.pool (PopulationPool):
  .living: list[Person]
  .archived: list[Person]
  .get_by_name(name: str) -> Optional[Person]
  .random_living(n: int) -> list[Person]

Person:
  .name: str  .traits: list[str]  .background: str
  .birth_year: int  .death_year: Optional[int]
  .life_events: list[LifeEvent]  (.year, .event_type, .description)
  .faith_in_god: float  .prayer_pending: str
  .is_notable: bool
  .add_event(year: int, event_type: str, description: str)
  .age(current_year: int) -> int
  .life_stage(current_year: int) -> str

state_manager.module_data[MODULE_NAME] -> dict  # 模块持久化存储（register中初始化）
state_manager.add_event(text: str)              # 向事件日志追加
state_manager.request_upgrade(module_name, proposal, proposer)  # 请求升级

模块是纯叠加性的：可以读所有状态、添加事件、修改 module_data 和调用 state_manager 的公开方法，
但不要替换或覆盖核心 tick 逻辑（人口老化/出生/祈祷、NPC 自主行为）。核心只负责「世界的最小物理」，
其余一切 —— 变异、神话、异人识别、贸易、战争、瘟疫、仪式、其他神明…… —— 都由你们这些模块承担。
"""

# 涌现系统调色板：供 emergence 判定和模块命名时参考
EMERGENCE_PALETTE = """
可能涌现的系统类别（仅作参考，不限于此）：

注意：mutation_system 是内核保证在场的基础物理，不要再判定它——已经存在。
其他系统才走涌现逻辑。

· 世界物理（非基础）：
  - weather_system   天象与季节
  - disease_system   疾病与瘟疫传播

· 生命与个体：
  - prophet_system     先知 / 异人识别（标记 is_notable）
  - receptivity_system 少数凡人开始能感知神明的存在（梦境、低语、目光），
                        为玩家重新打开「向某人传话」的通道——但必须是世界长出来的能力，
                        不是内置权限。触发条件通常是：长期高信仰、重大神迹见证者、
                        或某种变异留下的后遗症。
  - bloodline_system   血脉与遗传
  - dream_system       梦境与预兆

· 社会结构：
  - trade_system     贸易、交换、度量衡
  - kinship_system   氏族、血亲、婚姻
  - war_system       冲突、派系、武力
  - migration_system 迁徙与定居

· 精神与文化：
  - myth_system      口传神话与故事沉淀
  - ritual_system    宗教仪式、节日、禁忌
  - oracle_system    占卜、征兆解读
  - taboo_system     禁忌与污名

· 超自然：
  - other_deities    其他神明的存在与干涉
  - spirit_system    精灵 / 祖灵 / 物之灵
  - paranormal       灵异现象、维度裂隙

判断应基于：近期事件是否真的暗示某种系统正在自然出现，而非凭空臆造。
"""


def check_emergence(world_state, pool, recent_events: list,
                    existing_modules: list) -> dict:
    if USE_MOCK:
        return {"should_generate": False}

    events_text = "\n".join(recent_events[-20:]) if recent_events else "无"
    existing_text = ", ".join(existing_modules) if existing_modules else "无"
    system = (
        WORLD_BIBLE
        + f"\n\n{EMERGENCE_PALETTE}"
        + f"\n\n只返回如下 JSON，不加任何其他文字：\n{EMERGENCE}"
    )
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"近期事件：\n{events_text}\n\n"
        f"已存在的扩展模块：{existing_text}\n\n"
        "判断是否有一个全新的系统正在自然涌现。\n"
        "注意：核心游戏极简（只有时间、人、信仰、玩家干预、NPC 自主），"
        "任何具体的世界物理（变异、神话、异人、其他神明、疾病、贸易、战争……）都应由模块承担。\n"
        "只有当近期事件真的暗示某类系统正在出现时才生成。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=300))
    except Exception:
        return {"should_generate": False}


def generate_module_code(module_name: str, reason: str, hint: str,
                          world_state, pool, api_docs: str = MODULE_API_DOCS) -> str:
    people_sample = "\n".join(
        f"  {p.name}（{'、'.join(p.traits)}）：{p.background}"
        for p in pool.living[:6]
    )
    system = _CODE_SYSTEM + f"\n\n可用API文档：\n{api_docs}"
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"部分居民：\n{people_sample}\n\n"
        f"需要生成的模块：{module_name}\n涌现原因：{reason}\n系统职责提示：{hint}\n\n"
        "编写这个Python模块。直接输出代码，不要任何包裹或解释。"
    )
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL_CODE, max_tokens=5000,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    return strip_code_fences(resp.choices[0].message.content)


def fix_module_code(module_name: str, broken_code: str, error: str) -> str:
    system = _CODE_SYSTEM + "\n你的任务是修复一段有bug的Python游戏模块代码。直接输出修复后的完整代码，不要任何包裹或解释。"
    user = f"模块名：{module_name}\n\n错误信息：\n{error}\n\n有bug的代码：\n{broken_code}\n\n输出修复后的完整代码。"
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL_CODE, max_tokens=5000,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    return strip_code_fences(resp.choices[0].message.content)


def upgrade_module_code(module_name: str, old_code: str, reason: str,
                         proposer: str, world_state=None, pool=None) -> str:
    people_sample = ""
    if pool:
        people_sample = "\n".join(
            f"  {p.name}（{'、'.join(p.traits)}）：{p.background}"
            for p in pool.living[:6]
        )
    system = _CODE_SYSTEM + f"\n\n可用API文档：\n{MODULE_API_DOCS}"
    world_info = world_state.summary() if world_state else "（不可用）"
    user = (
        f"世界状态：\n{world_info}\n\n"
        + (f"部分居民：\n{people_sample}\n\n" if people_sample else "")
        + f"需要升级的模块：{module_name}\n提案人：{proposer}\n升级原因：{reason}\n\n"
        f"现有代码：\n{old_code}\n\n"
        "根据提案内容改进这个模块。保留原有功能，增加新能力。直接输出完整的改进后代码。"
    )
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL_CODE, max_tokens=6000,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    return strip_code_fences(resp.choices[0].message.content)


def get_error_narrative(module_name: str, error: str, world_state, pool) -> dict:
    if USE_MOCK:
        return {"narrative": "世界的某处发出了低沉的震颤，像是什么东西崩断了。",
                "npc_reaction": "一位长者停下脚步，皱起眉头：「有什么东西不见了。」"}
    npc = pool.random_living(1)
    npc_name = npc[0].name if npc else "一位老人"
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{ERROR_NARRATIVE}"
    user = (
        f"世界年份：{world_state.year_display()}\n崩溃的系统：{module_name}\n"
        f"技术错误（仅供参考，不要提及）：{error[:200]}\n可以引用的NPC：{npc_name}\n\n"
        "描述这个世界层面的异常事件。不要提及代码、系统、模块等词。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=200))
    except Exception:
        return {"narrative": "世界的法则出现了短暂的撕裂。", "npc_reaction": ""}


def get_fix_narrative(module_name: str, world_state, pool) -> str:
    if USE_MOCK:
        return "秩序悄悄回归，像什么都没发生过一样。"
    npc = pool.random_living(1)
    npc_name = npc[0].name if npc else "一位居民"
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{FIX_NARRATIVE}"
    user = (
        f"世界年份：{world_state.year_display()}\n恢复的系统：{module_name}\n可以引用的NPC：{npc_name}\n\n"
        "描述世界异常恢复正常了。从居民视角，感官性。返回 JSON。"
    )
    try:
        result = json.loads(call(system, user, max_tokens=150))
        npc_r = result.get("npc_name", "")
        narrative = result.get("narrative", "")
        return f"{narrative}（{npc_r}注意到了这一点）" if npc_r else narrative
    except Exception:
        return "某种平衡悄然恢复了。"


def get_upgrade_narrative(module_name: str, proposer: str, world_state, pool) -> str:
    if USE_MOCK:
        return f"{proposer}的想法在人群中流传开来，不知不觉间，事情开始有了新的秩序。"
    npc = pool.random_living(1)
    npc_name = npc[0].name if npc else proposer
    system = WORLD_BIBLE + "\n\n只返回一段不超过60字的叙事文字，感官性，描述某种新秩序在世界中成形。不要提及代码或模块。"
    user = (
        f"世界年份：{world_state.year_display()}\n提案人：{proposer}\n"
        f"改变的系统（内部名称，不要直接提及）：{module_name}\n"
        f"叙事中可以提及的另一个NPC：{npc_name}\n\n"
        f"{proposer}提出的某种新方法开始被更多人接受，描述这种变化对世界的感官影响。"
    )
    try:
        raw = call(system, user, max_tokens=120).strip().strip('"')
        return raw
    except Exception:
        return f"{proposer}的想法悄悄改变了人们做事的方式。"
