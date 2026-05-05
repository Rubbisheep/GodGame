"""
《无名之界》— 命令行神明模拟器

指令：
  赐予 <物品>        消耗10神力，赐予部落一件物品
  施放 <奇迹>        消耗50神力，降下神迹
  回应 <名字> <类型>  回应NPC的祈祷 (类型: 答应/无视/惩戒/赐福)
  凝视 <名字/地点>   深度洞察某人或某地
  状态               世界概况
  地图               世界感知图
  人群               命名居民列表
  人 <名字>          查看某人的完整人生事件流
  人物               特殊人物
  变异               活跃变异
  神话               世界神话库
  模块               自生成扩展系统
  祈祷               查看当前祈祷列表
  帮助 / 退出
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.panel import Panel
from rich.text import Text

from state_manager import StateManager, SAVE_FILE
from core.models import MIRACLE_COST, GIFT_COST
from core.simulator import WorldSimulator, calc_catchup_years
import cli.display as display


def _help():
    t = Text()
    t.append("  赐予 <物品>        ", style="cyan")
    t.append("— 将神力凝结为实物降入人间（消耗10神力）\n", style="dim")
    t.append("  施放 <奇迹>        ", style="cyan")
    t.append("— 以神力直接干预世界法则（消耗50神力）\n", style="dim")
    t.append("  回应 <名字> <类型> ", style="cyan")
    t.append("— 回应祈祷（类型：答应/无视/惩戒/赐福）\n", style="dim")
    t.append("  凝视 <名字/地点>   ", style="cyan")
    t.append("— 深度洞察某人或某地（不消耗回合）\n", style="dim")
    t.append("  状态               ", style="cyan")
    t.append("— 世界概况（含当前神力）\n", style="dim")
    t.append("  地图               ", style="cyan")
    t.append("— 世界感知图\n", style="dim")
    t.append("  人群               ", style="cyan")
    t.append("— 命名居民列表\n", style="dim")
    t.append("  人 <名字>          ", style="cyan")
    t.append("— 某人的完整人生事件流\n", style="dim")
    t.append("  人物               ", style="cyan")
    t.append("— 特殊人物\n", style="dim")
    t.append("  变异               ", style="cyan")
    t.append("— 活跃变异\n", style="dim")
    t.append("  神话               ", style="cyan")
    t.append("— 世界神话库\n", style="dim")
    t.append("  模块               ", style="cyan")
    t.append("— 世界自生成扩展系统\n", style="dim")
    t.append("  祈祷               ", style="cyan")
    t.append("— 当前祈祷列表\n\n", style="dim")
    t.append("  神力：你行使意志的能量。每年自然积累，居民的信仰会加速积累。\n", style="italic dim")
    t.append("  初始神力20；赐予消耗10，施放消耗50。他们目前还不知道你的存在。", style="italic dim")
    display.console.print(Panel(t, title="[bold]指令列表[/bold]", border_style="dim"))


def _flush_events(sim: WorldSimulator):
    events = sim.drain()
    if events:
        display.console.print()
        for e in events:
            display.print_event(e)


def run():
    display.print_banner()

    manager = StateManager()

    if SAVE_FILE.exists():
        catchup = calc_catchup_years(SAVE_FILE)
        manager.load()
        display.console.print("\n  你的注意力重新落回这个世界。", style="italic dim")
        if catchup > 0:
            display.console.print(
                f"  你离开的时间里，世界又走过了约 [bold]{catchup}[/bold] 年……",
                style="dim"
            )
    else:
        catchup = 0
        display.console.print("  正在创世……", style="dim italic")
        opening = manager.initialize()
        display.console.print()
        display.console.print(opening, style="italic")

    sim = WorldSimulator(manager)
    sim.start(catchup_years=catchup)

    _flush_events(sim)

    def _status():
        display.render_status(manager.world, manager.pool, manager.loader)

    sim.player_query(_status)
    _help()

    while True:
        _flush_events(sim)

        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            display.console.print("\n  你的目光从这个世界上移开了。", style="italic dim")
            sim.stop()
            sys.exit(0)

        if not raw:
            continue

        _flush_events(sim)

        parts = raw.split(maxsplit=2)
        cmd = parts[0]
        arg1 = parts[1].strip() if len(parts) > 1 else ""
        arg2 = parts[2].strip() if len(parts) > 2 else ""

        # ── 纯展示指令 ────────────────────────────────────────────────────────

        if cmd in ("退出", "quit", "exit"):
            sim.stop()
            display.console.print("  你的意识退潮，这个世界仍在继续。", style="italic dim")
            break

        elif cmd == "帮助":
            _help()
            continue

        elif cmd == "状态":
            sim.player_query(
                lambda: display.render_status(manager.world, manager.pool, manager.loader)
            )
            continue

        elif cmd == "地图":
            sim.player_query(
                lambda: display.render_world_map(manager.world, manager.pool)
            )
            continue

        elif cmd == "人群":
            sim.player_query(
                lambda: display.render_population_table(manager.pool, manager.world)
            )
            continue

        elif cmd == "人":
            if not arg1:
                display.console.print("  用法：人 <名字>", style="dim")
                continue
            def _show_person(name=arg1):
                person = manager.pool.get_by_name(name)
                if not person:
                    display.console.print(
                        f"  未找到「{name}」，输入「人群」查看所有人名。", style="red dim"
                    )
                    return
                display.render_person_timeline(person, manager.world)
            sim.player_query(_show_person)
            continue

        elif cmd == "人物":
            sim.player_query(
                lambda: display.render_entities(manager.active_entities)
            )
            continue

        elif cmd == "变异":
            sim.player_query(
                lambda: display.render_mutations(manager.world)
            )
            continue

        elif cmd == "神话":
            sim.player_query(
                lambda: display.render_myths(manager.myths)
            )
            continue

        elif cmd == "祈祷":
            sim.player_query(
                lambda: display.render_prayers(manager.pool.pending_prayers())
            )
            continue

        elif cmd == "模块":
            sim.player_query(
                lambda: display.render_modules(manager.loader)
            )
            continue

        # ── 会推进回合的指令 ──────────────────────────────────────────────────

        elif cmd in ("赐予", "gift"):
            if not arg1:
                display.console.print("  用法：赐予 <物品名>", style="dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 赐予：{arg1}]", style="cyan")
            result = sim.player_act(manager.apply_action, "赐予", arg1, GIFT_COST)
            display.console.print(result, style="white")

        elif cmd in ("施放", "miracle"):
            if not arg1:
                display.console.print("  用法：施放 <奇迹名>", style="dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 施放：{arg1}]", style="bright_yellow")
            result = sim.player_act(manager.apply_action, "施放", arg1, MIRACLE_COST)
            display.console.print(result, style="white")

        elif cmd == "回应":
            if not arg1 or not arg2:
                display.console.print("  用法：回应 <名字> <答应/无视/惩戒/赐福>", style="dim")
                continue
            type_map = {"答应": "answer", "无视": "ignore", "惩戒": "punish", "赐福": "bless"}
            rtype = type_map.get(arg2)
            if not rtype:
                display.console.print("  回应类型只能是：答应 / 无视 / 惩戒 / 赐福", style="red dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 回应祈祷：{arg1}]", style="yellow")
            result = sim.player_act(manager.respond_to_prayer, arg1, rtype)
            display.console.print(result, style="white")

        elif cmd == "凝视":
            if not arg1:
                display.console.print("  用法：凝视 <名字或地点>", style="dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 神明凝视：{arg1}]", style="magenta")
            result = sim.player_query(manager.divine_gaze, arg1)
            display.console.print(result, style="white")
            continue

        else:
            display.console.print(
                f"  未知指令「{cmd}」。输入「帮助」查看指令列表。", style="red dim"
            )
            continue

        # ── 行动后状态摘要 ────────────────────────────────────────────────────
        display.print_divider()
        sim.player_query(
            lambda: display.render_status(manager.world, manager.pool, manager.loader)
        )


if __name__ == "__main__":
    run()
