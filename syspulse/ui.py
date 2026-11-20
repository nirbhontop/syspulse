"""Rich terminal UI renderer with a brutalist technical-editorial aesthetic."""

from __future__ import annotations

from collections import deque
from typing import Deque

from rich import box
from rich.align import Align
from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .metrics import MetricsCollector, SystemSnapshot

ACCENT = "#FF4D00"
SURFACE = "#111111"
TEXT_PRIMARY = "#F4F1EA"
TEXT_MUTED = "#888888"
BORDER_COLOR = "#333333"

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def make_bar(percent: float, width: int = 22) -> Text:
    """Create a crisp block progress bar with threshold coloring."""
    clamped = max(0.0, min(100.0, percent))
    filled = int(round((clamped / 100.0) * width))
    empty = width - filled

    if clamped >= 85:
        color = "#FF2A2A"
    elif clamped >= 65:
        color = ACCENT
    else:
        color = "#E5E2DC"

    bar = Text()
    bar.append("█" * filled, style=f"bold {color}")
    bar.append("░" * empty, style="#2E2E2E")
    bar.append(f" {clamped:5.1f}%", style=f"bold {TEXT_PRIMARY}")
    return bar


def make_sparkline(history: Deque[float], width: int = 28) -> Text:
    """Render an ASCII sparkline from recent percentage samples."""
    samples = list(history)[-width:]
    if len(samples) < width:
        samples = [0.0] * (width - len(samples)) + samples

    spark = Text()
    for val in samples:
        idx = min(len(SPARK_CHARS) - 1, max(0, int((val / 100.0) * (len(SPARK_CHARS) - 1))))
        style = ACCENT if val >= 70 else "#A09D96"
        spark.append(SPARK_CHARS[idx], style=style)
    return spark


class DashboardRenderer:
    """Builds the multi-panel Rich layout for SysPulse."""

    def __init__(self, history_len: int = 40) -> None:
        self.cpu_history: Deque[float] = deque(maxlen=history_len)
        self.mem_history: Deque[float] = deque(maxlen=history_len)

    def _build_header(self, snap: SystemSnapshot, refresh_rate: float, sort_by: str) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=2)
        grid.add_column(justify="center", ratio=2)
        grid.add_column(justify="right", ratio=2)

        left = Text()
        left.append("■ ", style=f"bold {ACCENT}")
        left.append(f"SYSPULSE v{__version__}", style=f"bold {TEXT_PRIMARY}")
        left.append(f"  //  {snap.hostname.upper()}", style=TEXT_MUTED)

        center = Text()
        center.append(f"{snap.os_info} ({snap.architecture})", style=TEXT_MUTED)
        center.append("  •  ", style=ACCENT)
        center.append(f"UP {MetricsCollector.format_uptime(snap.uptime_seconds)}", style=TEXT_PRIMARY)

        right = Text()
        right.append(f"SORT:{sort_by.upper()} ", style=f"bold {ACCENT}")
        right.append(f"• {refresh_rate:.1f}s • {snap.timestamp}", style=TEXT_MUTED)

        grid.add_row(left, center, right)
        return Panel(
            grid,
            box=box.SQUARE,
            border_style=BORDER_COLOR,
            padding=(0, 1),
        )

    def _build_cpu_panel(self, snap: SystemSnapshot) -> Panel:
        self.cpu_history.append(snap.cpu.total_percent)
        cpu = snap.cpu

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(ratio=1)
        table.add_column(justify="right", ratio=2)

        table.add_row(
            Text("TOTAL LOAD", style=f"bold {TEXT_PRIMARY}"),
            make_bar(cpu.total_percent, width=20),
        )
        table.add_row(
            Text("TELEMETRY", style=TEXT_MUTED),
            make_sparkline(self.cpu_history, width=27),
        )

        freq_str = (
            f"{cpu.freq_current_mhz:.0f} / {cpu.freq_max_mhz:.0f} MHz"
            if cpu.freq_max_mhz > 0
            else f"{cpu.freq_current_mhz:.0f} MHz"
        )
        table.add_row(
            Text("CORES / CLK", style=TEXT_MUTED),
            Text(
                f"{cpu.core_count_physical}P / {cpu.core_count_logical}L  •  {freq_str}",
                style=TEXT_PRIMARY,
            ),
        )

        if cpu.load_avg:
            la = f"{cpu.load_avg[0]:.2f}  {cpu.load_avg[1]:.2f}  {cpu.load_avg[2]:.2f}"
            table.add_row(Text("LOAD AVG", style=TEXT_MUTED), Text(la, style=TEXT_PRIMARY))

        # Per-core compact breakdown (up to 16 cores)
        core_lines = Text()
        for idx, pct in enumerate(cpu.per_core_percent[:16]):
            color = ACCENT if pct >= 70 else TEXT_PRIMARY
            core_lines.append(f"C{idx:02d}:", style=TEXT_MUTED)
            core_lines.append(f"{pct:4.0f}% ", style=color)
            if (idx + 1) % 4 == 0 and idx + 1 < len(cpu.per_core_percent[:16]):
                core_lines.append("\n")

        content = Group(table, Text(""), core_lines)
        return Panel(
            content,
            title=f"[bold {ACCENT}][01][/] [bold {TEXT_PRIMARY}]CPU TELEMETRY[/]",
            title_align="left",
            box=box.SQUARE,
            border_style=BORDER_COLOR,
            padding=(0, 1),
        )

    def _build_memory_panel(self, snap: SystemSnapshot) -> Panel:
        self.mem_history.append(snap.memory.percent)
        mem = snap.memory
        fmt = MetricsCollector.format_bytes

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(ratio=1)
        table.add_column(justify="right", ratio=2)

        table.add_row(
            Text("RAM USAGE", style=f"bold {TEXT_PRIMARY}"),
            make_bar(mem.percent, width=20),
        )
        table.add_row(
            Text("HISTORY", style=TEXT_MUTED),
            make_sparkline(self.mem_history, width=27),
        )
        table.add_row(
            Text("ALLOCATED", style=TEXT_MUTED),
            Text(f"{fmt(mem.used_bytes).strip()} / {fmt(mem.total_bytes).strip()}", style=TEXT_PRIMARY),
        )
        table.add_row(
            Text("AVAILABLE", style=TEXT_MUTED),
            Text(fmt(mem.available_bytes).strip(), style=TEXT_PRIMARY),
        )

        if mem.swap_total_bytes > 0:
            table.add_row(
                Text("SWAP", style=TEXT_MUTED),
                make_bar(mem.swap_percent, width=20),
            )
            table.add_row(
                Text("SWAP USED", style=TEXT_MUTED),
                Text(
                    f"{fmt(mem.swap_used_bytes).strip()} / {fmt(mem.swap_total_bytes).strip()}",
                    style=TEXT_PRIMARY,
                ),
            )
        else:
            table.add_row(Text("SWAP", style=TEXT_MUTED), Text("DISABLED", style=TEXT_MUTED))

        return Panel(
            table,
            title=f"[bold {ACCENT}][02][/] [bold {TEXT_PRIMARY}]MEMORY & SWAP[/]",
            title_align="left",
            box=box.SQUARE,
            border_style=BORDER_COLOR,
            padding=(0, 1),
        )

    def _build_storage_net_panel(self, snap: SystemSnapshot) -> Panel:
        fmt = MetricsCollector.format_bytes
        net = snap.network

        net_grid = Table.grid(expand=True, padding=(0, 1))
        net_grid.add_column(ratio=1)
        net_grid.add_column(justify="right", ratio=2)

        if net:
            net_grid.add_row(
                Text("DOWNLINK", style=TEXT_MUTED),
                Text(f"▼ {fmt(net.download_speed_bps).strip()}/s", style=f"bold {ACCENT}"),
            )
            net_grid.add_row(
                Text("UPLINK", style=TEXT_MUTED),
                Text(f"▲ {fmt(net.upload_speed_bps).strip()}/s", style=f"bold {TEXT_PRIMARY}"),
            )
            net_grid.add_row(
                Text("TOTAL I/O", style=TEXT_MUTED),
                Text(
                    f"RX {fmt(net.bytes_recv).strip()}  |  TX {fmt(net.bytes_sent).strip()}",
                    style=TEXT_PRIMARY,
                ),
            )

        disk_table = Table(
            box=box.SIMPLE,
            expand=True,
            show_header=True,
            header_style=f"bold {TEXT_MUTED}",
            padding=(0, 1),
        )
        disk_table.add_column("MOUNT", style=TEXT_PRIMARY, no_wrap=True)
        disk_table.add_column("USED / TOTAL", justify="right", style=TEXT_MUTED)
        disk_table.add_column("UTIL", justify="right")

        for d in snap.disks[:5]:
            disk_table.add_row(
                d.mountpoint[:16],
                f"{fmt(d.used_bytes).strip()}/{fmt(d.total_bytes).strip()}",
                make_bar(d.percent, width=10),
            )

        return Panel(
            Group(net_grid, Text(""), disk_table),
            title=f"[bold {ACCENT}][03][/] [bold {TEXT_PRIMARY}]NETWORK & STORAGE[/]",
            title_align="left",
            box=box.SQUARE,
            border_style=BORDER_COLOR,
            padding=(0, 1),
        )

    def _build_process_panel(self, snap: SystemSnapshot, sort_by: str) -> Panel:
        proc_table = Table(
            box=box.SIMPLE,
            expand=True,
            show_header=True,
            header_style=f"bold {TEXT_MUTED}",
            padding=(0, 1),
        )
        proc_table.add_column("PID", justify="right", style=TEXT_MUTED, width=7)
        proc_table.add_column("PROCESS", style=f"bold {TEXT_PRIMARY}", ratio=2)
        proc_table.add_column("USER", style=TEXT_MUTED, ratio=1)
        proc_table.add_column("STATE", style=TEXT_MUTED, width=9)
        proc_table.add_column(
            "CPU %" + (" ▼" if sort_by == "cpu" else ""),
            justify="right",
            width=9,
        )
        proc_table.add_column(
            "MEM %" + (" ▼" if sort_by == "mem" else ""),
            justify="right",
            width=9,
        )

        for p in snap.top_processes:
            cpu_style = f"bold {ACCENT}" if p.cpu_percent >= 25.0 else TEXT_PRIMARY
            mem_style = f"bold {ACCENT}" if p.memory_percent >= 15.0 else TEXT_PRIMARY
            proc_table.add_row(
                str(p.pid),
                p.name,
                p.username,
                p.status.upper(),
                Text(f"{p.cpu_percent:5.1f}%", style=cpu_style),
                Text(f"{p.memory_percent:5.1f}%", style=mem_style),
            )

        return Panel(
            proc_table,
            title=f"[bold {ACCENT}][04][/] [bold {TEXT_PRIMARY}]ACTIVE PROCESSES[/]",
            title_align="left",
            box=box.SQUARE,
            border_style=BORDER_COLOR,
            padding=(0, 1),
        )

    def _build_footer(self) -> Text:
        footer = Text()
        footer.append("CTRL+C", style=f"bold {ACCENT}")
        footer.append(" EXIT   ", style=TEXT_MUTED)
        footer.append("--sort cpu|mem", style=f"bold {TEXT_PRIMARY}")
        footer.append(" RANKING   ", style=TEXT_MUTED)
        footer.append("--json", style=f"bold {TEXT_PRIMARY}")
        footer.append(" SNAPSHOT EXPORT", style=TEXT_MUTED)
        return Align.center(footer)

    def render(self, snap: SystemSnapshot, refresh_rate: float, sort_by: str) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=1),
        )
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        layout["left"].split_column(
            Layout(name="cpu", ratio=1),
            Layout(name="memory", ratio=1),
        )
        layout["right"].split_column(
            Layout(name="storage_net", ratio=1),
            Layout(name="processes", ratio=1),
        )

        layout["header"].update(self._build_header(snap, refresh_rate, sort_by))
        layout["cpu"].update(self._build_cpu_panel(snap))
        layout["memory"].update(self._build_memory_panel(snap))
        layout["storage_net"].update(self._build_storage_net_panel(snap))
        layout["processes"].update(self._build_process_panel(snap, sort_by))
        layout["footer"].update(self._build_footer())
        return layout
