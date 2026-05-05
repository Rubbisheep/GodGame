"""
《无名之界》— 命令行神明模拟器

指令：
  赐予 <物品>       消耗10信仰，赐予部落一件物品
  施放 <奇迹>       消耗50信仰，降下神迹
  回应 <名字> <类型> 回应NPC的祈祷 (类型: 答应/无视/惩戒/赐福)
  凝视 <名字/地点>  深度洞察某人或某地
  状态              世界概况
  人群              命名居民列表
  人 <名字>         查看某人的完整人生事件流
  人物              特殊人物
  变异              活跃变异
  神话              世界神话库
  模块              自生成扩展系统
  祈祷              查看当前祈祷列表
  帮助 / 退出
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from state_manager import StateManager, SAVE_FILE
from models import MIRACLE_COST, GIFT_COST
from simulator import WorldSimulator, calc_catchup_years

DIV = "─" * 56


def _help():
    print(
        "\n指令："
        "\n  赐予 <物品>        — 消耗10信仰"
        "\n  施放 <奇迹>        — 消耗50信仰"
        "\n  回应 <名字> <类型> — 回应祈祷（类型：答应/无视/惩戒/赐福）"
        "\n  凝视 <名字/地点>   — 神明深度洞察"
        "\n  状态               — 世界概况"
        "\n  人群               — 命名居民列表"
        "\n  人 <名字>          — 某人的完整人生事件流"
        "\n  人物               — 特殊人物"
        "\n  变异               — 活跃变异"
        "\n  神话               — 世界神话库"
        "\n  模块               — 世界自生成扩展系统"
        "\n  祈祷               — 当前祈祷列表"
    )


def _flush_events(sim: WorldSimulator):
    """打印所有后台积累的世界事件。"""
    events = sim.drain()
    if events:
        print()
        for e in events:
            if e.strip():
                print(e)


def run():
    print(f"\n{DIV}")
    print("  《无名之界》")
    print(DIV)

    manager = StateManager()

    if SAVE_FILE.exists():
        catchup = calc_catchup_years(SAVE_FILE)
        manager.load()
        print("世界重新进入你的视野。")
        if catchup > 0:
            print(f"你离开期间大约过去了 {catchup} 年……")
    else:
        catchup = 0
        print("正在创世……")
        manager.initialize()

    sim = WorldSimulator(manager)
    sim.start(catchup_years=catchup)

    # 打印离线补偿事件
    _flush_events(sim)

    print("\n你是一个正在注视这个世界的存在。")
    print("一切都还很原始，但某些东西已经开始躁动。")
    _help()

    def _status():
        print(f"\n{DIV}")
        print(manager.world.summary())
        print(f"  命名居民：{len(manager.pool.living)}人  已故存档：{len(manager.pool.archived)}人")
        if manager.loader.active_names():
            print(f"  活跃模块：{', '.join(manager.loader.active_names())}")
        prayers = manager.pool.pending_prayers()
        if prayers:
            print(f"  祈祷等待中：{', '.join(p.name for p in prayers)}")
        print(DIV)

    sim.player_query(_status)

    while True:
        # 每次等待输入前先冲刷后台事件
        _flush_events(sim)

        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n你的目光从这个世界上移开了。")
            sim.stop()
            sys.exit(0)

        if not raw:
            continue

        # 输入后再冲一次，避免后台线程恰好在这时产生事件
        _flush_events(sim)

        parts = raw.split(maxsplit=2)
        cmd = parts[0]
        arg1 = parts[1].strip() if len(parts) > 1 else ""
        arg2 = parts[2].strip() if len(parts) > 2 else ""

        # ── 纯展示指令（只读查询，不推进回合） ─────────────────────────────

        if cmd in ("退出", "quit", "exit"):
            sim.stop()
            print("你的意识退潮，这个世界仍在继续。")
            break

        elif cmd == "帮助":
            _help()
            continue

        elif cmd == "状态":
            sim.player_query(_status)
            continue

        elif cmd == "人群":
            def _show_crowd():
                print(f"\n{DIV}")
                print("【命名居民】")
                print(manager.pool.summary_list(manager.world.world_year))
                if manager.pool.archived:
                    names = ", ".join(p.name for p in manager.pool.archived[-6:])
                    print(f"\n  已故：{names}")
                print(DIV)
            sim.player_query(_show_crowd)
            continue

        elif cmd == "人":
            if not arg1:
                print("用法：人 <名字>")
                continue
            def _show_person(name=arg1):
                person = manager.pool.get_by_name(name)
                if not person:
                    print(f"未找到「{name}」，输入「人群」查看所有人名。")
                    return
                print(f"\n{DIV}")
                print(person.display_timeline(manager.world.world_year))
                print(DIV)
            sim.player_query(_show_person)
            continue

        elif cmd == "人物":
            def _show_entities():
                print(f"\n{DIV}")
                print("【特殊人物】")
                print(manager.entities_summary())
                print(DIV)
            sim.player_query(_show_entities)
            continue

        elif cmd == "变异":
            def _show_mutations():
                print(f"\n{DIV}")
                print("【活跃变异】")
                print(manager.mutations_summary())
                print(DIV)
            sim.player_query(_show_mutations)
            continue

        elif cmd == "神话":
            def _show_myths():
                print(f"\n{DIV}")
                print("【世界神话】")
                print(manager.myths_summary())
                print(DIV)
            sim.player_query(_show_myths)
            continue

        elif cmd == "祈祷":
            def _show_prayers():
                print(f"\n{DIV}")
                print("【当前祈祷】")
                prayers = manager.pool.pending_prayers()
                if prayers:
                    for p in prayers:
                        print(f"  · {p.name}：{p.prayer_pending}")
                    print("\n  用「回应 <名字> <答应/无视/惩戒/赐福>」来回应")
                else:
                    print("  （当前无人祈祷）")
                print(DIV)
            sim.player_query(_show_prayers)
            continue

        elif cmd == "模块":
            def _show_modules():
                print(f"\n{DIV}")
                print("【世界扩展模块】")
                active = manager.loader.active_names()
                broken = manager.loader.broken_names()
                if active:
                    for n in active:
                        desc = manager.loader.get_description(n)
                        print(f"  + {n}  {desc}")
                else:
                    print("  （尚无涌现模块）")
                if broken:
                    print(f"\n  修复中：{', '.join(broken)}")
                pending = [n for n, _, _ in manager._upgrade_requests]
                if pending:
                    print(f"  升级请求中：{', '.join(pending)}")
                print(DIV)
            sim.player_query(_show_modules)
            continue

        # ── 会推进回合的指令 ─────────────────────────────────────────────────

        elif cmd in ("赐予", "gift"):
            if not arg1:
                print("用法：赐予 <物品名>")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            print(f"\n[{year_str} · 赐予：{arg1}]")
            result = sim.player_act(manager.apply_action, "赐予", arg1, GIFT_COST)
            print(result)

        elif cmd in ("施放", "miracle"):
            if not arg1:
                print("用法：施放 <奇迹名>")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            print(f"\n[{year_str} · 施放：{arg1}]")
            result = sim.player_act(manager.apply_action, "施放", arg1, MIRACLE_COST)
            print(result)

        elif cmd == "回应":
            if not arg1 or not arg2:
                print("用法：回应 <名字> <答应/无视/惩戒/赐福>")
                continue
            type_map = {"答应": "answer", "无视": "ignore", "惩戒": "punish", "赐福": "bless"}
            rtype = type_map.get(arg2)
            if not rtype:
                print("回应类型只能是：答应 / 无视 / 惩戒 / 赐福")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            print(f"\n[{year_str} · 回应祈祷：{arg1}]")
            result = sim.player_act(manager.respond_to_prayer, arg1, rtype)
            print(result)

        elif cmd == "凝视":
            if not arg1:
                print("用法：凝视 <名字或地点>")
                continue
            year_str = sim.player_query(lambda: manager.world.year_display())
            print(f"\n[{year_str} · 神明凝视：{arg1}]")
            result = sim.player_query(manager.divine_gaze, arg1)
            print(result)
            continue  # 凝视不触发额外回合结算

        else:
            print(f"未知指令「{cmd}」。输入「帮助」查看指令列表。")
            continue

        # ── 行动后状态摘要 ───────────────────────────────────────────────────
        sim.player_query(_status)


if __name__ == "__main__":
    run()
