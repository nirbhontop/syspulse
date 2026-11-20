"""Unit tests for SysPulse metrics collection and formatting."""

import dataclasses
import json
import unittest

from syspulse.cli import parse_args
from syspulse.metrics import MetricsCollector


class TestSysPulse(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(MetricsCollector.format_bytes(512).strip(), "512.0 B")
        self.assertEqual(MetricsCollector.format_bytes(1024).strip(), "1.0 KB")
        self.assertEqual(MetricsCollector.format_bytes(1024 ** 3).strip(), "1.0 GB")

    def test_format_uptime(self):
        self.assertEqual(MetricsCollector.format_uptime(65), "1m 5s")
        self.assertEqual(MetricsCollector.format_uptime(3661), "1h 1m 1s")
        self.assertEqual(MetricsCollector.format_uptime(90061), "1d 1h 1m 1s")

    def test_collect_snapshot_serializable(self):
        collector = MetricsCollector()
        snap = collector.collect(process_limit=3, sort_by="mem")
        self.assertGreaterEqual(snap.cpu.core_count_logical, 1)
        self.assertGreater(snap.memory.total_bytes, 0)
        self.assertLessEqual(len(snap.top_processes), 3)

        payload = json.dumps(dataclasses.asdict(snap))
        self.assertIn("hostname", payload)

    def test_cli_arg_parsing(self):
        args = parse_args(["--refresh", "0.5", "--sort", "mem", "--procs", "5", "--json"])
        self.assertEqual(args.refresh, 0.5)
        self.assertEqual(args.sort, "mem")
        self.assertEqual(args.procs, 5)
        self.assertTrue(args.json)


if __name__ == "__main__":
    unittest.main()
