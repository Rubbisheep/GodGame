"""
StateManager — 薄协调器，把所有子系统串起来。
各 tick 系统在 systems/ 中独立实现。
LLM 调用全在 llm/ 中，不在这里。

核心极简：时间 / 人 / 信仰循环 / 玩家干预 / NPC 自主 / 涌现引擎。
其他一切（变异、神话、异人、其他神明、贸易、战争……）都由 LLM 生成的模块承担。
"""
import json
from pathlib import Path

from core.models import WorldState, MIRACLE_COST, GIFT_COST
from core.population import Person, PopulationPool
from llm import (
    get_action_result, generate_initial_population,
    generate_prayer_response, generate_divine_gaze, generate_yearly_digest,
    get_error_narrative, get_fix_narrative, get_upgrade_narrative,
)
from evolution import ModuleLoader, MetaSystem, MODULES_DIR
from systems import SYSTEMS

SAVE_DIR = Path(__file__).parent / "saves"
SAVE_FILE = SAVE_DIR / "savegame.json"
GIFT_ABSORB_YEARS = 8
MIRACLE_COOLDOWN_YEARS = 15


class StateManager:
    def __init__(self):
        self.world = WorldState()
        self.pool = PopulationPool()
        self.loader = ModuleLoader()
        self.meta = MetaSystem()
        self.module_data: dict[str, dict] = {}
        self.event_log: list[str] = []
        self._upgrade_requests: list[tuple[str, str, str]] = []
        self._last_gift_year: int = -999
        self._last_miracle_year: int = -999

    # ── 公开 API（供模块和外部调用）──────────────────────────────────────

    def request_upgrade(self, module_name: str, proposal: str, proposer: str = ""):
        self._upgrade_requests.append((module_name, proposal, proposer))

    def add_event(self, text: str):
        self.event_log.append(text)
        if len(self.event_log) > 80:
            self.event_log = self.event_log[-80:]

    # ── 初始化 ───────────────────────────────────────────────────────────

    def initialize(self) -> str:
        data = generate_initial_population(self.world, count=10)
        age_to_offset = {"child": -8, "youth": -16, "adult": -28, "elder": -45}
        elders = []
        for pd in data.get("people", []):
            offset = age_to_offset.get(pd.get("age_stage", "adult"), -25)
            birth_yr = self.world.world_year + offset
            p = Person(
                name=pd["name"], birth_year=birth_yr,
                traits=pd.get("traits", ["未知"]),
                background=pd.get("background", ""),
                faith_in_god=0.0,
            )
            p.add_event(birth_yr, "birth", pd.get("background", "出生。"))
            self.pool.add(p)
            if pd.get("age_stage") == "elder":
                elders.append(p)

        sensitive = elders[0] if elders else (self.pool.living[0] if self.pool.living else None)
        if sensitive:
            sensitive.faith_in_god = 0.06
            sensitive.add_event(
                self.world.world_year, "autonomous",
                "每天在河边垒几块石头，对着空气低语——他自己也不知道在和谁说话。"
            )

        opening = (
            "\n你在某个时刻意识到自己存在。\n"
            "没有名字。没有记忆。\n"
            "只有一种正在凝聚的注意力——某种东西刚刚从极深处浮现，\n"
            "第一次真正看见了这个世界。\n\n"
            f"你看见了：一条河，一片泥滩，一堆快要熄灭的火，\n"
            f"围在火边的 {len(self.pool.living)} 个人影。\n"
            "他们不知道你在看他们。\n\n"
        )
        if sensitive:
            opening += (
                f"其中一个长者——{sensitive.name}——每天在河边垒石头，\n"
                "对着空气低语，像在回应某个他从未听到回应的声音。\n\n"
            )
        opening += "这个世界刚刚有了一个观察者。"
        self.add_event(opening)
        return opening

    # ── 玩家行动 ─────────────────────────────────────────────────────────

    def apply_action(self, action_type: str, subject: str, cost: int) -> str:
        if not self.world.can_afford(cost):
            return f"神力不足（需要 {cost}，当前 {self.world.faith}）。"

        yr = self.world.world_year
        if action_type == "赐予":
            wait = GIFT_ABSORB_YEARS - (yr - self._last_gift_year)
            if wait > 0:
                return f"部落还在消化上一次的恩赐，需要再等 {wait} 年。"
        elif action_type == "施放":
            wait = MIRACLE_COOLDOWN_YEARS - (yr - self._last_miracle_year)
            if wait > 0:
                return f"神力仍在恢复，奇迹需要再等 {wait} 年才能再次降临。"

        self.world.spend_faith(cost)
        result = get_action_result(action_type, subject, self.world, self.pool)

        self.world.apply_population_change(result.get("population_change", 0))
        for tag in result.get("new_tech_tags", []):
            if tag not in self.world.tech_and_culture_tags:
                self.world.tech_and_culture_tags.append(tag)
        self.world.accumulate_tendency(result.get("tendency_hints", [subject[:2]]))

        for ev in result.get("individual_events", []):
            p = self.pool.get_by_name(ev.get("name", ""))
            if p and p.is_alive():
                p.add_event(self.world.world_year, ev.get("event_type", "witness"),
                            ev.get("description", ""))
                if ev.get("event_type") in ("witness", "miracle", "divine"):
                    p.faith_in_god = min(1.0, p.faith_in_god + 0.15)
            sp = ev.get("system_proposal") or {}
            if sp.get("target_module") and sp.get("proposal"):
                self._upgrade_requests.append((sp["target_module"], sp["proposal"], ev.get("name", "")))

        if result.get("calendar_name"):
            self.world.calendar_name = result["calendar_name"]

        if action_type == "赐予":
            self._last_gift_year = self.world.world_year
        elif action_type == "施放":
            self._last_miracle_year = self.world.world_year

        era_notice = ""
        if result.get("is_era_breakthrough") and result.get("new_era_name"):
            self.world.current_era = result["new_era_name"]
            era_notice = f"\n\n  ★ 时代跨越！世界迈入了【{self.world.current_era}】！"

        for r in self.loader.run_on_action(self, action_type, subject):
            if r.get("narrative"):
                self.add_event(r["narrative"])

        delta = result.get("population_change", 0)
        sign = "+" if delta >= 0 else ""
        narrative = result["narrative_text"] + era_notice + f"\n  人口变化：{sign}{delta}"
        self.add_event(narrative)
        return narrative

    # ── 祈祷 / 凝视 ──────────────────────────────────────────────────────

    def respond_to_prayer(self, person_name: str, response_type: str) -> str:
        person = self.pool.get_by_name(person_name)
        if not person or not person.is_alive():
            return f"未找到正在祈祷的「{person_name}」。"
        if not person.prayer_pending:
            return f"{person_name} 当前没有祈祷。"
        result = generate_prayer_response(person, person.prayer_pending, self.world, response_type)
        person.prayer_pending = ""
        person.add_event(self.world.world_year, "miracle", result.get("event_for_person", ""))
        faith_delta = result.get("faith_change_for_person", 0)
        person.faith_in_god = max(0.0, min(1.0, person.faith_in_god + faith_delta / 100))
        self.world.apply_population_change(result.get("population_change", 0))
        narrative = result.get("narrative", "")
        self.add_event(narrative)
        return narrative

    def divine_gaze(self, target_name: str) -> str:
        target_type = "person"
        person = self.pool.get_by_name(target_name)
        if not person:
            target_type = "place"
        result = generate_divine_gaze(target_name, target_type, self.world, self.pool)
        if person and person.is_alive():
            person.add_event(self.world.world_year, "divine",
                             "神明的目光曾短暂停在他身上——他不知道这意味着什么。")
            person.faith_in_god = min(1.0, person.faith_in_god + 0.03)
        return (
            f"【神明凝视：{target_name}】\n"
            f"{result.get('deep_vision', '')}\n\n"
            f"  ▸ {result.get('hidden_truth', '')}"
        )

    # ── 模块 tick ────────────────────────────────────────────────────────

    def _tick_modules(self) -> list[str]:
        notices = []
        for module_name, proposal, proposer in list(self._upgrade_requests):
            self.loader.request_upgrade(module_name, proposal, proposer,
                                        self.world, self.pool)
        self._upgrade_requests.clear()

        for result in self.loader.check_pending_results(self):
            t, name, proposer = result["type"], result["name"], result.get("proposer", "")
            if t == "fix":
                narrative = get_fix_narrative(name, self.world, self.pool)
                notices.append(f"\n  [法则修复] {narrative}")
            elif t == "upgrade":
                narrative = get_upgrade_narrative(name, proposer, self.world, self.pool)
                notices.append(f"\n  [系统进化] {narrative}")
            else:
                notices.append(f"\n  [法则异常延续] {name} 的异常仍未解决。")

        for msg, module_name in self.loader.run_turn_end(self):
            if msg == "__crash__":
                err_result = get_error_narrative(module_name, "", self.world, self.pool)
                notices.append(f"\n  [法则异常] {err_result.get('narrative', '世界出现了裂缝。')}")
                if err_result.get("npc_reaction"):
                    notices.append(f"    {err_result['npc_reaction']}")
                notices.append("    （正在修复中……）")
            else:
                notices.append(msg)
        return notices

    # ── 回合推进（核心） ──────────────────────────────────────────────────

    def end_of_turn(self, *, narrate: bool = True) -> list[str]:
        """推进一年。
        narrate=True：把当年原始事件压成一段叙事 digest 返回（玩家可见）。
        narrate=False：静默推进（catchup / 快进），原始事件仍写入 event_log。
        无论哪种模式，原始事件都会落到 self.event_log 供 `故事` 命令深挖。
        """
        faith_bonus = int(sum(p.faith_in_god for p in self.pool.living) * 2)
        self.world.tick_resources(faith_bonus)

        raw: list[str] = []
        for system in SYSTEMS:
            raw.extend(system.tick(self))
        raw.extend(self._tick_modules())

        self.meta.record_turn_events(raw)
        if self.meta.should_check(self.world.world_year):
            raw.extend(self.meta.check_and_generate(self, self.loader))

        # 原始事件全部入 event_log（包括 emergence 通告）
        for m in raw:
            if m.strip():
                self.add_event(m)

        if not narrate:
            return []

        nontrivial = [m for m in raw if m.strip()]
        if not nontrivial:
            return []

        digest = generate_yearly_digest(self.world, nontrivial)
        if digest:
            return [digest]
        # 兜底：digest LLM 失败时，直接返回前几条 raw，避免玩家看到空年
        return nontrivial[:3]

    # ── 存档 / 读档 ──────────────────────────────────────────────────────

    def save(self, path: Path = SAVE_FILE):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "world": self.world.to_dict(),
            "pool": self.pool.to_dict(),
            "event_log": self.event_log[-50:],
            "module_data": self.module_data,
            "active_modules": self.loader.active_names(),
            "last_gift_year": self._last_gift_year,
            "last_miracle_year": self._last_miracle_year,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: Path = SAVE_FILE):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.world = WorldState.from_dict(data["world"])
        self.pool = PopulationPool.from_dict(data["pool"])
        self.event_log = data.get("event_log", [])
        self.module_data = data.get("module_data", {})
        self._last_gift_year = data.get("last_gift_year", -999)
        self._last_miracle_year = data.get("last_miracle_year", -999)
        for name in data.get("active_modules", []):
            mod_file = MODULES_DIR / f"{name}.py"
            if mod_file.exists():
                self.loader.load(name, mod_file.read_text(encoding="utf-8"), self)
