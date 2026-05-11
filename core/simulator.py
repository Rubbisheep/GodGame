"""
世界模拟器 — 后台线程持续推进世界时间。
基准：TICK_INTERVAL 秒真实时间 = 世界 1 年。
玩家可通过倍速 (speed_multiplier) 调节流速；也可以 fast_forward 主动快进若干年。
启动时计算离线时长并快进补偿（上限 MAX_CATCHUP 年）。
"""
import threading
import time
import queue
import json
from pathlib import Path

TICK_INTERVAL = 3600  # 基准：1 小时真实时间 = 世界 1 年
AUTOSAVE_EVERY = 5
MAX_CATCHUP = 100
MIN_SPEED, MAX_SPEED = 0.1, 3600.0  # 极端值防呆
TIMESTAMP_KEY = "__last_tick_time__"

_SAVE_FILE = Path(__file__).parent.parent / "saves" / "savegame.json"


class WorldSimulator:
    def __init__(self, state_manager):
        self.sm = state_manager
        self.event_queue: queue.Queue = queue.Queue()
        self.lock = threading.RLock()
        self._running = False
        self._ticks_since_save = 0
        self._thread: threading.Thread | None = None
        self._bg_ticked = False  # 后台 tick 发生过，下次刷新时自动显示状态
        self.speed_multiplier: float = 1.0  # 1.0 = 1h/年；60.0 = 1min/年，等等

    # ── 启动/停止 ───────────────────────────────────────────────────────────

    def start(self, catchup_years: int = 0, on_progress=None):
        """启动后台时流。
        on_progress(year_done, total) 在每年 catchup tick 后调用——
        调用方应当用它来 drain 事件队列、即时打印，避免玩家干等。
        catchup 模式跳过 autonomy_tick 以加速；玩家 Ctrl+C 可中断。
        """
        self._running = True

        if catchup_years > 0:
            actual = min(catchup_years, MAX_CATCHUP)
            self.event_queue.put(f"\n  ══ 你离开期间，世界又流逝了 {actual} 年 ══")
            self.event_queue.put("  正在追溯（每年滚动汇报，可 Ctrl+C 跳过）……\n")
            try:
                for i in range(actual):
                    if not self._running:
                        break
                    with self.lock:
                        msgs = self.sm.end_of_turn(narrate=True, skip_autonomy=True)
                        for m in msgs:
                            if m.strip():
                                self.event_queue.put(m)
                    if on_progress:
                        on_progress(i + 1, actual)
            except KeyboardInterrupt:
                self.event_queue.put(
                    f"\n  ══ 追溯被中断（停留在第 {self.sm.world.world_year} 年） ══"
                )
                if on_progress:
                    on_progress(actual, actual)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._force_save()

    # ── 主循环 ──────────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            interval = TICK_INTERVAL / max(MIN_SPEED, self.speed_multiplier)
            time.sleep(interval)
            if self._running:
                self._tick(silent=False)
                self._bg_ticked = True

    # ── 速度控制 ─────────────────────────────────────────────────────────────

    def set_speed(self, multiplier: float) -> float:
        """设置倍速并返回实际应用的值（被 clamp 过）。"""
        self.speed_multiplier = max(MIN_SPEED, min(MAX_SPEED, float(multiplier)))
        return self.speed_multiplier

    def fast_forward(self, years: int, on_progress=None) -> int:
        """主动快进 N 年。返回实际推进的年数（中断时为已完成的年数）。
        和 catchup 同套机制：每年生成 digest 流式输出、跳 autonomy_tick、可 Ctrl+C 打断。"""
        actual = max(0, min(int(years), MAX_CATCHUP))
        if actual <= 0:
            return 0
        completed = 0
        try:
            for i in range(actual):
                with self.lock:
                    msgs = self.sm.end_of_turn(narrate=True, skip_autonomy=True)
                    for m in msgs:
                        if m.strip():
                            self.event_queue.put(m)
                completed = i + 1
                if on_progress:
                    on_progress(completed, actual)
        except KeyboardInterrupt:
            pass
        self._bg_ticked = True
        return completed

    def _tick(self, silent: bool = False):
        with self.lock:
            msgs = self.sm.end_of_turn(narrate=not silent)
            if not silent:
                for m in msgs:
                    if m.strip():
                        self.event_queue.put(m)
            self._ticks_since_save += 1
            if self._ticks_since_save >= AUTOSAVE_EVERY:
                self._force_save()

    def _force_save(self):
        try:
            self.sm.save()
            data = json.loads(_SAVE_FILE.read_text(encoding="utf-8"))
            data[TIMESTAMP_KEY] = time.time()
            _SAVE_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._ticks_since_save = 0
        except Exception:
            pass

    # ── 玩家接口 ─────────────────────────────────────────────────────────────

    def player_act(self, fn, *args, **kwargs) -> str:
        with self.lock:
            result = fn(*args, **kwargs)
            msgs = self.sm.end_of_turn()
            for m in msgs:
                if m.strip():
                    self.event_queue.put(m)
        return result

    def player_query(self, fn, *args, **kwargs):
        with self.lock:
            return fn(*args, **kwargs)

    def drain(self) -> tuple[list[str], bool]:
        """返回 (事件列表, 是否有后台 tick 发生)。"""
        events = []
        while True:
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        ticked = self._bg_ticked
        self._bg_ticked = False
        return events, ticked


def calc_catchup_years(save_file: Path) -> int:
    if not save_file.exists():
        return 0
    try:
        data = json.loads(save_file.read_text(encoding="utf-8"))
        last = data.get(TIMESTAMP_KEY)
        if last is None:
            return 0
        elapsed_sec = time.time() - float(last)
        return max(0, int(elapsed_sec // TICK_INTERVAL))
    except Exception:
        return 0
