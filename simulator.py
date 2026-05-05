"""
世界模拟器 — 后台线程持续推进世界时间。

每 TICK_INTERVAL 秒真实时间 = 世界 1 年。
启动时计算离线时长并快进补偿（上限 MAX_CATCHUP 年）。
"""
import threading
import time
import queue
from pathlib import Path

TICK_INTERVAL = 60        # 真实秒数 / 年
AUTOSAVE_EVERY = 5        # 每N年自动存档一次
MAX_CATCHUP = 100         # 离线最多补计N年
TIMESTAMP_KEY = "__last_tick_time__"


class WorldSimulator:
    def __init__(self, state_manager):
        self.sm = state_manager
        self.event_queue: queue.Queue = queue.Queue()
        self.lock = threading.RLock()
        self._running = False
        self._ticks_since_save = 0
        self._thread: threading.Thread | None = None

    # ── 启动/停止 ────────────────────────────────────────────────────────────

    def start(self, catchup_years: int = 0):
        """启动后台模拟线程。catchup_years 为补进年数。"""
        if catchup_years > 0:
            actual = min(catchup_years, MAX_CATCHUP)
            self.event_queue.put(
                f"\n  ══ 你离开期间，世界又流逝了 {actual} 年 ══"
            )
            for _ in range(actual):
                self._tick(silent=False)

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._force_save()

    # ── 线程主循环 ───────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            time.sleep(TICK_INTERVAL)
            if self._running:
                self._tick(silent=False)

    def _tick(self, silent: bool = False):
        with self.lock:
            msgs = self.sm.end_of_turn()
            if not silent:
                for m in msgs:
                    if m.strip():
                        self.event_queue.put(m)
            self._ticks_since_save += 1
            if self._ticks_since_save >= AUTOSAVE_EVERY:
                self._force_save()

    def _force_save(self):
        try:
            import time as _t
            self.sm.save()
            # 在存档里记录当前时间戳
            import json
            from state_manager import SAVE_FILE
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            data[TIMESTAMP_KEY] = _t.time()
            SAVE_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._ticks_since_save = 0
        except Exception:
            pass

    # ── 玩家行动（持锁执行）────────────────────────────────────────────────

    def player_act(self, fn, *args, **kwargs) -> str:
        """在锁内执行玩家行动，并推进一个回合。"""
        with self.lock:
            result = fn(*args, **kwargs)
            msgs = self.sm.end_of_turn()
            for m in msgs:
                if m.strip():
                    self.event_queue.put(m)
        return result

    def player_query(self, fn, *args, **kwargs):
        """在锁内执行只读查询（不推进回合）。"""
        with self.lock:
            return fn(*args, **kwargs)

    # ── 事件提取 ─────────────────────────────────────────────────────────────

    def drain(self) -> list[str]:
        """提取并清空所有积压事件。"""
        events = []
        while True:
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events


# ── 离线补偿计算 ──────────────────────────────────────────────────────────────

def calc_catchup_years(save_file: Path) -> int:
    """读取存档时间戳，计算应补进的年数。"""
    if not save_file.exists():
        return 0
    try:
        import json, time as _t
        data = json.loads(save_file.read_text(encoding="utf-8"))
        last = data.get(TIMESTAMP_KEY)
        if last is None:
            return 0
        elapsed_sec = _t.time() - float(last)
        return max(0, int(elapsed_sec // TICK_INTERVAL))
    except Exception:
        return 0
