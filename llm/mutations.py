"""变异描述生成：创建新变异 + 扩散描述。"""
import json
from .client import call, USE_MOCK
from .bible import WORLD_BIBLE
from .schemas import MUTATION, SPREAD, mock_mutation, mock_spread


def generate_mutation_description(tier: int, target_type: str, target_name: str,
                                   tendencies: list, world_summary: str,
                                   era: str, people_names: list) -> dict:
    if USE_MOCK:
        return mock_mutation(tier, target_name, people_names)

    tier_desc = {1: "表层（外观/习惯改变）", 2: "功能（能力/行为改变）", 3: "本质（存在形态改变，极其诡异）"}
    names_hint = f"当前可以被影响的命名居民：{', '.join(people_names[:15])}" if people_names else ""
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{MUTATION}"
    user = (
        f"世界状态：\n{world_summary}\n\n"
        f"变异烈度：{tier_desc[tier]}\n"
        f"变异目标：{target_name}（类型：{target_type}）\n"
        f"当前世界倾向：{', '.join(tendencies) or '无'}\n"
        f"{names_hint}\n"
        "生成变异描述。如果变异影响了某个命名居民，在affected_person填写其名字。返回 JSON。"
    )
    return json.loads(call(system, user, max_tokens=250))


def generate_spread_description(original_mutation: str, spread_target: str,
                                  tier: int, era: str, people_names: list) -> dict:
    if USE_MOCK:
        return mock_spread(original_mutation, spread_target, people_names)

    names_hint = f"可能被影响的命名居民：{', '.join(people_names[:10])}" if people_names else ""
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{SPREAD}"
    user = (
        f"原始变异：{original_mutation}\n"
        f"扩散至：{spread_target}\n"
        f"{names_hint}\n返回 JSON。"
    )
    return json.loads(call(system, user, max_tokens=200))
