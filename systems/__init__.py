"""
世界 tick 系统注册表。
每个系统暴露 tick(sm) -> list[str] 函数，由 StateManager.end_of_turn() 依序调用。
新增系统只需在此导入并追加到 SYSTEMS 列表。
"""
from . import population_tick, mutation_tick, entity_tick, divinity_tick

SYSTEMS = [
    entity_tick,
    population_tick,
    mutation_tick,
    divinity_tick,
]
