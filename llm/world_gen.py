"""初始世界生成：人口、出生、特殊实体。"""
import json
import random
from .client import call, safe_json, USE_MOCK
from .bible import WORLD_BIBLE
from .schemas import INIT_POPULATION, ENTITY, BIRTH
from .schemas import mock_init_people, mock_entity, mock_birth


def generate_initial_population(world_state, count: int = 10) -> dict:
    if USE_MOCK:
        return mock_init_people()
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{INIT_POPULATION}"
    user = (
        f"世界初始状态：{world_state.summary()}\n\n"
        f"为一个石器时代的狩猎采集小部落生成 {count} 个核心成员。"
        "他们约30人，住在河边，靠狩猎和采集为生，没有任何文字或组织化宗教。"
        "必须包含：至少1名长老（elder）、至少2名少年或儿童（youth/child）、其余为成年人（adult）。"
        "其中有一名长老天生对某些无法解释的现象格外敏感——他不知道原因，只是习惯性地对空气和水低语。"
        "名字完全虚构，有异域质感，与任何现实语言无关。"
        "背景要具体真实，体现石器时代的生活细节。返回 JSON。"
    )
    return json.loads(call(system, user, max_tokens=1200))


def generate_new_entity(world_state) -> dict:
    if USE_MOCK:
        return mock_entity(world_state.current_era)
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{ENTITY}"
    user = f"世界状态：\n{world_state.summary()}\n\n生成一位悄然崛起的特殊个体。返回 JSON。"
    return json.loads(call(system, user, max_tokens=256))


def generate_birth(world_state, population_pool) -> dict:
    if USE_MOCK:
        return mock_birth()
    parents = random.sample(population_pool.living, min(2, len(population_pool.living)))
    parent_lines = [f"{p.name}（{'、'.join(p.traits)}）：{p.background}" for p in parents]
    system = WORLD_BIBLE + f"\n\n只返回如下 JSON，不加任何其他文字：\n{BIRTH}"
    user = (
        f"世界状态：\n{world_state.summary()}\n"
        f"父母信息：\n" + "\n".join(parent_lines) + "\n\n"
        "生成一个刚出生的孩子。inherited_memory 只有当父母有特别值得传承的东西时才填写，否则空字符串。返回 JSON。"
    )
    try:
        return json.loads(call(system, user, max_tokens=250))
    except Exception:
        return {"name": "未命名", "traits": ["安静"], "background": "出生于普通家庭",
                "parent1_traits": [], "parent2_traits": [], "inherited_memory": ""}
