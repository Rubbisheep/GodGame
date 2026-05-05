"""
模块热加载器。

生命周期：新建 → 运行 → [崩溃 → 后台修复 → 恢复]
                      → [NPC提案 → 后台升级 → 热替换]
"""
import types
import threading
import queue
import traceback
from pathlib import Path

MODULES_DIR = Path(__file__).parent / "modules"
MODULES_DIR.mkdir(exist_ok=True)

# 所有生成/升级的模块必须实现的接口（嵌入每次代码生成的 prompt）
MODULE_INTERFACE_DOC = """
模块必须定义：
  MODULE_NAME: str
  MODULE_DESCRIPTION: str
  EMERGENCE_REASON: str

  def register(state_manager): ...
  def on_turn_end(state_manager) -> list[str]: return []
  def on_action(state_manager, action_type: str, subject: str) -> dict: return {}

模块内可通过 state_manager 访问：
  state_manager.world        — WorldState
  state_manager.pool         — PopulationPool
  state_manager.active_entities — list[SpecialEntity]
  state_manager.event_log    — list[str]，近50条事件文本
  state_manager.loader.request_upgrade(module_name, reason, proposer)
                             — 请求升级自身或其他模块
"""


class LoadedModule:
    def __init__(self, name: str, mod: types.ModuleType, code: str):
        self.name = name
        self.mod = mod
        self.code = code


class ModuleLoader:
    def __init__(self):
        self._active: dict[str, LoadedModule] = {}
        self._broken: dict[str, str] = {}          # name → broken_code
        self._fix_queue: queue.Queue = queue.Queue()     # (name, fixed_code|None, "fix")
        self._upgrade_queue: queue.Queue = queue.Queue() # (name, new_code|None, proposer)
        self._pending: set[str] = set()            # names currently being fixed/upgraded

    # ── 加载 ──────────────────────────────────────────────────────────────

    def load(self, name: str, code: str, state_manager) -> tuple[bool, str]:
        path = MODULES_DIR / f"{name}.py"
        path.write_text(code, encoding="utf-8")
        try:
            mod = types.ModuleType(name)
            mod.__file__ = str(path)
            exec(compile(code, str(path), "exec"), mod.__dict__)
            for fn in ("register", "on_turn_end", "on_action"):
                if not callable(getattr(mod, fn, None)):
                    raise AttributeError(f"缺少函数：{fn}")
            mod.register(state_manager)
            self._active[name] = LoadedModule(name, mod, code)
            self._broken.pop(name, None)
            self._pending.discard(name)
            return True, ""
        except Exception:
            err = traceback.format_exc()
            self._broken[name] = code
            self._pending.discard(name)
            return False, err

    # ── 运行时调用 ────────────────────────────────────────────────────────

    def run_turn_end(self, state_manager) -> list[tuple[str, str]]:
        """返回 [(message, module_name)]，崩溃时 message=="__crash__"。"""
        out = []
        for name, lm in list(self._active.items()):
            try:
                msgs = lm.mod.on_turn_end(state_manager) or []
                for m in msgs:
                    out.append((m, name))
            except Exception:
                err = traceback.format_exc()
                self._handle_crash(name, lm.code, err)
                out.append(("__crash__", name))
        return out

    def run_on_action(self, state_manager, action_type: str, subject: str) -> list[dict]:
        results = []
        for name, lm in list(self._active.items()):
            try:
                r = lm.mod.on_action(state_manager, action_type, subject)
                if r:
                    results.append(r)
            except Exception:
                err = traceback.format_exc()
                self._handle_crash(name, lm.code, err)
        return results

    # ── 崩溃修复 ──────────────────────────────────────────────────────────

    def _handle_crash(self, name: str, code: str, error: str):
        self._active.pop(name, None)
        self._broken[name] = code
        if name not in self._pending:
            self._pending.add(name)
            threading.Thread(
                target=self._bg_fix, args=(name, code, error), daemon=True
            ).start()

    def _bg_fix(self, name: str, broken_code: str, error: str):
        try:
            from llm_interface import fix_module_code
            fixed = fix_module_code(name, broken_code, error)
            self._fix_queue.put((name, fixed))
        except Exception:
            self._fix_queue.put((name, None))

    # ── NPC 提案升级 ──────────────────────────────────────────────────────

    def request_upgrade(self, module_name: str, reason: str, proposer: str = ""):
        """由 NPC 提案或模块自身触发升级请求。"""
        if module_name not in self._active:
            return
        if module_name in self._pending:
            return
        self._pending.add(module_name)
        old_code = self._active[module_name].code
        threading.Thread(
            target=self._bg_upgrade,
            args=(module_name, old_code, reason, proposer),
            daemon=True,
        ).start()

    def _bg_upgrade(self, name: str, old_code: str, reason: str, proposer: str):
        try:
            from llm_interface import upgrade_module_code
            new_code = upgrade_module_code(name, old_code, reason, proposer)
            self._upgrade_queue.put((name, new_code, proposer))
        except Exception:
            self._upgrade_queue.put((name, None, proposer))

    # ── 回合末：处理队列 ──────────────────────────────────────────────────

    def check_pending_results(self, state_manager) -> list[dict]:
        """
        处理修复和升级队列，返回事件列表：
        [{"type": "fix"|"upgrade"|"fail", "name": ..., "proposer": ...}]
        """
        results = []

        while not self._fix_queue.empty():
            name, code = self._fix_queue.get_nowait()
            if code is None:
                results.append({"type": "fail", "name": name, "proposer": ""})
                self._pending.discard(name)
                continue
            ok, _ = self.load(name, code, state_manager)
            results.append({"type": "fix" if ok else "fail", "name": name, "proposer": ""})

        while not self._upgrade_queue.empty():
            name, code, proposer = self._upgrade_queue.get_nowait()
            if code is None:
                results.append({"type": "fail", "name": name, "proposer": proposer})
                self._pending.discard(name)
                continue
            ok, _ = self.load(name, code, state_manager)
            results.append({
                "type": "upgrade" if ok else "fail",
                "name": name,
                "proposer": proposer,
            })

        return results

    # ── 查询 ──────────────────────────────────────────────────────────────

    def active_names(self) -> list[str]:
        return list(self._active.keys())

    def broken_names(self) -> list[str]:
        return list(self._broken.keys())

    def is_loaded(self, name: str) -> bool:
        return name in self._active

    def get_description(self, name: str) -> str:
        path = MODULES_DIR / f"{name}.py"
        if not path.exists():
            return ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if "MODULE_DESCRIPTION" in line and "=" in line:
                return line.split("=", 1)[1].strip().strip("\"'")
        return ""
