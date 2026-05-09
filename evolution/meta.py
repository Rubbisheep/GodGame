"""
世界涌现检测器。
每隔 CHECK_INTERVAL 年分析世界状态，判断是否有新系统自然涌现并自动生成模块。

基础物理（FOUNDATIONAL_MODULES）由内核保证在场：每次涌现检查时若缺失就自动生成，
不走 LLM 判定。LLM 只负责具体形态和参数，不决定"要不要有"。
其他一切（社会、文化、超自然……）照旧靠 LLM 读事件信号自行涌现。

涌现行为对玩家完全静默——模块的存在通过它产出的世界事件被玩家感受到，
而不是通过 [世界涌现] 这种元层通告。"系统/模块"是开发者概念，不暴露给玩家。
"""

CHECK_INTERVAL = 3            # 检查间隔：每 N 年一次涌现机会（实际是否生成由 LLM 判断）
MIN_FIRST_CHECK_YEAR = 20     # 婴儿期保护：前 N 年完全不检查涌现，给世界冷启动呼吸空间。
                              # 没有节流伞，但有一段无涌现的"原初混沌"——世界刚意识到自己存在，
                              # 连火都未稳定，先让它静一会儿。20 年后才进入正常涌现节奏。

# ── 基础物理：内核保证在场的模块 ─────────────────────────────────────────────
# 这些不是"可能涌现"的东西，是世界本身就该有的底层物理。
# 类似现实中的重力和天气——不需要"等社会积累"才出现。
# 每次涌现检查时，若 name 不在 active+broken 列表里，就重新生成一次。
FOUNDATIONAL_MODULES = {
    "mutation_system": {
        "reason": "世界的基础物理之一：无形的意识场在有形物质上留下印记。"
                  "这不是偶然事件，而是世界始终在发生的背景过程。",
        "hint": "追踪三级变异：(1)表层——视觉/触感的细微扭曲；(2)功能——被影响者做出异常行为或获得异常能力；"
                "(3)本质——被影响者开始接收来自世界深处的信号，常被误解为神明低语。"
                "变异可以发生在人、物、地形、乃至事件上。可扩散到邻近目标。"
                "低频但稳定：每回合有小概率产生新变异、或让已有变异扩散/升级。"
                "产出事件文本要感官化（『叶子在无风时同步颤动』而非『触发mutation事件』），"
                "不使用『息/凝质/Veth/Sang』等底层术语。",
    },
}


class MetaSystem:
    def __init__(self):
        self._last_check_year = 0
        self._turn_log: list[str] = []
        self._last_emergence_year = 0  # 最近一次有新模块成形的年份（基础物理不计）

    def record_turn_events(self, events: list[str]):
        self._turn_log.extend(events)
        if len(self._turn_log) > 50:
            self._turn_log = self._turn_log[-50:]

    def should_check(self, current_year: int) -> bool:
        if current_year < MIN_FIRST_CHECK_YEAR:
            return False
        return (current_year - self._last_check_year) >= CHECK_INTERVAL

    def check_and_generate(self, state_manager, loader) -> list[str]:
        """涌现检查：基础物理补缺 + LLM 判断有机涌现。
        总是返回 []——玩家不该看到"系统涌现"这种元层概念。
        模块的存在通过它产出的世界事件被玩家感受到，不通过通告。
        """
        from llm import check_emergence, generate_module_code, MODULE_API_DOCS

        self._last_check_year = state_manager.world.world_year
        existing = set(loader.active_names() + loader.broken_names())

        # ── 基础物理：缺失就补上（静默） ────────────────────────────────
        for name, info in FOUNDATIONAL_MODULES.items():
            if name in existing:
                continue
            code = generate_module_code(
                module_name=name, reason=info["reason"], hint=info["hint"],
                world_state=state_manager.world, pool=state_manager.pool,
                api_docs=MODULE_API_DOCS,
            )
            loader.load(name, code, state_manager)
            existing.add(name)

        # ── 有机涌现：把现有模块的「名字 + 描述」一起喂给 LLM 帮助去重 ──
        existing_with_desc = {
            n: loader.get_description(n) or "(描述缺失)"
            for n in existing
        }

        emergence = check_emergence(
            world_state=state_manager.world,
            pool=state_manager.pool,
            recent_events=self._turn_log,
            existing_modules_with_desc=existing_with_desc,
            years_since_last_emergence=(
                state_manager.world.world_year - self._last_emergence_year
            ),
        )
        if not emergence.get("should_generate"):
            return []

        reason = emergence.get("reason", "")
        module_name = emergence.get("module_name", "")
        hint = emergence.get("hint", "")
        subtle = bool(emergence.get("subtle", False))

        # LLM 不得覆盖基础物理（即使它忘了约束尝试重生成）
        if (not module_name or module_name in existing
                or module_name in FOUNDATIONAL_MODULES):
            return []

        code = generate_module_code(
            module_name=module_name, reason=reason, hint=hint,
            world_state=state_manager.world, pool=state_manager.pool,
            api_docs=MODULE_API_DOCS, subtle=subtle,
        )
        ok, _ = loader.load(module_name, code, state_manager)
        if ok and not subtle:
            # 伏笔不计冷却。显形的也不通告，但要计冷却防止短期内连续显形
            self._last_emergence_year = state_manager.world.world_year
        return []
