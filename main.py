"""
《无名之界》— 命令行神明模拟器
输入「帮助」或「help」查看指令列表。
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.panel import Panel
from rich.text import Text

from state_manager import StateManager, SAVE_FILE, GIFT_ABSORB_YEARS, MIRACLE_COOLDOWN_YEARS
from core.models import MIRACLE_COST, GIFT_COST
from core.simulator import WorldSimulator, calc_catchup_years
import cli.display as display


def _help(manager=None):
    yr = manager.world.world_year if manager else "?"
    last_gift = manager._last_gift_year if manager else -999
    last_miracle = manager._last_miracle_year if manager else -999

    gift_wait = max(0, GIFT_ABSORB_YEARS - (yr - last_gift)) if manager else 0
    miracle_wait = max(0, MIRACLE_COOLDOWN_YEARS - (yr - last_miracle)) if manager else 0
    gift_label   = f"冷却中 {gift_wait}年" if gift_wait > 0 else "可用"
    gift_style   = "red" if gift_wait > 0 else "green"
    miracle_label  = f"冷却中 {miracle_wait}年" if miracle_wait > 0 else "可用"
    miracle_style  = "red" if miracle_wait > 0 else "green"

    t = Text()
    t.append("── 干预 ──\n", style="bold dim")
    t.append("  赐予 / gift   <物品>        ", style="cyan")
    t.append("神力10  ", style="dim")
    t.append(gift_label, style=gift_style)
    t.append("  例：赐予 火种 / gift 石斧\n", style="dim italic")
    t.append("  施放 / cast   <奇迹>        ", style="cyan")
    t.append("神力50  ", style="dim")
    t.append(miracle_label, style=miracle_style)
    t.append("  例：施放 丰收 / cast 瘟疫治愈\n", style="dim italic")
    t.append("  回应 / respond <名字> <类型>", style="cyan")
    t.append("  类型：答应 / 无视 / 惩戒 / 赐福\n", style="dim")
    t.append("  凝视 / gaze   <名字或地点>  ", style="cyan")
    t.append("深度洞察，不消耗回合\n\n", style="dim")

    t.append("── 查看 ──\n", style="bold dim")
    t.append("  状态 / status / s  ", style="cyan")
    t.append("世界概况（神力·人口·倾向）\n", style="dim")
    t.append("  地图 / map    / m  ", style="cyan")
    t.append("世界感知图\n", style="dim")
    t.append("  人群 / people      ", style="cyan")
    t.append("命名居民列表\n", style="dim")
    t.append("  人 / person <名字> ", style="cyan")
    t.append("某人的完整人生时间线\n", style="dim")
    t.append("  人物 / entities    ", style="cyan")
    t.append("特殊人物\n", style="dim")
    t.append("  神话 / myths       ", style="cyan")
    t.append("世界神话库\n", style="dim")
    t.append("  祈祷 / prayers     ", style="cyan")
    t.append("当前等待回应的祈祷\n", style="dim")
    t.append("  模块 / modules     ", style="cyan")
    t.append("世界自生成扩展模块\n\n", style="dim")

    t.append("  退出 / quit / exit", style="dim")

    display.console.print(Panel(t, title="[bold]指令列表[/bold]", border_style="dim"))


def _flush_events(sim: WorldSimulator, manager: StateManager, auto_status: bool = True):
    events, bg_ticked = sim.drain()
    if events:
        display.console.print()
        for e in events:
            display.print_event(e)
        if auto_status and bg_ticked:
            display.print_divider()
            sim.player_query(
                lambda: display.render_status(manager.world, manager.pool, manager.loader)
            )


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

    _flush_events(sim, manager, auto_status=False)

    sim.player_query(
        lambda: display.render_status(manager.world, manager.pool, manager.loader)
    )
    _help(manager)

    while True:
        _flush_events(sim, manager)

        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            display.console.print("\n  你的目光从这个世界上移开了。", style="italic dim")
            sim.stop()
            sys.exit(0)

        if not raw:
            continue

        _flush_events(sim, manager)

        parts = raw.split(maxsplit=2)
        cmd = parts[0]
        arg1 = parts[1].strip() if len(parts) > 1 else ""
        arg2 = parts[2].strip() if len(parts) > 2 else ""

        # ── 退出 ──────────────────────────────────────────────────────────────
        if cmd in ("退出", "quit", "exit"):
            sim.stop()
            display.console.print("  你的意识退潮，这个世界仍在继续。", style="italic dim")
            break

        # ── 查看指令 ──────────────────────────────────────────────────────────
        elif cmd in ("帮助", "help", "h", "?"):
            sim.player_query(lambda: _help(manager))

        elif cmd in ("状态", "status", "s"):
            sim.player_query(
                lambda: display.render_status(manager.world, manager.pool, manager.loader)
            )

        elif cmd in ("地图", "map", "m"):
            sim.player_query(
                lambda: display.render_world_map(manager.world, manager.pool)
            )

        elif cmd in ("人群", "people", "pop"):
            sim.player_query(
                lambda: display.render_population_table(manager.pool, manager.world)
            )

        elif cmd in ("人", "person"):
            if not arg1:
                display.console.print("  用法：人 <名字>  /  person <name>", style="dim")
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

        elif cmd in ("人物", "entities", "entity"):
            sim.player_query(lambda: display.render_entities(manager.active_entities))

        elif cmd in ("神话", "myths"):
            sim.player_query(lambda: display.render_myths(manager.myths))

        elif cmd in ("祈祷", "prayers"):
            sim.player_query(
                lambda: display.render_prayers(manager.pool.pending_prayers())
            )

        elif cmd in ("模块", "modules"):
            sim.player_query(lambda: display.render_modules(manager.loader))

        # ── 干预指令（推进回合）──────────────────────────────────────────────
        elif cmd in ("赐予", "gift", "give"):
            if not arg1:
                display.console.print("  用法：赐予 <物品>  /  gift 火种", style="dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 赐予：{arg1}]", style="cyan")
            result = sim.player_act(manager.apply_action, "赐予", arg1, GIFT_COST)
            display.console.print(result, style="white")
            display.print_divider()
            sim.player_query(
                lambda: display.render_status(manager.world, manager.pool, manager.loader)
            )

        elif cmd in ("施放", "cast", "miracle"):
            if not arg1:
                display.console.print("  用法：施放 <奇迹>  /  cast 丰收", style="dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 施放：{arg1}]", style="bright_yellow")
            result = sim.player_act(manager.apply_action, "施放", arg1, MIRACLE_COST)
            display.console.print(result, style="white")
            display.print_divider()
            sim.player_query(
                lambda: display.render_status(manager.world, manager.pool, manager.loader)
            )

        elif cmd in ("回应", "respond"):
            if not arg1 or not arg2:
                display.console.print(
                    "  用法：回应 <名字> <答应/无视/惩戒/赐福>", style="dim"
                )
                continue
            type_map = {"答应": "answer", "无视": "ignore", "惩戒": "punish", "赐福": "bless"}
            rtype = type_map.get(arg2)
            if not rtype:
                display.console.print(
                    "  回应类型只能是：答应 / 无视 / 惩戒 / 赐福", style="red dim"
                )
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 回应祈祷：{arg1}]", style="yellow")
            result = sim.player_act(manager.respond_to_prayer, arg1, rtype)
            display.console.print(result, style="white")
            display.print_divider()
            sim.player_query(
                lambda: display.render_status(manager.world, manager.pool, manager.loader)
            )

        elif cmd in ("凝视", "gaze"):
            if not arg1:
                display.console.print("  用法：凝视 <名字或地点>  /  gaze <name>", style="dim")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            display.print_divider()
            display.console.print(f"  [{year_str} · 神明凝视：{arg1}]", style="magenta")
            result = sim.player_query(manager.divine_gaze, arg1)
            display.console.print(result, style="white")

        else:
            display.console.print(
                f"  未知指令「{cmd}」。输入「help」查看指令列表。", style="red dim"
            )


if __name__ == "__main__":
    run()
