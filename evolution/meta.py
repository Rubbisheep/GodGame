"""
世界涌现检测器。
每隔 CHECK_INTERVAL 年分析世界状态，判断是否有新系统自然涌现并自动生成模块。
"""
from pathlib import Path

CHECK_INTERVAL = 3


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
        existing = loader.active_names() + loader.broken_names()

        emergence = check_emergence(
            world_state=state_manager.world,
            pool=state_manager.pool,
            recent_events=self._turn_log,
            existing_modules=existing,
        )
        if not emergence.get("should_generate"):
            return []

        reason = emergence.get("reason", "")
        module_name = emergence.get("module_name", "")
        hint = emergence.get("hint", "")

        if not module_name or loader.is_loaded(module_name):
            return []

        code = generate_module_code(
            module_name=module_name, reason=reason, hint=hint,
            world_state=state_manager.world, pool=state_manager.pool,
            api_docs=MODULE_API_DOCS,
        )
        ok, _ = loader.load(module_name, code, state_manager)

        if ok:
            mod_file = Path(__file__).parent.parent / "modules" / f"{module_name}.py"
            mod_desc = ""
            if mod_file.exists():
                for line in mod_file.read_text(encoding="utf-8").splitlines():
                    if "MODULE_DESCRIPTION" in line and "=" in line:
                        mod_desc = line.split("=", 1)[1].strip().strip('"\'')
                        break
            return [f"\n  [世界涌现] 一个新的秩序在世界中成形。\n    {mod_desc or reason}"]
        return []
