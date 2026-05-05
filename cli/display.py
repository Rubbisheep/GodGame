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

_MAP_W, _MAP_H = 30, 10

# ── 内部工具 ────────────────────────────────────────────────────────────────

def _faith_bar(value: float, width: int = 10) -> Text:
    filled = int(value * width)
    t = Text()
    if value < 0.3:
        color = "red"
    elif value < 0.6:
        color = "yellow"
    else:
        color = "green"
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="grey50")
    t.append(f" {value:.0%}", style="white")
    return t


def _power_bar(faith: int, width: int = 16) -> Text:
    capped = min(faith, 200)
    filled = int(capped / 200 * width)
    t = Text()
    t.append("▓" * filled, style="cyan")
    t.append("░" * (width - filled), style="grey50")
    t.append(f"  {faith}", style="bright_white")
    return t


def _name_pos(name: str, w: int, h: int) -> tuple[int, int]:
    h_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return (h_val % w), ((h_val >> 16) % h)


def _terrain(x: int, y: int, seed: int) -> tuple[str, str]:
    h = int(hashlib.md5(f"{x},{y},{seed // 8}".encode()).hexdigest(), 16) % 100
    if h < 8:   return "≈", "blue"       # 水域
    if h < 20:  return "▪", "green"      # 林地
    if h < 27:  return "▲", "yellow"     # 山地
    return " ", "grey35"                  # 平原（留空更清晰）


# ── 渲染函数 ─────────────────────────────────────────────────────────────────

def render_status(world, pool, loader):
    """主状态面板：年份/时代/神力/人口/倾向/模块。"""
    avg_faith = sum(p.faith_in_god for p in pool.living) / max(1, len(pool.living))

    left = Text()
    left.append(f"  {world.year_display()}\n", style="bold bright_white")
    left.append(f"  {world.current_era}\n\n", style="italic dim")
    left.append("  神力  ", style="cyan")
    left.append(_power_bar(world.faith))
    left.append("\n  居民信仰  ", style="cyan")
    left.append(_faith_bar(avg_faith))
    left.append(f"\n\n  人口  {world.population}", style="dim")

    right = Text()
    tags = "、".join(world.tech_and_culture_tags) or "无"
    tend = "、".join(world.dominant_tendencies()) or "无"
    right.append(f"  掌握  {tags}\n", style="dim")
    right.append(f"  倾向  {tend}\n", style="dim")
    right.append(f"  变异  {len(world.active_mutations)} 处\n", style="dim")
    if loader.active_names():
        right.append(f"  模块  {', '.join(loader.active_names())}", style="green dim")
    if loader.broken_names():
        right.append(f"\n  修复中  {', '.join(loader.broken_names())}", style="red dim")

    prayers = [p for p in pool.living if p.prayer_pending]
    if prayers:
        right.append(f"\n\n  祈祷  {', '.join(p.name for p in prayers)}", style="yellow")

    named_living = len(pool.living)
    named_dead = len(pool.archived)
    right.append(f"\n\n  命名居民  {named_living} 人  已故 {named_dead}", style="dim")

    console.print(Columns([Panel(left, box=box.SIMPLE), Panel(right, box=box.SIMPLE)],
                          equal=True))


def render_world_map(world, pool):
    """世界感知图：左侧地图 + 右侧居民名单。"""
    grid_char: list[list[str]] = [[" " for _ in range(_MAP_W)] for _ in range(_MAP_H)]
    grid_style: list[list[str]] = [["grey35" for _ in range(_MAP_W)] for _ in range(_MAP_H)]

    seed = world.world_year
    for y in range(_MAP_H):
        for x in range(_MAP_W):
            ch, st = _terrain(x, y, seed)
            grid_char[y][x] = ch
            grid_style[y][x] = st

    # 变异标记
    mut_symbols = {1: ("◌", "grey70"), 2: ("●", "yellow"), 3: ("⬡", "bright_red")}
    for i, m in enumerate(world.active_mutations):
        mh = int(hashlib.md5(f"{m.mutation_id}{i}".encode()).hexdigest(), 16)
        mx, my = (mh * 7) % _MAP_W, ((mh * 13) >> 8) % _MAP_H
        grid_char[my][mx], grid_style[my][mx] = mut_symbols.get(m.tier, ("?", "white"))

    # NPC：按信仰显示不同颜色，祈祷中显示 ✦
    for p in pool.living:
        px, py = _name_pos(p.name, _MAP_W - 2, _MAP_H)
        if p.prayer_pending:
            grid_char[py][px] = "✦"
            grid_style[py][px] = "bold yellow"
        else:
            grid_char[py][px] = p.name[0]
            grid_style[py][px] = "bold bright_cyan" if p.faith_in_god > 0.3 else "bold white"

    # 渲染地图
    map_text = Text()
    for row_c, row_s in zip(grid_char, grid_style):
        map_text.append(" ")
        for ch, st in zip(row_c, row_s):
            map_text.append(ch + " ", style=st)
        map_text.append("\n")

    legend = Text("\n ")
    legend.append("  平原", style="grey35")
    legend.append("  ≈ 水域", style="blue")
    legend.append("  ▪ 林地", style="green")
    legend.append("  ▲ 山地", style="yellow")
    legend.append("  ⬡ 变异", style="bright_red")
    legend.append("  ✦ 祈祷", style="yellow")

    # 居民名单（右侧面板）
    roster = Text()
    roster.append("  居民\n\n", style="bold dim")
    for p in sorted(pool.living, key=lambda x: x.birth_year):
        bar = "█" * int(p.faith_in_god * 5) + "░" * (5 - int(p.faith_in_god * 5))
        flag = "✦" if p.prayer_pending else ("★" if p.is_notable else " ")
        name_style = "yellow" if p.prayer_pending else ("bright_white" if p.is_notable else "white")
        roster.append(f" {flag} {p.name}", style=name_style)
        roster.append(f"  [{bar}]\n", style="cyan dim")
    if pool.archived:
        roster.append(f"\n  已故 {len(pool.archived)} 人", style="dim")

    left = Panel(Text.assemble(map_text, legend), border_style="dim", padding=(0, 0))
    right = Panel(roster, border_style="dim", padding=(0, 0))

    console.print(
        f"  [bold]世界感知图[/bold]  "
        f"[dim]{world.year_display()} · {world.current_era}[/dim]"
    )
    console.print(Columns([left, right], equal=False))


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
    """某人的完整人生时间线：信仰条/血脉/事件流。"""
    status = ("已故" if person.death_year
              else f"{person.life_stage(world.world_year)} · {person.age(world.world_year)}岁")

    header = Text()
    header.append(f"【{person.name}】  ", style="bold bright_white")
    header.append(status + "\n", style="dim")
    header.append(f"  性格  {'、'.join(person.traits)}\n", style="dim")
    header.append(f"  出身  {person.background}\n", style="dim")
    header.append("  信仰  ")
    header.append(_faith_bar(person.faith_in_god))
    if person.parent_names:
        header.append(f"\n  父母  {', '.join(person.parent_names)}", style="dim")
    if person.children_names:
        header.append(f"\n  子女  {', '.join(person.children_names)}", style="dim")
    if person.inherited_memory:
        header.append(f"\n  遗记  {person.inherited_memory}", style="italic dim")

    if not person.life_events:
        console.print(Panel(Text.assemble(header, Text("\n\n  （暂无记录）", style="dim")),
                            border_style="dim"))
        return

    by_year: dict[int, list] = {}
    for ev in person.life_events:
        by_year.setdefault(ev.year, []).append(ev)

    type_icons = {
        "birth": ("◉", "green"), "witness": ("◎", "cyan"), "mutation": ("⬡", "yellow"),
        "encounter": ("◈", "blue"), "autonomous": ("→", "white"), "death": ("✕", "red"),
        "growth": ("↑", "green"), "prayer": ("✦", "yellow"), "miracle": ("★", "bright_yellow"),
        "divine": ("∞", "magenta"), "memory": ("~", "dim"),
    }

    timeline = Text.assemble(header, Text("\n"))
    for yr in sorted(by_year.keys()):
        timeline.append(f"\n  ── 第{yr}年 ──\n", style="dim")
        for ev in by_year[yr]:
            icon, style = type_icons.get(ev.event_type, ("·", "white"))
            labels = {"birth": "出生", "witness": "见证", "mutation": "变异",
                      "encounter": "相遇", "autonomous": "自发", "death": "离世",
                      "growth": "成长", "prayer": "祈祷", "miracle": "神迹",
                      "divine": "神明感知", "memory": "记忆碎片"}
            label = labels.get(ev.event_type, ev.event_type)
            timeline.append(f"    {icon} [{label}] ", style=style)
            timeline.append(ev.description + "\n", style="white")

    console.print(Panel(timeline, border_style="dim"))


def render_mutations(world):
    """活跃变异面板。"""
    if not world.active_mutations:
        console.print(Panel("  （无活跃变异）", title="变异", border_style="dim"))
        return
    t = Table(box=box.SIMPLE, header_style="bold", border_style="grey35", show_header=True)
    t.add_column("层级", min_width=6)
    t.add_column("目标", min_width=10)
    t.add_column("描述")
    t.add_column("扩散", justify="right", min_width=4)
    tier_info = {1: ("◈ 表层", "grey70"), 2: ("◉ 功能", "yellow"), 3: ("⬡ 本质", "bright_red")}
    for m in world.active_mutations:
        label, style = tier_info.get(m.tier, ("?", "white"))
        t.add_row(Text(label, style=style), m.target_name, m.description, str(m.spread_count))
    console.print(Panel(t, title="活跃变异", border_style="dim"))


def render_myths(myths: list):
    """世界神话库展示。"""
    if not myths:
        console.print(Panel("  （世界尚无神话）", title="世界神话", border_style="dim"))
        return
    content = Text()
    for m in myths[-5:]:
        content.append(f"  《{m['myth_name']}》\n", style="bold bright_white")
        content.append(f"  {m['myth_text']}\n", style="italic")
        if m.get("cultural_effect"):
            content.append(f"  影响：{m['cultural_effect']}\n", style="dim")
        content.append("\n")
    console.print(Panel(content, title="世界神话", border_style="dim"))


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
        console.print(Panel("  （尚无涌现模块）", title="扩展模块", border_style="dim"))
        return
    content = Text()
    for n in active:
        desc = loader.get_description(n)
        content.append(f"  ✓ {n}  ", style="green")
        content.append(desc + "\n", style="dim")
    for n in broken:
        content.append(f"  ✗ {n}（修复中）\n", style="red")
    console.print(Panel(content, title="扩展模块", border_style="dim"))


def render_entities(active_entities: list):
    """特殊人物面板。"""
    if not active_entities:
        console.print(Panel("  （暂无特殊人物）", title="特殊人物", border_style="dim"))
        return
    content = Text()
    for e in active_entities:
        content.append(f"  {e.name}  ", style="bold bright_white")
        content.append(f"{'、'.join(e.traits)}  ", style="dim")
        content.append(f"第{e.age}/{e.max_age}年\n", style="dim")
        content.append(f"    正在：{e.current_focus}\n", style="italic")
        if e.mutations:
            content.append(f"    变异：{'；'.join(e.mutations)}\n", style="yellow")
    console.print(Panel(content, title="特殊人物", border_style="dim"))


def print_event(text: str):
    """打印世界事件流（带样式）。"""
    if not text.strip():
        return
    if "[离世]" in text or "✕" in text:
        console.print(text, style="dim red")
    elif "[新生]" in text:
        console.print(text, style="dim green")
    elif "[祈祷]" in text:
        console.print(text, style="yellow")
    elif "[变异" in text or "扩散" in text:
        console.print(text, style="yellow dim")
    elif "[织体异常]" in text or "[崩溃]" in text:
        console.print(text, style="red")
    elif "[涌现]" in text or "[系统进化]" in text:
        console.print(text, style="bright_green")
    elif "★" in text:
        console.print(text, style="bright_yellow")
    else:
        console.print(text, style="dim")


def print_banner():
    """开场 banner。"""
    banner = Text()
    banner.append("  《无名之界》\n", style="bold bright_white")
    banner.append("  Unnamed World — a god simulator\n", style="dim italic")
    console.print(Panel(banner, border_style="dim", padding=(0, 2)))


def print_divider():
    console.print("─" * 56, style="grey30")
