"""
世界涌现检测器。
每隔 CHECK_INTERVAL 年分析世界状态，判断是否有新系统自然涌现并自动生成模块。

基础物理（FOUNDATIONAL_MODULES）由内核保证在场：每次涌现检查时若缺失就自动生成，
不走 LLM 判定。LLM 只负责具体形态和参数，不决定"要不要有"。
其他一切（社会、文化、超自然……）照旧靠 LLM 读事件信号自行涌现。
"""
from pathlib import Path

CHECK_INTERVAL = 12  # 涌现节流：每 12 年检查一次有机模块涌现，让世界有时间消化已有概念

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

    def record_turn_events(self, events: list[str]):
        self._turn_log.extend(events)
        if len(self._turn_log) > 50:
            self._turn_log = self._turn_log[-50:]

    def should_check(self, current_year: int) -> bool:
        return (current_year - self._last_check_year) >= CHECK_INTERVAL

    def check_and_generate(self, state_manager, loader) -> list[str]:
        from llm import check_emergence, generate_module_code, MODULE_API_DOCS

        self._last_check_year = state_manager.world.world_year
        existing = set(loader.active_names() + loader.broken_names())
        notices: list[str] = []

        # ── 基础物理：缺失就补上 ─────────────────────────────────────────
        for name, info in FOUNDATIONAL_MODULES.items():
            if name in existing:
                continue
            code = generate_module_code(
                module_name=name, reason=info["reason"], hint=info["hint"],
                world_state=state_manager.world, pool=state_manager.pool,
                api_docs=MODULE_API_DOCS,
            )
            ok, _ = loader.load(name, code, state_manager)
            existing.add(name)
            if ok:
                notices.append(_describe_new_module(name, info["reason"]))

        # ── 有机涌现：LLM 读事件判断 ─────────────────────────────────────
        emergence = check_emergence(
            world_state=state_manager.world,
            pool=state_manager.pool,
            recent_events=self._turn_log,
            existing_modules=list(existing),
        )
        if not emergence.get("should_generate"):
            return notices

        reason = emergence.get("reason", "")
        module_name = emergence.get("module_name", "")
        hint = emergence.get("hint", "")

        # LLM 不得覆盖基础物理（即使它忘了约束尝试重生成）
        if (not module_name or module_name in existing
                or module_name in FOUNDATIONAL_MODULES):
            return notices

        code = generate_module_code(
            module_name=module_name, reason=reason, hint=hint,
            world_state=state_manager.world, pool=state_manager.pool,
            api_docs=MODULE_API_DOCS,
        )
        ok, _ = loader.load(module_name, code, state_manager)
        if ok:
            notices.append(_describe_new_module(module_name, reason))
        return notices


def _describe_new_module(module_name: str, fallback_reason: str) -> str:
    mod_file = Path(__file__).parent.parent / "modules" / f"{module_name}.py"
    mod_desc = ""
    if mod_file.exists():
        for line in mod_file.read_text(encoding="utf-8").splitlines():
            if "MODULE_DESCRIPTION" in line and "=" in line:
                mod_desc = line.split("=", 1)[1].strip().strip('"\'')
                break
    return f"\n  [世界涌现] 一个新的秩序在世界中成形。\n    {mod_desc or fallback_reason}"
