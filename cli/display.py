"""
CLI 可视化层。依赖 rich 库，提供所有玩家可见的渲染函数。
所有函数直接打印到终端，不返回值。
"""
import hashlib
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

console = Console(highlight=False)

_MAP_W, _MAP_H = 22, 11

# ── 内部工具 ────────────────────────────────────────────────────────────────

def _faith_bar(value: float, width: int = 10) -> Text:
    filled = int(value * width)
    t = Text()
    if value < 0.3:     color = "red"
    elif value < 0.6:   color = "yellow"
    else:               color = "green"
    t.append("●" * filled, style=color)
    t.append("·" * (width - filled), style="grey42")
    t.append(f"  {value:.0%}", style="dim")
    return t


def _power_bar(faith: int, width: int = 16) -> Text:
    capped = min(faith, 200)
    filled = int(capped / 200 * width)
    t = Text()
    t.append("◆" * filled, style="cyan")
    t.append("·" * (width - filled), style="grey42")
    t.append(f"  {faith}", style="bright_white")
    return t


def _name_pos(name: str, w: int, h: int) -> tuple[int, int]:
    h_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return (h_val % w), ((h_val >> 16) % h)


def _terrain(x: int, y: int, seed: int) -> tuple[str, str]:
    # 粗粒度分块，2x2 格子共享地形，形成成片的区域感
    h = int(hashlib.md5(f"{x//2},{y//2},{seed // 16}".encode()).hexdigest(), 16) % 100
    if h < 12:  return "~", "blue"       # 水域
    if h < 32:  return "T", "green"      # 林地
    if h < 42:  return "^", "yellow"     # 山地
    return ".", "grey30"                  # 平原


# ── 渲染函数 ─────────────────────────────────────────────────────────────────

def render_status(world, pool, loader, speed_multiplier: float = 1.0):
    """主状态面板：世界此刻的快照。"""
    avg_faith = sum(p.faith_in_god for p in pool.living) / max(1, len(pool.living))
    prayers = [p for p in pool.living if p.prayer_pending]
    notables = [p for p in pool.living if p.is_notable]

    # 左：世界此刻
    left = Text()
    left.append(f"  {world.year_display()}\n", style="bold bright_white")
    left.append(f"  ─ {world.current_era} ─\n\n", style="italic grey58")
    left.append("  神力    ", style="cyan")
    left.append(_power_bar(world.faith))
    left.append("\n  信仰    ", style="cyan")
    left.append(_faith_bar(avg_faith))
    left.append(f"\n\n  人口    ", style="dim")
    left.append(f"{world.population}", style="bright_white")
    left.append(f"      命名居民  ", style="dim")
    left.append(f"{len(pool.living)}", style="bright_white")
    if pool.archived:
        left.append(f"  已故 {len(pool.archived)}", style="red dim")
    if speed_multiplier != 1.0:
        left.append(f"\n\n  时流    ", style="dim")
        left.append(f"{speed_multiplier:g}x", style="magenta")

    # 右：世界正在成为什么
    right = Text()
    tags = "、".join(world.tech_and_culture_tags) or "—"
    tend = "、".join(world.dominant_tendencies()) or "—"
    right.append("  掌握  ", style="dim")
    right.append(f"{tags}\n", style="white")
    right.append("  倾向  ", style="dim")
    right.append(f"{tend}\n", style="white")

    if loader.active_names():
        right.append("\n  法则  ", style="dim")
        right.append(f"{' · '.join(loader.active_names())}", style="green")
    if loader.broken_names():
        right.append("\n  裂缝  ", style="red dim")
        right.append(f"{' · '.join(loader.broken_names())}", style="red")

    if prayers:
        right.append("\n\n  祈祷\n", style="yellow dim")
        for p in prayers[:4]:
            right.append(f"    ◆  {p.name}\n", style="yellow")
        if len(prayers) > 4:
            right.append(f"    … 另有 {len(prayers)-4} 人\n", style="yellow dim")

    if notables:
        right.append("\n  异人  ", style="dim")
        right.append(f"{'、'.join(n.name for n in notables)}", style="bright_white")

    console.print(Columns(
        [Panel(left, box=box.SIMPLE, padding=(0, 1)),
         Panel(right, box=box.SIMPLE, padding=(0, 1))],
        equal=True
    ))


def render_world_map(world, pool):
    """世界感知图：粗笔草图风格。每格 2 字符宽，地形成片。"""
    # 每个逻辑格子渲染 2 个字符，通过重复地形符号形成「笔触」
    grid_char: list[list[str]] = [[" " for _ in range(_MAP_W)] for _ in range(_MAP_H)]
    grid_style: list[list[str]] = [["grey30" for _ in range(_MAP_W)] for _ in range(_MAP_H)]

    seed = world.world_year
    for y in range(_MAP_H):
        for x in range(_MAP_W):
            ch, st = _terrain(x, y, seed)
            grid_char[y][x] = ch
            grid_style[y][x] = st

    # NPC 位置：用汉字（2 字符宽）直接覆盖地形
    npc_cells: dict[tuple[int, int], object] = {}
    for p in pool.living:
        px, py = _name_pos(p.name, _MAP_W - 1, _MAP_H)
        npc_cells[(px, py)] = p

    # 渲染主地图
    map_text = Text()
    for y, (row_c, row_s) in enumerate(zip(grid_char, grid_style)):
        map_text.append("  ")
        x = 0
        while x < _MAP_W:
            if (x, y) in npc_cells:
                p = npc_cells[(x, y)]
                if p.prayer_pending:
                    map_text.append(p.name[0], style="bold yellow on grey11")
                elif p.faith_in_god > 0.4:
                    map_text.append(p.name[0], style="bold bright_cyan on grey11")
                else:
                    map_text.append(p.name[0], style="bold white on grey11")
                x += 1  # 汉字占 2 显示宽度，相当于占用一格但视觉宽度匹配两个 ASCII 地形字符
            else:
                ch, st = row_c[x], row_s[x]
                map_text.append(ch + ch, style=st)
                x += 1
        map_text.append("\n")

    # 图例
    legend = Text("\n  ")
    legend.append(".. ", style="grey30")
    legend.append("平原   ", style="dim")
    legend.append("~~ ", style="blue")
    legend.append("水域   ", style="dim")
    legend.append("TT ", style="green")
    legend.append("林地   ", style="dim")
    legend.append("^^ ", style="yellow")
    legend.append("山地", style="dim")

    # 右侧居民名单
    roster = Text()
    roster.append("  居民\n\n", style="bold dim")
    for p in sorted(pool.living, key=lambda x: (not x.is_notable, x.birth_year)):
        filled = int(p.faith_in_god * 5)
        bar = "●" * filled + "·" * (5 - filled)
        if p.prayer_pending:
            flag, nstyle = "◆", "yellow"
        elif p.is_notable:
            flag, nstyle = "★", "bright_white"
        else:
            flag, nstyle = " ", "white"
        roster.append(f"  {flag} {p.name}  ", style=nstyle)
        roster.append(bar + "\n", style="cyan dim")
    if pool.archived:
        roster.append(f"\n  已故 {len(pool.archived)} 人", style="red dim")

    map_panel = Panel(Text.assemble(map_text, legend), border_style="grey30",
                      padding=(0, 1))
    roster_panel = Panel(roster, border_style="grey30", padding=(0, 1))

    console.print(
        f"\n  [bold]世界感知图[/bold]  "
        f"[dim]{world.year_display()} · {world.current_era}[/dim]"
    )
    console.print(Columns([map_panel, roster_panel], equal=False))


def render_population_table(pool, world):
    """命名居民表格：姓名/年龄/阶段/信仰/特质/状态。"""
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan",
              border_style="grey35")
    t.add_column("姓名", style="bright_white", min_width=6)
    t.add_column("年龄", justify="right", min_width=4)
    t.add_column("阶段", min_width=4)
    t.add_column("信仰", min_width=14)
    t.add_column("特质")
    t.add_column("", min_width=2)  # 标记列

    for p in sorted(pool.living, key=lambda x: x.birth_year):
        age = p.age(world.world_year)
        stage = p.life_stage(world.world_year)
        faith_t = _faith_bar(p.faith_in_god, 8)
        traits = "、".join(p.traits)
        flags = ""
        if p.is_notable:  flags += "★"
        if p.prayer_pending: flags += "✦"
        t.add_row(p.name, str(age), stage, faith_t, traits, flags)

    if pool.archived:
        console.print(t)
        dead_names = "、".join(p.name for p in pool.archived[-8:])
        console.print(f"  [dim]已故：{dead_names}[/dim]")
    else:
        console.print(t)


def render_person_timeline(person, world):
    """某人的完整人生时间线。"""
    age = person.age(world.world_year)
    if person.death_year:
        status = f"已故 · 享年 {age}"
        status_style = "red dim"
    else:
        status = f"{person.life_stage(world.world_year)} · {age}岁"
        status_style = "bright_white"

    header = Text()
    header.append(f"  {person.name}", style="bold bright_white")
    if person.is_notable:
        header.append("  ★", style="bright_yellow")
    header.append(f"    {status}\n", style=status_style)
    header.append(f"  ─" * 30 + "\n", style="grey30")

    header.append(f"  性格    ", style="dim")
    header.append(f"{'、'.join(person.traits)}\n", style="white")
    header.append(f"  出身    ", style="dim")
    header.append(f"{person.background}\n", style="white")
    header.append(f"  信仰    ", style="dim")
    header.append(_faith_bar(person.faith_in_god))

    if person.parent_names:
        header.append(f"\n  父母    ", style="dim")
        header.append(f"{'、'.join(person.parent_names)}", style="white")
    if person.children_names:
        header.append(f"\n  子女    ", style="dim")
        header.append(f"{'、'.join(person.children_names)}", style="white")
    if person.inherited_memory:
        header.append(f"\n  遗记    ", style="dim")
        header.append(f"{person.inherited_memory}", style="italic grey62")

    if not person.life_events:
        console.print(Panel(
            Text.assemble(header, Text("\n\n  （暂无记录）", style="dim")),
            border_style="grey30", padding=(1, 2)
        ))
        return

    by_year: dict[int, list] = {}
    for ev in person.life_events:
        by_year.setdefault(ev.year, []).append(ev)

    type_icons = {
        "birth":      ("○", "green"),         "witness":    ("◎", "cyan"),
        "mutation":   ("◉", "yellow"),        "encounter":  ("◇", "blue"),
        "autonomous": ("→", "grey62"),        "death":      ("✕", "red"),
        "growth":     ("↑", "green"),         "prayer":     ("◆", "yellow"),
        "miracle":    ("✦", "bright_yellow"), "divine":     ("◇", "magenta"),
        "memory":     ("~", "grey50"),
    }
    labels = {
        "birth": "出生", "witness": "见证", "mutation": "变异",
        "encounter": "相遇", "autonomous": "自发", "death": "离世",
        "growth": "成长", "prayer": "祈祷", "miracle": "神迹",
        "divine": "神明", "memory": "遗记",
    }

    timeline = Text.assemble(header, Text("\n\n"))
    for yr in sorted(by_year.keys()):
        timeline.append(f"\n  · 第 {yr} 年\n", style="grey58")
        for ev in by_year[yr]:
            icon, style = type_icons.get(ev.event_type, ("·", "white"))
            label = labels.get(ev.event_type, ev.event_type)
            timeline.append(f"      {icon}  ", style=style)
            timeline.append(f"{label}  ", style="dim")
            timeline.append(f"{ev.description}\n", style="white")

    console.print(Panel(timeline, border_style="grey30", padding=(1, 2)))


def render_prayers(prayers: list):
    """等待回应的祈祷列表。"""
    if not prayers:
        console.print(Panel("  （当前无人祈祷）", title="祈祷", border_style="dim"))
        return
    content = Text()
    for p in prayers:
        content.append(f"  {p.name}  ", style="bright_white")
        content.append(p.prayer_pending + "\n", style="italic")
    content.append("\n  用「回应 <名字> <答应/无视/惩戒/赐福>」来回应", style="dim")
    console.print(Panel(content, title="当前祈祷", border_style="yellow dim"))


def render_modules(loader):
    """自生成模块状态面板。"""
    active = loader.active_names()
    broken = loader.broken_names()
    if not active and not broken:
        console.print(Panel("  （世界尚无法则涌现）", title="法则", border_style="dim"))
        return
    content = Text()
    for n in active:
        desc = loader.get_description(n)
        content.append(f"  ✓ {n}  ", style="green")
        content.append(desc + "\n", style="dim")
    for n in broken:
        content.append(f"  ✗ {n}（修复中）\n", style="red")
    console.print(Panel(content, title="法则", border_style="dim"))


def render_story(new_events: list):
    """显示尚未读过的新事件。"""
    if not new_events:
        console.print("  （当前无新动态，世界正在运转）", style="dim italic")
        return
    console.print(f"\n  [bold]新动态[/bold]  [dim]{len(new_events)} 条[/dim]")
    print_divider()
    for entry in new_events:
        print_event(entry)
    print_divider()


def render_oracle(question: str, result: dict):
    """展示神明自询的回答。"""
    known = result.get("known", False)
    answer = result.get("answer", "")
    t = Text()
    t.append(f"  问：{question}\n\n", style="dim")
    if known:
        t.append(f"  {answer}", style="italic white")
    else:
        t.append(f"  {answer}", style="italic dim")
    console.print(Panel(t, title="[bold]神明自询[/bold]",
                        border_style="magenta dim" if known else "dim"))


_EVENT_STYLES = [
    (("[离世]", "✕"),               "·", "red"),
    (("[新生]",),                    "○", "green"),
    (("[祈祷]",),                    "◆", "yellow"),
    (("[变异", "扩散"),              "◉", "yellow"),
    (("[法则异常]", "[崩溃]"),       "✕", "red"),
    (("[涌现]", "[系统进化]"),       "✦", "bright_green"),
    (("[自主]",),                    "→", "grey62"),
    (("[异类出现]",),                "★", "bright_yellow"),
    (("[神迹]", "[奇迹]"),           "✦", "bright_yellow"),
    (("[神明凝视]",),                "◇", "magenta"),
]


def print_event(text: str):
    """打印世界事件流（带样式）。"""
    if not text.strip():
        return
    for triggers, marker, color in _EVENT_STYLES:
        if any(tag in text for tag in triggers):
            stripped = text.lstrip("\n ")
            indent = text[:len(text) - len(text.lstrip("\n"))]
            console.print(f"{indent}  {marker}  ", style=color, end="")
            console.print(stripped.lstrip(), style=color if color != "grey62" else "dim")
            return
    console.print(text, style="dim")


def print_banner():
    """开场 banner。"""
    console.print()
    art = Text()
    art.append("     ·   ·                 ·\n", style="grey42")
    art.append("  ·       ", style="grey42")
    art.append("《 无 名 之 界 》", style="bold bright_white")
    art.append("       ·\n", style="grey42")
    art.append("              ·       ·\n", style="grey42")
    art.append("     U N N A M E D   W O R L D\n", style="dim")
    art.append("   ─ ─ ─  a god simulator  ─ ─ ─", style="italic grey58")
    console.print(Panel(art, border_style="grey30", padding=(1, 4)))


def print_divider():
    console.print("─" * 56, style="grey30")
