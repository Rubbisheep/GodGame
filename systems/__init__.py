"""
世界 tick 系统注册表。
每个系统暴露 tick(sm) -> list[str] 函数，由 StateManager.end_of_turn() 依序调用。
新增系统只需在此导入并追加到 SYSTEMS 列表；大部分新系统应由 LLM 通过模块涌现自行产生。
"""
from . import population_tick, autonomy_tick

SYSTEMS = [
    population_tick,
    autonomy_tick,
]
