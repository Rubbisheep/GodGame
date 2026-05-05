"""
世界涌现检测器。

每隔几回合分析当前世界状态，判断是否有新系统自然涌现。
如果是，调用 LLM 生成对应的 Python 模块代码并热加载它。
"""


# 每隔多少年检查一次涌现
CHECK_INTERVAL = 3

# 已知的可以涌现的系统（防止重复生成）
# 这个列表会在运行时动态扩展

# 给 LLM 的 API 文档（告诉它可以访问哪些对象）
_API_DOCS = """
可用的游戏对象（通过 state_manager 访问）：

state_manager.world (WorldState):
  .population: int
  .faith: int
  .world_year: int
  .current_era: str
  .tech_and_culture_tags: list[str]
  .tendency_vectors: dict[str, float]
  .active_mutations: list[Mutation]
  .calendar_name: str
  .apply_population_change(delta: int)
  .accumulate_tendency(tags: list[str])
  .summary() -> str

state_manager.pool (PopulationPool):
  .living: list[Person]
  .archived: list[Person]
  .get_by_name(name: str) -> Optional[Person]
  .random_living(n: int) -> list[Person]

Person:
  .name: str
  .traits: list[str]
  .background: str
  .birth_year: int
  .death_year: Optional[int]
  .life_events: list[LifeEvent]  (.year, .event_type, .description)
  .is_notable: bool
  .relationships: list[str]
  .add_event(year: int, event_type: str, description: str)
  .age(current_year: int) -> int
  .life_stage(current_year: int) -> str

state_manager.active_entities: list[SpecialEntity]
SpecialEntity:
  .name, .traits, .current_focus, .risk_level, .mutations
  .legacy_tags: list[str]

state_manager.loader (ModuleLoader):  # 其他已加载的模块
  .active_names() -> list[str]

可以在 register() 中给 state_manager 添加新属性，例如：
  state_manager.trade_routes = []

可以在 on_turn_end() 中调用 state_manager.world 的方法修改世界。
不要 import 标准库以外的第三方包。可以使用：random, json, math, collections, dataclasses
"""


class MetaSystem:
    def __init__(self):
        self._last_check_year = 0
        self._turn_log: list[str] = []  # 累积的回合事件，用于涌现分析

    def record_turn_events(self, events: list[str]):
        """把本回合发生的事记录下来，供涌现分析使用。"""
        self._turn_log.extend(events)
        # 只保留最近 50 条
        if len(self._turn_log) > 50:
            self._turn_log = self._turn_log[-50:]

    def should_check(self, current_year: int) -> bool:
        return (current_year - self._last_check_year) >= CHECK_INTERVAL

    def check_and_generate(self, state_manager, loader) -> list[str]:
        """
        分析世界状态，如有必要生成新模块。
        返回给玩家的通知消息。
        """
        from llm_interface import check_emergence, generate_module_code

        self._last_check_year = state_manager.world.world_year
        notices = []

        # 询问 LLM：世界当前需要新系统吗？
        existing = loader.active_names() + loader.broken_names()
        emergence = check_emergence(
            world_state=state_manager.world,
            pool=state_manager.pool,
            active_entities=state_manager.active_entities,
            recent_events=self._turn_log,
            existing_modules=existing,
        )

        if not emergence.get("should_generate"):
            return []

        reason = emergence.get("reason", "")
        module_name = emergence.get("module_name", "")
        module_hint = emergence.get("hint", "")

        if not module_name or loader.is_loaded(module_name):
            return []

        # LLM 生成模块代码
        code = generate_module_code(
            module_name=module_name,
            reason=reason,
            hint=module_hint,
            world_state=state_manager.world,
            pool=state_manager.pool,
            api_docs=_API_DOCS,
        )

        ok, err = loader.load(module_name, code, state_manager)

        if ok:
            desc = getattr(
                __import__("types").ModuleType,  # trick to get mod description
                "MODULE_DESCRIPTION", ""
            )
            # 从磁盘读回模块描述
            from pathlib import Path
            mod_file = Path(__file__).parent / "modules" / f"{module_name}.py"
            mod_desc = ""
            if mod_file.exists():
                for line in mod_file.read_text(encoding="utf-8").splitlines():
                    if "MODULE_DESCRIPTION" in line and "=" in line:
                        mod_desc = line.split("=", 1)[1].strip().strip('"\'')
                        break
            notices.append(
                f"\n  [世界涌现] 一个新的秩序在世界中成形。\n"
                f"    {mod_desc or reason}"
            )
        else:
            # 初次就加载失败，直接进热修复流程（_handle_crash 已在 loader.load 内触发）
            pass

        return notices

    def process_fix_results(self, fix_results: list, state_manager, loader) -> list[str]:
        """
        把 loader.check_pending_fixes() 的结果转成叙事消息。
        """
        from llm_interface import get_fix_narrative, get_error_narrative

        notices = []
        for success, module_name, err in fix_results:
            if success:
                narrative = get_fix_narrative(module_name, state_manager.world, state_manager.pool)
                notices.append(f"\n  [世界修复] {narrative}")
            else:
                # 仍然失败，给个简短提示，不打扰游戏
                notices.append(f"\n  [织体异常延续] {module_name} 系统的裂缝仍未弥合。")
        return notices
