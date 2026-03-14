"""
Input validation and sanitization utilities.

Provides comprehensive validation for user inputs, SSH configurations,
file paths, and environment variables to prevent injection attacks.
"""

import re
import shlex
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException

# Comprehensive list of dangerous command patterns
DANGEROUS_COMMANDS = [
    # File system destruction
    "rm -rf /", "rm -rf /*", "rm -fr /", "rm -fr /*",
    "mkfs", "dd if=", "shred",
    
    # System control
    "shutdown", "reboot", "halt", "poweroff", "init 0", "init 6",
    "systemctl poweroff", "systemctl reboot", "systemctl halt",
    
    # Disk/mount operations
    "mount", "umount", "fdisk", "parted", "mkfs",
    
    # User management (dangerous without proper context)
    "passwd", "useradd", "userdel", "usermod", "groupadd", "groupdel",
    
    # Permission changes that could expose system
    "chmod 777 /", "chmod -R 777 /", "chown -R",
    
    # Process killing (system-critical)
    "kill -9 1", "killall init", "pkill systemd",
    
    # Cryptographic key operations
    "ssh-keygen -y", "openssl", "gpg --export-secret",
    
    # Database operations (without context)
    "DROP DATABASE", "DROP TABLE", "TRUNCATE",
]

# Dangerous shell operators that could enable command injection
DANGEROUS_OPERATORS = [
    ";", "&&", "||", "|", ">", ">>", "<", "$(", "`", "${",
]

# Regex pattern for valid environment variable names
ENV_VAR_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Regex pattern for valid file paths (no special chars that could enable attacks)
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9/_.\-]+$")


def sanitize_command(command: str, allow_operators: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and sanitize a shell command.
    
    Args:
        command: The command string to validate
        allow_operators: Whether to allow shell operators (;, &&, ||, etc.)
        
    Returns:
        Tuple of (is_safe, sanitized_command, error_message)
        - is_safe: True if command passes all safety checks
        - sanitized_command: Cleaned version of the command
        - error_message: Description of security issue if not safe
    """
    if not command or not command.strip():
        return False, "", "Empty command"
    
    command = command.strip()
    command_lower = command.lower()
    
    # Check for dangerous commands
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous.lower() in command_lower:
            return False, "", f"Dangerous command detected: {dangerous}"
    
    # Check for command injection via operators (unless explicitly allowed)
    if not allow_operators:
        for operator in DANGEROUS_OPERATORS:
            if operator in command:
                return False, "", f"Potentially dangerous operator detected: {operator}"
    
    # Check for attempts to access /etc/shadow or other sensitive files
    sensitive_files = ["/etc/shadow", "/etc/passwd", "/root/.ssh", "~/.ssh/id_"]
    for sensitive in sensitive_files:
        if sensitive in command_lower:
            return False, "", f"Attempt to access sensitive file: {sensitive}"
    
    # Validate that command can be parsed by shlex (detects malformed quotes/escapes)
    try:
        shlex.split(command)
    except ValueError as e:
        return False, "", f"Malformed command syntax: {str(e)}"
    
    return True, command, None


def validate_ssh_config(config: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate SSH configuration dictionary.
    
    Args:
        config: Dictionary containing SSH connection parameters
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["host", "username"]
    for field in required_fields:
        if not config.get(field):
            return False, f"Missing required field: {field}"
    
    # Validate host format (prevent command injection via host field)
    host = config.get("host", "")
    if not re.match(r"^[a-zA-Z0-9.-]+$", host):
        return False, "Invalid host format. Only alphanumeric, dots, and hyphens allowed."
    
    # Validate port
    port = config.get("port", 22)
    try:
        port_int = int(port)
        if not (1 <= port_int <= 65535):
            return False, "Port must be between 1 and 65535"
    except (ValueError, TypeError):
        return False, "Invalid port number"
    
    # Validate username format
    username = config.get("username", "")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Invalid username format. Only alphanumeric, underscore, and hyphen allowed."
    
    # Validate authentication method
    auth_method = config.get("ssh_auth_method", "private_key")
    if auth_method not in ["private_key", "password"]:
        return False, "Invalid authentication method. Must be 'private_key' or 'password'."
    
    # Check that appropriate credentials are provided
    if auth_method == "private_key":
        ssh_key = config.get("ssh_key", "")
        if not ssh_key or len(ssh_key) < 100:  # SSH keys are typically >100 chars
            return False, "SSH private key is required and must be valid"
        
        # Basic validation that it looks like an SSH key
        if not ("BEGIN" in ssh_key and "PRIVATE KEY" in ssh_key):
            return False, "SSH key format appears invalid"
    
    elif auth_method == "password":
        password = config.get("ssh_password", "")
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters"
    
    return True, None


def is_safe_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a file path is safe to use.
    
    Args:
        path: The file path to validate
        
    Returns:
        Tuple of (is_safe, error_message)
    """
    if not path or not path.strip():
        return False, "Empty path"
    
    path = path.strip()
    
    # Check for path traversal attempts
    if ".." in path:
        return False, "Path traversal detected (..)path"
    
    # Check for null bytes (can terminate strings in C-based tools)
    if "\0" in path:
        return False, "Null byte detected in path"
    
    # Prevent access to sensitive system directories
    sensitive_paths = ["/etc/shadow", "/etc/passwd", "/root/.ssh", "/etc/sudoers"]
    for sensitive in sensitive_paths:
        if path.startswith(sensitive):
            return False, f"Access to sensitive path denied: {sensitive}"
    
    # Validate path characters
    if not SAFE_PATH_PATTERN.match(path):
        return False, "Path contains invalid characters"
    
    return True, None


def validate_env_var_name(name: str) -> bool:
    """
    Validate environment variable name format.
    
    Args:
        name: The environment variable name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    
    return bool(ENV_VAR_PATTERN.match(name))


def validate_deployment_script(script: str) -> Tuple[bool, List[str]]:
    """
    Validate a deployment script for security issues.
    
    Args:
        script: The deployment script content
        
    Returns:
        Tuple of (is_safe, list_of_warnings)
    """
    if not script or not script.strip():
        return False, ["Empty script"]
    
    warnings = []
    lines = script.split("\n")
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Check each line for dangerous patterns
        is_safe, _, error = sanitize_command(line, allow_operators=True)
        if not is_safe:
            warnings.append(f"Line {i}: {error}")
    
    return len(warnings) == 0, warnings


def sanitize_log_output(output: str, max_length: int = 10000) -> str:
    """
    Sanitize log output to prevent log injection and limit size.
    
    Args:
        output: The log output to sanitize
        max_length: Maximum length of output to return
        
    Returns:
        Sanitized log output
    """
    if not output:
        return ""
    
    # Remove control characters that could manipulate terminal
    output = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', output)
    
    # Truncate if too long
    if len(output) > max_length:
        output = output[:max_length] + "\n... (truncated)"
    
    return output
