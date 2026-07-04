"""
disk_scheduler.py
------------------
Disk Scheduling Module for the Digital Lab OS Resource Management Simulator.

Implements disk scheduling algorithms to handle multiple concurrent disk
I/O requests (simulating page-in/page-out and file block requests):
- FCFS  (First Come First Serve)
- SSTF  (Shortest Seek Time First)
- SCAN
- C-SCAN
- LOOK
- C-LOOK

Measures total head movement (seek distance) and produces the service order,
used as a proxy for disk access performance.
"""

import logging


class DiskScheduler:
    def __init__(self, num_cylinders=200, logger=None):
        self.num_cylinders = num_cylinders
        self.logger = logger or logging.getLogger("DiskScheduler")

    def fcfs(self, requests, head_start):
        order = list(requests)
        total_seek = 0
        current = head_start
        for r in order:
            total_seek += abs(r - current)
            current = r
        return order, total_seek

    def sstf(self, requests, head_start):
        pending = list(requests)
        order = []
        total_seek = 0
        current = head_start
        while pending:
            closest = min(pending, key=lambda r: abs(r - current))
            total_seek += abs(closest - current)
            current = closest
            order.append(closest)
            pending.remove(closest)
        return order, total_seek

    def scan(self, requests, head_start, direction="up"):
        order = []
        total_seek = 0
        current = head_start
        reqs = sorted(requests)
        if direction == "up":
            greater = [r for r in reqs if r >= current]
            lesser = [r for r in reqs if r < current]
            order = greater + [self.num_cylinders - 1] + lesser[::-1]
        else:
            lesser = [r for r in reqs if r <= current]
            greater = [r for r in reqs if r > current]
            order = lesser[::-1] + [0] + greater[::-1]
        # compute seek
        prev = current
        for r in order:
            total_seek += abs(r - prev)
            prev = r
        return order, total_seek

    def c_scan(self, requests, head_start):
        order = []
        total_seek = 0
        current = head_start
        reqs = sorted(requests)
        greater = [r for r in reqs if r >= current]
        lesser = [r for r in reqs if r < current]
        # go up to the end, jump to 0, continue up to first unserved request
        order = greater + [self.num_cylinders - 1, 0] + lesser
        prev = current
        for r in order:
            total_seek += abs(r - prev)
            prev = r
        return order, total_seek

    def look(self, requests, head_start, direction="up"):
        reqs = sorted(requests)
        if direction == "up":
            greater = [r for r in reqs if r >= head_start]
            lesser = [r for r in reqs if r < head_start]
            order = greater + lesser[::-1]
        else:
            lesser = [r for r in reqs if r <= head_start]
            greater = [r for r in reqs if r > head_start]
            order = lesser[::-1] + greater[::-1]
        total_seek = 0
        prev = head_start
        for r in order:
            total_seek += abs(r - prev)
            prev = r
        return order, total_seek

    def c_look(self, requests, head_start):
        reqs = sorted(requests)
        greater = [r for r in reqs if r >= head_start]
        lesser = [r for r in reqs if r < head_start]
        order = greater + lesser
        total_seek = 0
        prev = head_start
        for r in order:
            total_seek += abs(r - prev)
            prev = r
        return order, total_seek

    def run(self, algorithm, requests, head_start):
        algorithm = algorithm.upper()
        dispatch = {
            "FCFS": lambda: self.fcfs(requests, head_start),
            "SSTF": lambda: self.sstf(requests, head_start),
            "SCAN": lambda: self.scan(requests, head_start),
            "C-SCAN": lambda: self.c_scan(requests, head_start),
            "LOOK": lambda: self.look(requests, head_start),
            "C-LOOK": lambda: self.c_look(requests, head_start),
        }
        if algorithm not in dispatch:
            raise ValueError(f"Unknown disk scheduling algorithm: {algorithm}")
        order, total_seek = dispatch[algorithm]()
        avg_seek = total_seek / len(requests) if requests else 0
        self.logger.info(
            f"[{algorithm}] Service order: {order} | Total head movement: {total_seek} "
            f"cylinders | Avg seek/request: {avg_seek:.2f}"
        )
        return {
            "algorithm": algorithm,
            "service_order": order,
            "total_head_movement": total_seek,
            "average_seek_time": round(avg_seek, 2),
            "num_requests": len(requests),
        }
