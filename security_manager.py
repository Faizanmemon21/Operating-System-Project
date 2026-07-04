"""
security_manager.py
--------------------
Security & Role-Based Access Control (RBAC) Module for the Digital Lab OS
Resource Management Simulator.

Implements:
- User Role Table (Admin, Student, Guest) with explicit permission sets
- Access control enforcement for file operations based on role
- Logging of access attempts and security violations
"""

import logging
import time

ROLE_PERMISSIONS = {
    "Admin":   {"read", "write", "delete", "modify", "create"},
    "Student": {"read", "write", "modify", "create"},   # cannot delete read-only/system files
    "Guest":   {"read"},                                  # read-only access
}

MAX_USERS = 50


class User:
    def __init__(self, user_id, name, role):
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"Invalid role: {role}")
        self.user_id = user_id
        self.name = name
        self.role = role


class SecurityManager:
    def __init__(self, logger=None):
        self.users = {}
        self.access_log = []
        self.violations = []
        self.logger = logger or logging.getLogger("SecurityManager")

    def register_user(self, user_id, name, role):
        if len(self.users) >= MAX_USERS:
            raise OverflowError("Maximum number of lab users (50) reached.")
        user = User(user_id, name, role)
        self.users[user_id] = user
        self.logger.info(f"User registered: id={user_id}, name={name}, role={role}")
        return user

    def has_permission(self, user_id, operation):
        user = self.users.get(user_id)
        if user is None:
            raise KeyError(f"Unknown user_id: {user_id}")
        allowed = operation in ROLE_PERMISSIONS[user.role]
        timestamp = time.time()
        entry = {
            "timestamp": timestamp,
            "user_id": user_id,
            "name": user.name,
            "role": user.role,
            "operation": operation,
            "allowed": allowed,
        }
        self.access_log.append(entry)
        if not allowed:
            self.violations.append(entry)
            self.logger.warning(
                f"SECURITY VIOLATION: user={user.name} (role={user.role}) attempted "
                f"unauthorized '{operation}' operation."
            )
        else:
            self.logger.info(
                f"Access granted: user={user.name} (role={user.role}) performed '{operation}'."
            )
        return allowed

    def get_violation_report(self):
        return self.violations

    def get_stats(self):
        total = len(self.access_log)
        denied = len(self.violations)
        return {
            "total_access_attempts": total,
            "granted": total - denied,
            "denied_violations": denied,
            "violation_rate_percent": round((denied / total * 100), 2) if total else 0.0,
        }
