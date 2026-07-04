"""
main_simulator.py
-------------------
Digital Lab OS Resource Management Simulator - Main Driver

Ties together:
  - MemoryManager (paging + page replacement)
  - FileSystem (hierarchical FS + indexed allocation + permissions)
  - DiskScheduler (FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK)
  - SecurityManager (RBAC + violation logging)

Produces console output and a persistent log file (logs/simulation.log)
documenting all required metrics:
  - Memory utilization over time
  - Page fault frequency
  - Disk I/O performance
  - File system operations
  - Security violation events
"""

import logging
import os
import json
import random

from memory_manager import MemoryManager
from file_system import FileSystem, PermissionError_
from disk_scheduler import DiskScheduler
from security_manager import SecurityManager

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "simulation.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-16s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("Simulator")


def section(title):
    bar = "=" * 70
    logger.info(bar)
    logger.info(title)
    logger.info(bar)


def run_memory_module():
    section("MODULE 1: MEMORY MANAGEMENT - PAGING & PAGE REPLACEMENT")

    # Reference string simulating process page access pattern in the lab
    reference_string = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5, 6, 1, 2, 3, 7, 2, 3, 6]
    num_frames = 4  # small frame count chosen to clearly demonstrate faults/replacement

    results = {}
    for algo in ["FIFO", "LRU", "OPTIMAL"]:
        mm = MemoryManager(num_frames=num_frames, algorithm=algo, logger=logging.getLogger(f"Memory.{algo}"))
        stats = mm.run_reference_string(reference_string)
        results[algo] = stats
        logger.info(f"[{algo}] Stats: {json.dumps(stats)}")

    logger.info(f"Reference string used: {reference_string}")
    logger.info(f"Number of frames (simulated lab partition): {num_frames}")
    return results


def run_filesystem_module():
    section("MODULE 2: HIERARCHICAL FILE SYSTEM - INDEXED ALLOCATION")

    fs = FileSystem(logger=logging.getLogger("FileSystem"))

    # Build directory hierarchy
    labs = fs.make_directory(fs.root, "Labs")
    cs101 = fs.make_directory(labs, "CS101")
    cs102 = fs.make_directory(labs, "CS102")
    shared = fs.make_directory(fs.root, "Shared")

    # Admin creates files
    fs.create_file(cs101, "assignment1.txt", role="Admin",
                    content="Operating Systems Assignment 1: Process Scheduling Basics." * 5,
                    permission="read-write")
    fs.create_file(cs101, "syllabus.pdf", role="Admin",
                    content="CS101 Course Syllabus - Fall Semester." * 8,
                    permission="read-only")
    fs.create_file(cs102, "lab_manual.txt", role="Admin",
                    content="CS102 Lab Manual: File Systems and Memory Management." * 6,
                    permission="read-write")
    fs.create_file(shared, "notice.txt", role="Admin",
                    content="Lab maintenance scheduled for Sunday." * 3,
                    permission="read-only")

    # Student operations (read-write file -> allowed)
    student_ops_ok = 0
    try:
        fs.write_file(cs101, "assignment1.txt", "Updated content: added section on round robin scheduling." * 4, role="Student")
        student_ops_ok += 1
        content = fs.read_file(cs101, "assignment1.txt", role="Student")
        student_ops_ok += 1
        logger.info(f"Student successfully modified and read assignment1.txt ({len(content)} bytes).")
    except PermissionError_ as e:
        logger.warning(f"Unexpected denial for student write: {e}")

    # Student attempts to delete a read-only file -> should be denied
    violations = []
    try:
        fs.delete_file(cs101, "syllabus.pdf", role="Student")
    except PermissionError_ as e:
        violations.append(str(e))
        logger.warning(f"Expected denial captured: {e}")

    # Guest attempts to write -> should be denied
    try:
        fs.write_file(shared, "notice.txt", "Guest trying to overwrite notice.", role="Guest")
    except PermissionError_ as e:
        violations.append(str(e))
        logger.warning(f"Expected denial captured: {e}")

    # Guest attempts to delete -> should be denied (this is the canonical example from the spec)
    try:
        fs.delete_file(shared, "notice.txt", role="Guest")
    except PermissionError_ as e:
        violations.append(str(e))
        logger.warning(f"Expected denial captured (Guest delete attempt): {e}")

    # Admin deletes a file (legitimate cleanup)
    fs.create_file(cs102, "temp.txt", role="Admin", content="temporary scratch file")
    fs.delete_file(cs102, "temp.txt", role="Admin")

    disk_stats = fs.disk_usage()
    logger.info(f"Disk usage after operations: {json.dumps(disk_stats)}")
    logger.info(f"File-system level access violations captured: {len(violations)}")

    return {
        "disk_usage": disk_stats,
        "violations_in_fs_module": violations,
        "directory_tree": {
            "Labs": {"CS101": list(cs101.files.keys()), "CS102": list(cs102.files.keys())},
            "Shared": list(shared.files.keys()),
        }
    }


def run_disk_scheduling_module():
    section("MODULE 3: DISK SCHEDULING - I/O REQUEST HANDLING")

    # Simulated pending disk requests (cylinder numbers) generated by concurrent
    # student processes requesting page-ins / file block reads
    random.seed(42)
    requests = sorted(random.sample(range(0, 199), 8))
    head_start = 53
    num_cylinders = 200

    scheduler = DiskScheduler(num_cylinders=num_cylinders, logger=logging.getLogger("DiskScheduler"))
    results = {}
    for algo in ["FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"]:
        res = scheduler.run(algo, requests, head_start)
        results[algo] = res

    logger.info(f"Pending disk requests (cylinders): {requests}")
    logger.info(f"Initial head position: {head_start}")
    best_algo = min(results, key=lambda a: results[a]["total_head_movement"])
    logger.info(f"Most efficient algorithm for this request batch: {best_algo} "
                f"(total head movement = {results[best_algo]['total_head_movement']})")
    return results


def run_security_module():
    section("MODULE 4: SECURITY & ROLE-BASED ACCESS CONTROL")

    sec = SecurityManager(logger=logging.getLogger("SecurityManager"))

    sec.register_user(1, "Dr. Ahmed (Lab Admin)", "Admin")
    sec.register_user(2, "Ali Raza", "Student")
    sec.register_user(3, "Sara Khan", "Student")
    sec.register_user(4, "Guest_Visitor_01", "Guest")

    # Simulated sequence of operation attempts across the lab session
    attempts = [
        (1, "create"), (1, "delete"), (1, "modify"),
        (2, "read"), (2, "write"), (2, "create"),
        (3, "read"), (3, "modify"),
        (4, "read"),
        (4, "delete"),   # Guest attempting to delete -> unauthorized
        (4, "write"),    # Guest attempting to write -> unauthorized
        (2, "delete"),   # Student attempting to delete -> unauthorized (not permitted for students)
    ]

    for user_id, op in attempts:
        sec.has_permission(user_id, op)

    stats = sec.get_stats()
    logger.info(f"Security stats: {json.dumps(stats)}")
    logger.info(f"Violations detail: {json.dumps(sec.get_violation_report(), default=str, indent=2)}")
    return {"stats": stats, "violations": sec.get_violation_report()}


def main():
    section("DIGITAL LAB OS RESOURCE MANAGEMENT SIMULATOR")
    logger.info("Simulation started.")
    logger.info("Constraints: Max memory = 512MB | Page size = 4KB | Max users = 50 | Linux-based | CLI")

    memory_results = run_memory_module()
    fs_results = run_filesystem_module()
    disk_results = run_disk_scheduling_module()
    security_results = run_security_module()

    section("SIMULATION SUMMARY")
    summary = {
        "memory_management": memory_results,
        "file_system": fs_results,
        "disk_scheduling": disk_results,
        "security": security_results,
    }
    logger.info(json.dumps(summary, indent=2, default=str))

    # Persist machine-readable results for the technical report
    with open(os.path.join(LOG_DIR, "results_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info("Simulation completed successfully. Full log saved to logs/simulation.log")
    logger.info("Structured results saved to logs/results_summary.json")


if __name__ == "__main__":
    main()
