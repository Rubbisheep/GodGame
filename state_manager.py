"""
GameState 管理器 — 协调所有子系统。

新增功能：
- event_log: 近50条事件文本，供模块和 meta 系统读取
- module_data: 模块持久化存储
- request_upgrade(): 供 NPC 提案触发
- 祈祷、神明凝视、其他神明干涉、神话生成
- 血脉继承
- 存档/读档
"""
import json
import random
from pathlib import Path
from typing import Optional

from models import WorldState, SpecialEntity, MIRACLE_COST, GIFT_COST
from population import Person, PopulationPool
from llm_interface import (
    get_action_result, generate_new_entity, generate_npc_autonomy,
    generate_initial_population, generate_birth,
    get_error_narrative, get_fix_narrative, get_upgrade_narrative,
    generate_prayer_response, generate_divine_gaze,
    generate_other_god_event, generate_world_myth,
)
from mutation_system import roll_mutations, spread_mutations
from module_loader import ModuleLoader
from meta_system import MetaSystem

SAVE_FILE = Path(__file__).parent / "savegame.json"


class StateManager:
    def __init__(self):
        self.world = WorldState()
        self.active_entities: list[SpecialEntity] = []
        self.pool = PopulationPool()
        self.loader = ModuleLoader()
        self.meta = MetaSystem()

        # 模块持久化存储 (module_name -> dict)
        self.module_data: dict[str, dict] = {}

        # 近期事件流（供模块和 meta 读取）
        self.event_log: list[str] = []

        # 神话库（重大事件沉淀为神话）
        self.myths: list[dict] = []

        # 其他神明干涉冷却（每N回合最多一次）
        self._other_god_cooldown = 0

        # 升级请求队列 (module_name, proposal, proposer)
        self._upgrade_requests: list[tuple[str, str, str]] = []

    # ── 对外接口：模块可调用 ────────────────────────────────────────────────

    def request_upgrade(self, module_name: str, proposal: str, proposer: str = ""):
        """NPC 提案或模块自身请求升级。"""
        self._upgrade_requests.append((module_name, proposal, proposer))

    def add_event(self, text: str):
        """追加一条事件到事件流。"""
        self.event_log.append(text)
        if len(self.event_log) > 80:
            self.event_log = self.event_log[-80:]

    # ── 初始化 ───────────────────────────────────────────────────────────────

    def initialize(self):
        data = generate_initial_population(self.world, count=12)
        age_to_offset = {"child": -8, "youth": -16, "adult": -28, "elder": -52}
        for pd in data.get("people", []):
            offset = age_to_offset.get(pd.get("age_stage", "adult"), -25)
            birth_yr = self.world.world_year + offset   # 可以是负数，代表游戏开始前出生
            p = Person(
                name=pd["name"],
                birth_year=birth_yr,
                traits=pd.get("traits", ["未知"]),
                background=pd.get("background", ""),
            )
            p.add_event(birth_yr, "birth", pd.get("background", "出生。"))
            self.pool.add(p)

    # ── 玩家操作 ────────────────────────────────────────────────────────────

    def apply_action(self, action_type: str, subject: str, cost: int) -> str:
        if not self.world.can_afford(cost):
            return f"信仰不足（需要 {cost}，当前 {self.world.faith}）。"

        self.world.spend_faith(cost)
        result = get_action_result(action_type, subject, self.world,
                                   self.active_entities, self.pool)

        self.world.apply_population_change(result.get("population_change", 0))

        for tag in result.get("new_tech_tags", []):
            if tag not in self.world.tech_and_culture_tags:
                self.world.tech_and_culture_tags.append(tag)

        self.world.accumulate_tendency(result.get("tendency_hints", [subject[:2]]))

        # 个人事件 + NPC 提案
        for ev in result.get("individual_events", []):
            p = self.pool.get_by_name(ev.get("name", ""))
            if p and p.is_alive():
                p.add_event(self.world.world_year,
                            ev.get("event_type", "witness"),
                            ev.get("description", ""))
            sp = ev.get("system_proposal") or {}
            if sp.get("target_module") and sp.get("proposal"):
                self._upgrade_requests.append((
                    sp["target_module"], sp["proposal"],
                    ev.get("name", ""),
                ))

        if result.get("calendar_name"):
            self.world.calendar_name = result["calendar_name"]

        era_notice = ""
        if result.get("is_era_breakthrough") and result.get("new_era_name"):
            self.world.current_era = result["new_era_name"]
            era_notice = f"\n\n  ★ 时代跨越！世界迈入了【{self.world.current_era}】！"
            # 时代跨越 → 考虑生成神话
            self._maybe_generate_myth(result.get("narrative_text", ""))

        # 通知已加载模块
        for r in self.loader.run_on_action(self, action_type, subject):
            if r.get("narrative"):
                self.add_event(r["narrative"])

        delta = result.get("population_change", 0)
        sign = "+" if delta >= 0 else ""
        narrative = result["narrative_text"] + era_notice + f"\n  人口变化：{sign}{delta}"
        self.add_event(narrative)
        return narrative

    # ── 祈祷回应 ─────────────────────────────────────────────────────────────

    def respond_to_prayer(self, person_name: str, response_type: str) -> str:
        """response_type: answer / ignore / punish / bless"""
        person = self.pool.get_by_name(person_name)
        if not person or not person.is_alive():
            return f"未找到正在祈祷的「{person_name}」。"
        if not person.prayer_pending:
            return f"{person_name} 当前没有祈祷。"

        result = generate_prayer_response(
            person, person.prayer_pending, self.world, response_type
        )
        person.prayer_pending = ""
        person.add_event(self.world.world_year, "miracle", result.get("event_for_person", ""))

        # 调整该人的信仰值
        faith_delta = result.get("faith_change_for_person", 0)
        person.faith_in_god = max(0.0, min(1.0, person.faith_in_god + faith_delta / 100))

        self.world.apply_population_change(result.get("population_change", 0))
        narrative = result.get("narrative", "")
        self.add_event(narrative)
        return narrative

    # ── 神明凝视 ─────────────────────────────────────────────────────────────

    def divine_gaze(self, target_name: str) -> str:
        """深度洞察某人或某地，揭示普通事件流看不到的层面。"""
        target_type = "person"
        person = self.pool.get_by_name(target_name)
        if not person:
            target_type = "place"

        result = generate_divine_gaze(target_name, target_type, self.world, self.pool)

        if person and person.is_alive():
            person.add_event(self.world.world_year, "divine",
                             "神明的目光曾短暂停在他身上——他不知道这意味着什么。")

        return (
            f"【神明凝视：{target_name}】\n"
            f"{result.get('deep_vision', '')}\n\n"
            f"  ▸ {result.get('hidden_truth', '')}"
        )

    # ── NPC 自主行为 ─────────────────────────────────────────────────────────

    def _tick_npc_autonomy(self) -> list[str]:
        if not self.pool.living:
            return []
        data = generate_npc_autonomy(self.world, self.pool, self.active_entities)
        notices = []
        for ev in data.get("autonomous_events", []):
            p = self.pool.get_by_name(ev.get("name", ""))
            if p and p.is_alive():
                desc = ev.get("description", "")
                p.add_event(self.world.world_year, "autonomous", desc)
                notices.append(f"  [自主] {p.name}：{desc}")
            effect = ev.get("world_effect", "")
            if effect:
                notices.append(f"    → {effect}")
            pop = ev.get("population_change", 0)
            if pop:
                self.world.apply_population_change(pop)
            # NPC 提案
            sp = ev.get("system_proposal") or {}
            if sp.get("target_module") and sp.get("proposal"):
                self._upgrade_requests.append((
                    sp["target_module"], sp["proposal"],
                    ev.get("name", ""),
                ))
        return notices

    # ── 特殊实体生命周期 ─────────────────────────────────────────────────────

    def _retire_entity(self, entity: SpecialEntity, reason: str) -> str:
        for tag in entity.legacy_tags:
            if tag not in self.world.tech_and_culture_tags:
                self.world.tech_and_culture_tags.append(tag)
        notice = f"  [{entity.name}离世] {reason}"
        if entity.legacy_tags:
            notice += f"\n    他留下了：{', '.join(entity.legacy_tags)}"
        return notice

    def _tick_entities(self) -> list[str]:
        notices, survivors = [], []
        for e in self.active_entities:
            alive, reason = e.tick()
            if alive:
                survivors.append(e)
            else:
                notices.append(self._retire_entity(e, reason))
        self.active_entities = survivors
        return notices

    def _maybe_spawn_entity(self) -> Optional[str]:
        prob = min(0.04 + self.world.population / 100_000, 0.25)
        if random.random() > prob:
            return None
        data = generate_new_entity(self.world)
        entity = SpecialEntity(
            name=data["name"],
            traits=data["traits"],
            current_focus=data["current_focus"],
            risk_level=float(data["risk_level"]),
        )
        self.active_entities.append(entity)
        p = self.pool.get_by_name(entity.name)
        if p:
            p.is_notable = True
        return (
            f"\n  [异类出现] {entity.name}（{'、'.join(entity.traits)}）\n"
            f"    正在：{entity.current_focus}  危险度 {entity.risk_level}"
        )

    # ── 人口生命周期 ─────────────────────────────────────────────────────────

    def _tick_population(self) -> list[str]:
        notices = []
        for person, cause in self.pool.tick_aging(self.world.world_year):
            self.pool.kill(person, self.world.world_year, cause)
            notices.append(
                f"  [{person.name}离世] {cause}，"
                f"享年{person.age(self.world.world_year)}岁"
            )

        birth_prob = min(0.25 + self.world.population / 8000, 0.7)
        if self.pool.can_add_birth() and random.random() < birth_prob:
            data = generate_birth(self.world, self.pool)
            parents = random.sample(self.pool.living, min(2, len(self.pool.living)))
            baby = Person(
                name=data["name"],
                birth_year=self.world.world_year,
                traits=data.get("traits", ["未知"]),
                background=data.get("background", ""),
                parent_names=[p.name for p in parents],
                inherited_memory=data.get("inherited_memory", ""),
            )
            if data.get("inherited_memory"):
                baby.add_event(self.world.world_year, "memory", data["inherited_memory"])
            baby.add_event(self.world.world_year, "birth", data.get("background", "出生。"))
            for parent in parents:
                parent.children_names.append(baby.name)
            self.pool.add(baby)
            notices.append(f"  [新生] {baby.name}：{data.get('background', '')}")
        return notices

    # ── 变异 ─────────────────────────────────────────────────────────────────

    def _tick_mutations(self) -> list[str]:
        notices = []
        people_names = [p.name for p in self.pool.living]

        new_muts = roll_mutations(self.world, self.active_entities, people_names)
        for m in new_muts:
            self.world.active_mutations.append(m)
            tier_label = {1: "◈ 表层变异", 2: "◉ 功能变异", 3: "⬡ 本质变异"}[m.tier]
            notices.append(f"\n  [{tier_label}] {m.target_name}\n    {m.description}")
            if m.affected_person:
                p = self.pool.get_by_name(m.affected_person)
                if p and p.is_alive():
                    p.add_event(self.world.world_year, "mutation",
                                m.person_event or m.description)
            # 本质变异 → 可能生成神话
            if m.tier == 3:
                self._maybe_generate_myth(m.description)

        spread = spread_mutations(self.world, self.active_entities, people_names)
        for s in spread:
            notices.append(f"\n  [变异扩散] {s['description']}")
            if s.get("affected_person"):
                p = self.pool.get_by_name(s["affected_person"])
                if p and p.is_alive():
                    p.add_event(self.world.world_year, "mutation",
                                s.get("person_event", s["description"]))

        self.world.active_mutations = [
            m for m in self.world.active_mutations
            if m.tier == 3 or (self.world.world_year - m.turn_appeared) < 15
        ]
        return notices

    # ── 其他神明干涉 ─────────────────────────────────────────────────────────

    def _maybe_other_god(self) -> list[str]:
        self._other_god_cooldown -= 1
        if self._other_god_cooldown > 0:
            return []
        # 基础概率 3%
        if random.random() > 0.03:
            return []
        self._other_god_cooldown = random.randint(8, 20)
        result = generate_other_god_event(self.world, self.pool, self.active_entities)
        # 影响信仰
        faith_impact = result.get("faith_impact", 0)
        self.world.faith = max(0, self.world.faith + faith_impact)
        # 部分居民感知到
        for p in self.pool.random_living(2):
            p.add_event(self.world.world_year, "witness",
                        result.get("narrative_for_npcs", "感到某种无法解释的异样。"))
        return [f"\n  [异常现象] {result.get('description', '')}"]

    # ── 神话生成 ─────────────────────────────────────────────────────────────

    def _maybe_generate_myth(self, event_text: str):
        if not event_text or random.random() > 0.4:
            return
        myth = generate_world_myth(event_text, self.world)
        if myth.get("myth_name"):
            self.myths.append(myth)
            # 让一个随机居民记住这个神话
            people = self.pool.random_living(1)
            if people:
                people[0].add_event(
                    self.world.world_year, "growth",
                    f"听闻了「{myth['myth_name']}」的故事：{myth['myth_text'][:40]}…"
                )

    # ── 模块系统 ─────────────────────────────────────────────────────────────

    def _tick_modules(self) -> list[str]:
        notices = []

        # 处理升级请求
        for module_name, proposal, proposer in list(self._upgrade_requests):
            self.loader.request_upgrade(module_name, proposal, proposer)
        self._upgrade_requests.clear()

        # 处理修复/升级结果
        for result in self.loader.check_pending_results(self):
            t = result["type"]
            name = result["name"]
            proposer = result.get("proposer", "")
            if t == "fix":
                narrative = get_fix_narrative(name, self.world, self.pool)
                notices.append(f"\n  [织体修复] {narrative}")
            elif t == "upgrade":
                narrative = get_upgrade_narrative(name, proposer, self.world, self.pool)
                notices.append(f"\n  [系统进化] {narrative}")
            else:
                notices.append(f"\n  [织体撕裂延续] {name} 的异常仍未解决。")

        # 运行活跃模块
        for msg, module_name in self.loader.run_turn_end(self):
            if msg == "__crash__":
                err_result = get_error_narrative(module_name, "", self.world, self.pool)
                notices.append(f"\n  [织体异常] {err_result.get('narrative', '世界出现了裂缝。')}")
                if err_result.get("npc_reaction"):
                    notices.append(f"    {err_result['npc_reaction']}")
                notices.append(f"    （正在修复中……）")
            else:
                notices.append(msg)

        return notices

    # ── 祈祷检查 ─────────────────────────────────────────────────────────────

    def _tick_prayers(self) -> list[str]:
        """每回合随机产生新的祈祷者。"""
        notices = []
        for p in self.pool.living:
            if p.prayer_pending:
                continue
            # 高信仰或遭遇困境时更容易祈祷
            pray_prob = p.faith_in_god * 0.08
            if random.random() < pray_prob:
                prayers = [
                    f"祈求神明赐予食物，冬天快撑不下去了。",
                    f"祈求神明保佑孩子平安出生。",
                    f"祈求神明解释为何{random.choice(['河流变色', '树木发光', '天穹流动加速'])}。",
                    f"献上祭品，希望神明能让部落的敌人退去。",
                    f"请求神明的指引，不知道该往哪个方向走。",
                ]
                p.prayer_pending = random.choice(prayers)
                notices.append(f"  [祈祷] {p.name}：{p.prayer_pending}")
        return notices

    # ── 回合推进 ─────────────────────────────────────────────────────────────

    def end_of_turn(self) -> list[str]:
        self.world.tick_resources()   # 年份+1，信仰自然增长
        messages = []

        messages.extend(self._tick_entities())
        messages.extend(self._tick_population())

        spawn = self._maybe_spawn_entity()
        if spawn:
            messages.append(spawn)

        messages.extend(self._tick_npc_autonomy())
        messages.extend(self._tick_mutations())
        messages.extend(self._maybe_other_god())
        messages.extend(self._tick_prayers())
        messages.extend(self._tick_modules())

        # 积累事件
        for m in messages:
            if m.strip():
                self.add_event(m)

        # 涌现检测
        if self.meta.should_check(self.world.world_year):
            messages.extend(self.meta.check_and_generate(self, self.loader))

        return messages

    # ── 存档 / 读档 ───────────────────────────────────────────────────────────

    def save(self, path: Path = SAVE_FILE):
        entities_data = []
        for e in self.active_entities:
            entities_data.append({
                "name": e.name, "traits": e.traits,
                "current_focus": e.current_focus, "risk_level": e.risk_level,
                "age": e.age, "max_age": e.max_age,
                "legacy_tags": e.legacy_tags, "mutations": e.mutations,
            })
        data = {
            "world": self.world.to_dict(),
            "pool": self.pool.to_dict(),
            "active_entities": entities_data,
            "myths": self.myths,
            "event_log": self.event_log[-50:],
            "module_data": self.module_data,
            "active_modules": self.loader.active_names(),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: Path = SAVE_FILE):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.world = WorldState.from_dict(data["world"])
        self.pool = PopulationPool.from_dict(data["pool"])
        self.active_entities = [SpecialEntity(**e) for e in data.get("active_entities", [])]
        self.myths = data.get("myths", [])
        self.event_log = data.get("event_log", [])
        self.module_data = data.get("module_data", {})
        # 已保存的模块从磁盘重新加载
        from module_loader import MODULES_DIR
        for name in data.get("active_modules", []):
            mod_file = MODULES_DIR / f"{name}.py"
            if mod_file.exists():
                self.loader.load(name, mod_file.read_text(encoding="utf-8"), self)

    # ── 展示辅助 ─────────────────────────────────────────────────────────────

    def entities_summary(self) -> str:
        if not self.active_entities:
            return "  （暂无特殊人物）"
        lines = []
        for e in self.active_entities:
            mut = f"  变异：{'；'.join(e.mutations)}" if e.mutations else ""
            lines.append(
                f"  · {e.name}（{'、'.join(e.traits)}，第{e.age}/{e.max_age}年）\n"
                f"    正在：{e.current_focus}{mut}"
            )
        return "\n".join(lines)

    def mutations_summary(self) -> str:
        if not self.world.active_mutations:
            return "  （无活跃变异）"
        lines = []
        for m in self.world.active_mutations:
            tier_label = {1: "◈", 2: "◉", 3: "⬡"}[m.tier]
            lines.append(f"  {tier_label} {m.target_name}：{m.description}")
        return "\n".join(lines)

    def myths_summary(self) -> str:
        if not self.myths:
            return "  （世界尚无神话）"
        return "\n".join(
            f"  《{m['myth_name']}》\n  {m['myth_text'][:80]}…"
            for m in self.myths[-5:]
        )
