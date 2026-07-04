"""
file_system.py
--------------
Hierarchical File System Module for the Digital Lab OS Resource Management Simulator.

Implements:
- File creation, reading, writing, deletion, modification
- Directory structure with nested folders
- Access permissions (read-only, read-write)
- Indexed allocation technique (each file has an index block listing its data blocks)
"""

import logging
import time

DISK_TOTAL_BLOCKS = 2048   # simulated disk size in blocks
BLOCK_SIZE_BYTES = 512


class PermissionError_(Exception):
    pass


class DataBlock:
    __slots__ = ("block_id", "data")

    def __init__(self, block_id, data=""):
        self.block_id = block_id
        self.data = data


class INode:
    """Index block for a file -- holds metadata + list of allocated data block IDs (indexed allocation)."""

    def __init__(self, name, owner_role, permission="read-write"):
        self.name = name
        self.owner_role = owner_role
        self.permission = permission  # "read-only" or "read-write"
        self.index_blocks = []        # list of block_ids (indexed allocation)
        self.created_at = time.time()
        self.modified_at = time.time()

    def size_bytes(self):
        return len(self.index_blocks) * BLOCK_SIZE_BYTES


class Directory:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.subdirectories = {}  # name -> Directory
        self.files = {}           # name -> INode

    def path(self):
        if self.parent is None:
            return "/" + self.name
        return self.parent.path().rstrip("/") + "/" + self.name


class FileSystem:
    def __init__(self, logger=None):
        self.root = Directory("root")
        self.disk_blocks = [None] * DISK_TOTAL_BLOCKS
        self.free_blocks = list(range(DISK_TOTAL_BLOCKS))
        self.logger = logger or logging.getLogger("FileSystem")

    # ---------- directory helpers ----------
    def make_directory(self, parent_dir, name):
        if name in parent_dir.subdirectories:
            raise FileExistsError(f"Directory '{name}' already exists.")
        new_dir = Directory(name, parent=parent_dir)
        parent_dir.subdirectories[name] = new_dir
        self.logger.info(f"Directory created: {new_dir.path()}")
        return new_dir

    # ---------- block allocation (indexed allocation) ----------
    def _allocate_blocks(self, count):
        if count > len(self.free_blocks):
            raise MemoryError("Insufficient disk space.")
        allocated = [self.free_blocks.pop(0) for _ in range(count)]
        return allocated

    def _free_blocks_for_file(self, inode):
        for b in inode.index_blocks:
            self.disk_blocks[b] = None
            self.free_blocks.append(b)
        self.free_blocks.sort()
        inode.index_blocks = []

    # ---------- permission check ----------
    def _check_permission(self, inode, role, operation):
        """
        Role hierarchy: Admin > Student > Guest
        Guests cannot write/delete/modify under any circumstance.
        Students can read/write their own files but not delete read-only files.
        Admin can do anything.
        """
        if role == "Admin":
            return True
        if operation == "read":
            return True  # all roles can read unless explicitly restricted (kept simple)
        if role == "Guest":
            return False
        if role == "Student":
            if inode.permission == "read-only" and operation in ("write", "delete", "modify"):
                return False
            return True
        return False

    # ---------- file operations ----------
    def create_file(self, directory, name, role, content="", permission="read-write"):
        if name in directory.files:
            raise FileExistsError(f"File '{name}' already exists in {directory.path()}.")
        inode = INode(name, owner_role=role, permission=permission)
        directory.files[name] = inode
        self.logger.info(f"File created: {directory.path()}/{name} by role={role}")
        if content:
            self.write_file(directory, name, content, role)
        return inode

    def write_file(self, directory, name, content, role):
        inode = directory.files.get(name)
        if inode is None:
            raise FileNotFoundError(f"File '{name}' not found.")
        if not self._check_permission(inode, role, "write"):
            self.logger.warning(
                f"SECURITY VIOLATION: role={role} denied WRITE on {directory.path()}/{name}"
            )
            raise PermissionError_(f"Role '{role}' does not have write permission on '{name}'.")

        # free old blocks, allocate new ones sized to content
        self._free_blocks_for_file(inode)
        blocks_needed = max(1, -(-len(content.encode()) // BLOCK_SIZE_BYTES))  # ceil div
        block_ids = self._allocate_blocks(blocks_needed)
        chunk_size = max(1, len(content) // blocks_needed)
        for i, bid in enumerate(block_ids):
            chunk = content[i * chunk_size: (i + 1) * chunk_size] if i < blocks_needed - 1 else content[i * chunk_size:]
            self.disk_blocks[bid] = chunk
        inode.index_blocks = block_ids
        inode.modified_at = time.time()
        self.logger.info(f"File written: {directory.path()}/{name} ({blocks_needed} blocks) by role={role}")
        return True

    def read_file(self, directory, name, role):
        inode = directory.files.get(name)
        if inode is None:
            raise FileNotFoundError(f"File '{name}' not found.")
        if not self._check_permission(inode, role, "read"):
            self.logger.warning(
                f"SECURITY VIOLATION: role={role} denied READ on {directory.path()}/{name}"
            )
            raise PermissionError_(f"Role '{role}' does not have read permission on '{name}'.")
        data = "".join(self.disk_blocks[b] or "" for b in inode.index_blocks)
        self.logger.info(f"File read: {directory.path()}/{name} by role={role}")
        return data

    def modify_file(self, directory, name, new_content, role):
        return self.write_file(directory, name, new_content, role)

    def delete_file(self, directory, name, role):
        inode = directory.files.get(name)
        if inode is None:
            raise FileNotFoundError(f"File '{name}' not found.")
        if not self._check_permission(inode, role, "delete"):
            self.logger.warning(
                f"SECURITY VIOLATION: role={role} denied DELETE on {directory.path()}/{name}"
            )
            raise PermissionError_(f"Role '{role}' does not have delete permission on '{name}'.")
        self._free_blocks_for_file(inode)
        del directory.files[name]
        self.logger.info(f"File deleted: {directory.path()}/{name} by role={role}")
        return True

    def disk_usage(self):
        used = DISK_TOTAL_BLOCKS - len(self.free_blocks)
        return {
            "total_blocks": DISK_TOTAL_BLOCKS,
            "used_blocks": used,
            "free_blocks": len(self.free_blocks),
            "utilization_percent": round(used / DISK_TOTAL_BLOCKS * 100, 2),
        }
