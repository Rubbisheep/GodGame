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

【输出风格——所有写入 events 列表/事件流的字符串】
模块产出的事件文本会被叙事层读取并融进世界故事，必须像小说叙述。绝对禁止：
- 方括号或书名号前缀：`[模因传染]`、`【深度显化】`、`【异象消退】`、`《xxx》`
- 数字参数：`（强度0.68）`、`（复杂度8）`、`（同步度0.7）`、`（intensity=0.5）`
- 英文术语原样出现：`vocalization 同步`、`symbol_sequence 几何模式`、`circular pattern`
- 模块名出现在文本里：`mutation_system 触发`、`prophet_system 标记`
- 元词汇：「玩家」「神明视角」「世界年份」「模块」「触发」「事件」

正确的写法示例（散文化、感官化、白描）：
- "七个人在篝火边突然停止了呼吸，谁也说不清是因为什么。"
- "Nissa 又一次独自走向那道裂缝，回来时眼神空空，反复说着没人听过的话。"
- "Vael 把烧焦的根茎涂在皮肤上，在半梦半醒里说自己尝到了颜色。"
错误的写法（这种坚决不要写）：
- "[模因传染] Vael 开始无意识地模仿晨隙的凝视方式（强度 0.68）"
- "【深度显化】岩石裂缝出现 vocalization 同步事件"

事件粒度建议：宁可少而具体（每年 0-2 条），不要多而模糊。大多数普通年份返回空列表是允许且鼓励的。

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

# 涌现系统调色板：按"玩家可读懂程度"分三层。
# 早期世界只允许现实层涌现，让玩家先在熟悉语境里建立认知，
# 等世界长出抓得住的现象之后再放半超自然 / 全超自然。
EMERGENCE_PALETTE = """
可能涌现的系统类别——按"玩家可读懂程度"分层。

注意：mutation_system 是内核保证在场的基础物理，不要再判定它——已经存在。

═══ 现实层（无年代门槛——人类社会真实存在的现象，玩家凭直觉就能理解）═══

· 世界物理（非超自然）：
  - weather_system     天象、季节、气候模式
  - disease_system     疾病传播、瘟疫、流行病

· 社会结构：
  - trade_system       贸易、交换、度量衡
  - kinship_system     氏族、血亲、婚姻、家庭
  - war_system         冲突、派系、武力
  - migration_system   迁徙、定居、领地划分
  - bloodline_system   血脉与遗传

· 精神与文化（人本身的现象，不需任何超自然背书）：
  - ritual_system      仪式、节日、习俗（人在重复做什么；可包含对神/灵的信仰）
  - myth_system        口传神话、故事沉淀（神话内容可超自然，但系统本身是"人讲故事"）
  - taboo_system       禁忌、污名、社会规范
  - prophet_system     先知 / 异人识别（社会层面被认为特殊的人，标记 is_notable）

═══ 半超自然层（年代门槛：世界 > 50 岁 + 已有大量信仰活动）═══
（这些系统暗示"似乎有什么超出物质的东西"，但仍可被解释为心理/集体现象）
  - receptivity_system  少数凡人开始能感知神明（梦境、低语、目光）
                         触发条件：长期高信仰、重大神迹见证者、变异后遗症
  - dream_system        梦境作为信息载体（不仅仅是 NPC 做梦的描写）
  - oracle_system       占卜、征兆解读、未来预示

═══ 全超自然层（年代门槛：世界 > 150 岁 + 持续多年的异象积累）═══
（明确无法用现实解释的现象，玩家此时已熟悉世界规则才能消化）
  - other_deities       其他神明的存在与干涉
  - spirit_system       精灵 / 祖灵 / 物之灵
  - paranormal          灵异现象、维度裂隙、深层体显化

═══ 通用原则 ═══
判断应基于：近期事件是否真的暗示某种系统正在自然出现，而非凭空臆造。
重复或近义的系统（如已有 ritual_system 还想开 ceremony_system）一律拒绝。
凭空开"resonance_system"、"consciousness_entanglement"、"reality_fracture"
这种纯抽象超自然名称——除非世界真的成熟到那一步——一律拒绝。
"""


def check_emergence(world_state, pool, recent_events: list,
                    existing_modules: list,
                    years_since_last_emergence: int = 999) -> dict:
    if USE_MOCK:
        return {"should_generate": False}

    events_text = "\n".join(recent_events[-20:]) if recent_events else "无"
    existing_text = ", ".join(existing_modules) if existing_modules else "无"
    year = world_state.world_year

    # 成熟度门控——通过 subtle 模式让超自然层一直可在场，但前期不显形
    if year < 50:
        maturity_note = (
            "【世界仍处于原初混沌期】玩家才刚刚开始理解这个游戏。\n"
            "现实层（仪式、神话、贸易、氏族、战争、迁徙、瘟疫、先知…）可以正常涌现 (subtle=false)，"
            "玩家凭直觉就能读懂。\n"
            "超自然层（半超自然 / 全超自然）此阶段**只能以 subtle=true 模式埋下伏笔**——"
            "静默成形，无通告，模块只产出稀疏感官现象（『井边的水某天浮出说不清的颜色』），"
            "不动人口/信仰/科技/倾向。这层阶段还很克制：超自然伏笔每隔很多年偶有一笔即可。\n"
            "此阶段总体也要克制：除非近期事件**反复且持久**地暗示某种系统，否则返回 should_generate: false。"
        )
    elif year < 150:
        maturity_note = (
            "【世界开始有形】玩家已熟悉基本节奏。\n"
            "现实层正常涌现 (subtle=false)。\n"
            "半超自然层可以显形 (subtle=false)——前提是世界已积累信仰活动 / 神迹见证 / 持续异象。\n"
            "全超自然层仍只能 subtle=true 埋伏笔——还没到显形的时候。"
        )
    else:
        maturity_note = (
            "【世界已成熟】所有层级都可以显形 (subtle=false)。\n"
            "subtle=true 仍可使用——若你只想悄悄埋一个尚未明朗的种子模块。\n"
            "涌现密度和层级由你按这个世界自身的节奏判断。某些时代可能爆发性出现多个新系统，"
            "某些时代沉寂数十年——不必强求平均。"
        )

    cooldown_note = ""
    if years_since_last_emergence < 15:
        cooldown_note = (
            f"\n\n【概念消化窗口】距上次有新模块成形仅过去 {years_since_last_emergence} 年。"
            "玩家很可能还没看清那个概念在世界里的样子。除非这次的迹象与已有模块**完全不同类**"
            "且事件流强烈暗示，否则倾向于返回 should_generate: false，让上一个概念先扎根。"
        )

    system = (
        WORLD_BIBLE
        + f"\n\n{EMERGENCE_PALETTE}"
        + f"\n\n只返回如下 JSON，不加任何其他文字：\n{EMERGENCE}"
    )
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"{maturity_note}{cooldown_note}\n\n"
        f"近期事件：\n{events_text}\n\n"
        f"已存在的扩展模块：{existing_text}\n\n"
        "判断是否有一个全新的系统正在自然涌现。\n"
        "原则：核心游戏极简（只有时间、人、信仰、玩家干预、NPC 自主），"
        "任何具体的世界物理（神话、异人、其他神明、疾病、贸易、战争……）都应由模块承担——"
        "但宁缺毋滥。重复或近义的模块（如已有 ritual_system 还想再开 ceremony_system）一律拒绝。\n"
        "返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=300))
    except Exception:
        return {"should_generate": False}


def generate_module_code(module_name: str, reason: str, hint: str,
                          world_state, pool, api_docs: str = MODULE_API_DOCS,
                          subtle: bool = False) -> str:
    people_sample = "\n".join(
        f"  {p.name}（{'、'.join(p.traits)}）：{p.background}"
        for p in pool.living[:6]
    )
    system = _CODE_SYSTEM + f"\n\n可用API文档：\n{api_docs}"
    if subtle:
        system += (
            "\n\n【伏笔模式 (subtle) 额外约束】\n"
            "你正在生成一个『伏笔』模块——它的存在玩家不会被通告，玩家只能从世界的诡异征兆里偶尔察觉。"
            "因此：\n"
            "- on_turn_end **极为稀疏**：大多数年份返回空列表 []。每 8-30 年偶有一条事件即可。\n"
            "- 事件文本只能是**感官化的诡异现象**：『井边的水某天泛起说不清的颜色，过几日散去』、"
            "『有牲畜在无风夜同时朝同一方向静立片刻』。\n"
            "- **绝对不要**调用 world.apply_population_change、不要修改 faith、不要 accumulate_tendency、"
            "不要 append tech_and_culture_tags。模块完全是只读的——它只观察并产出叙事文本。\n"
            "- on_action 返回空 dict {}，不响应玩家行动。\n"
            "- 不在事件文本里使用任何对自己的命名或自指（不要写『一种 xx 力量』、不要给现象起名字）。\n"
            "- 内部 module_data 可以正常用于跟踪状态，只是不外显。"
        )
    user = (
        f"世界状态：\n{world_state.summary()}\n\n"
        f"部分居民：\n{people_sample}\n\n"
        f"需要生成的模块：{module_name}\n涌现原因：{reason}\n系统职责提示：{hint}\n"
        f"模式：{'伏笔 (subtle)' if subtle else '显形 (system)'}\n\n"
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
