"""System metrics collection module powered by psutil."""

from __future__ import annotations

import datetime
import platform
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil


@dataclass
class CpuMetrics:
    total_percent: float
    per_core_percent: List[float]
    core_count_logical: int
    core_count_physical: int
    freq_current_mhz: float
    freq_max_mhz: float
    load_avg: Optional[tuple[float, float, float]]


@dataclass
class MemoryMetrics:
    total_bytes: int
    available_bytes: int
    used_bytes: int
    percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float


@dataclass
class DiskMetrics:
    device: str
    mountpoint: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float


@dataclass
class NetworkMetrics:
    bytes_sent: int
    bytes_recv: int
    upload_speed_bps: float
    download_speed_bps: float
    packets_sent: int
    packets_recv: int


@dataclass
class ProcessInfo:
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str


@dataclass
class SystemSnapshot:
    hostname: str
    os_info: str
    architecture: str
    uptime_seconds: float
    timestamp: str
    cpu: CpuMetrics
    memory: MemoryMetrics
    disks: List[DiskMetrics] = field(default_factory=list)
    network: Optional[NetworkMetrics] = None
    top_processes: List[ProcessInfo] = field(default_factory=list)


class MetricsCollector:
    """Collects and calculates real-time host telemetry."""

    def __init__(self) -> None:
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.monotonic()
        # Prime cpu_percent counters so first read isn't 0.0
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

    @staticmethod
    def format_bytes(num_bytes: float) -> str:
        """Convert raw byte count into human-readable unit string."""
        for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:6.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:6.1f} EB"

    @staticmethod
    def format_uptime(seconds: float) -> str:
        """Format uptime seconds into `Xd Xh Xm Xs`."""
        total = int(seconds)
        days, rem = divmod(total, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or days:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    def get_cpu_metrics(self) -> CpuMetrics:
        total = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        freq = psutil.cpu_freq()
        try:
            load_avg = psutil.getloadavg()
        except (AttributeError, OSError):
            load_avg = None

        return CpuMetrics(
            total_percent=total,
            per_core_percent=per_core,
            core_count_logical=psutil.cpu_count(logical=True) or 1,
            core_count_physical=psutil.cpu_count(logical=False) or 1,
            freq_current_mhz=freq.current if freq else 0.0,
            freq_max_mhz=freq.max if freq else 0.0,
            load_avg=load_avg,
        )

    def get_memory_metrics(self) -> MemoryMetrics:
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        return MemoryMetrics(
            total_bytes=vm.total,
            available_bytes=vm.available,
            used_bytes=vm.used,
            percent=vm.percent,
            swap_total_bytes=sm.total,
            swap_used_bytes=sm.used,
            swap_percent=sm.percent,
        )

    def get_disk_metrics(self) -> List[DiskMetrics]:
        disks: List[DiskMetrics] = []
        seen_devices = set()
        for part in psutil.disk_partitions(all=False):
            if part.device in seen_devices:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            seen_devices.add(part.device)
            disks.append(
                DiskMetrics(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                    percent=usage.percent,
                )
            )
        return disks

    def get_network_metrics(self) -> NetworkMetrics:
        now = time.monotonic()
        current_io = psutil.net_io_counters()
        elapsed = max(now - self._last_net_time, 1e-6)

        up_speed = (current_io.bytes_sent - self._last_net_io.bytes_sent) / elapsed
        down_speed = (current_io.bytes_recv - self._last_net_io.bytes_recv) / elapsed

        self._last_net_io = current_io
        self._last_net_time = now

        return NetworkMetrics(
            bytes_sent=current_io.bytes_sent,
            bytes_recv=current_io.bytes_recv,
            upload_speed_bps=max(0.0, up_speed),
            download_speed_bps=max(0.0, down_speed),
            packets_sent=current_io.packets_sent,
            packets_recv=current_io.packets_recv,
        )

    def get_top_processes(self, limit: int = 8, sort_by: str = "cpu") -> List[ProcessInfo]:
        procs: List[ProcessInfo] = []
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                procs.append(
                    ProcessInfo(
                        pid=info.get("pid") or 0,
                        name=(info.get("name") or "unknown")[:26],
                        username=(info.get("username") or "-")[:14],
                        cpu_percent=float(info.get("cpu_percent") or 0.0),
                        memory_percent=float(info.get("memory_percent") or 0.0),
                        status=str(info.get("status") or "?"),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        key_fn = (
            (lambda p: p.memory_percent)
            if sort_by == "mem"
            else (lambda p: p.cpu_percent)
        )
        procs.sort(key=key_fn, reverse=True)
        return procs[:limit]

    def collect(self, process_limit: int = 8, sort_by: str = "cpu") -> SystemSnapshot:
        boot_time = psutil.boot_time()
        uptime = max(0.0, time.time() - boot_time)
        return SystemSnapshot(
            hostname=socket.gethostname(),
            os_info=f"{platform.system()} {platform.release()}",
            architecture=platform.machine(),
            uptime_seconds=uptime,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            cpu=self.get_cpu_metrics(),
            memory=self.get_memory_metrics(),
            disks=self.get_disk_metrics(),
            network=self.get_network_metrics(),
            top_processes=self.get_top_processes(limit=process_limit, sort_by=sort_by),
        )
