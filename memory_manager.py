"""
memory_manager.py
------------------
Memory Management Module for the Digital Lab OS Resource Management Simulator.

Implements:
- Fixed-size paging system (page size = 4 KB, max memory = 512 MB -> 131072 frames... 
  scaled down to a configurable frame count for simulation speed/clarity)
- Page fault simulation
- Page replacement algorithms: FIFO, LRU, Optimal
- Memory usage and page fault statistics logging
"""

from collections import OrderedDict
import logging
import time

PAGE_SIZE_KB = 4
MAX_MEMORY_MB = 512
MAX_FRAMES = (MAX_MEMORY_MB * 1024) // PAGE_SIZE_KB  # 131072 (real OS scale)


class MemoryManager:
    """
    Simulates a paged memory system with a fixed number of physical frames.
    For simulation purposes, the number of available frames can be set smaller
    than the theoretical maximum (131072) so that page faults can be observed
    and demonstrated clearly within a short reference string.
    """

    def __init__(self, num_frames, algorithm="LRU", logger=None):
        self.num_frames = num_frames
        self.algorithm = algorithm.upper()
        self.frames = OrderedDict()   # page_no -> last_used_time / load_time
        self.page_table = {}          # page_no -> frame_index (presence bit implied by key existing)
        self.free_frames = list(range(num_frames))
        self.page_faults = 0
        self.page_hits = 0
        self.access_log = []
        self.logger = logger or logging.getLogger("MemoryManager")
        self.clock = 0

    def _evict_fifo(self):
        evicted_page, _ = self.frames.popitem(last=False)
        return evicted_page

    def _evict_lru(self):
        evicted_page, _ = self.frames.popitem(last=False)
        return evicted_page

    def _evict_optimal(self, future_references, current_index):
        """Evict the page that will not be used for the longest time (or never again)."""
        farthest_use = -1
        page_to_evict = None
        for page in self.frames.keys():
            if page in future_references[current_index + 1:]:
                next_use = future_references[current_index + 1:].index(page)
            else:
                next_use = float('inf')
            if next_use > farthest_use:
                farthest_use = next_use
                page_to_evict = page
        return page_to_evict

    def access_page(self, page_no, reference_index=0, full_reference_string=None):
        """
        Simulate access to a page number. Returns True on hit, False on fault.
        """
        self.clock += 1
        if page_no in self.frames:
            self.page_hits += 1
            if self.algorithm in ("LRU", "FIFO"):
                if self.algorithm == "LRU":
                    self.frames.move_to_end(page_no)
            self.access_log.append((self.clock, page_no, "HIT"))
            self.logger.info(f"Access page {page_no}: HIT (frame already resident)")
            return True

        # Page fault
        self.page_faults += 1
        if len(self.frames) >= self.num_frames:
            if self.algorithm == "FIFO":
                evicted = self._evict_fifo()
            elif self.algorithm == "LRU":
                evicted = self._evict_lru()
            elif self.algorithm == "OPTIMAL":
                evicted = self._evict_optimal(full_reference_string or [], reference_index)
                del self.frames[evicted]
            else:
                raise ValueError(f"Unknown algorithm: {self.algorithm}")
            self.logger.info(f"Access page {page_no}: FAULT -> evicted page {evicted} ({self.algorithm})")
        else:
            self.logger.info(f"Access page {page_no}: FAULT -> loaded into free frame")

        self.frames[page_no] = self.clock
        self.access_log.append((self.clock, page_no, "FAULT"))
        return False

    def run_reference_string(self, reference_string):
        """Run a full reference string and return fault/hit statistics."""
        for i, page in enumerate(reference_string):
            self.access_page(page, reference_index=i, full_reference_string=reference_string)
        return self.get_stats()

    def get_stats(self):
        total = self.page_faults + self.page_hits
        fault_rate = (self.page_faults / total * 100) if total else 0.0
        return {
            "algorithm": self.algorithm,
            "num_frames": self.num_frames,
            "total_accesses": total,
            "page_faults": self.page_faults,
            "page_hits": self.page_hits,
            "fault_rate_percent": round(fault_rate, 2),
            "memory_utilization_percent": round(len(self.frames) / self.num_frames * 100, 2),
        }

    def memory_snapshot(self):
        return list(self.frames.keys())
