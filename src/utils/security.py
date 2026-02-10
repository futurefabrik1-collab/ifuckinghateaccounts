"""
Security Utilities

Provides validation and sanitization functions for secure file handling.
"""

import re
from pathlib import Path
from typing import Tuple
from werkzeug.datastructures import FileStorage
from config import Config
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails"""
    pass


def sanitize_filename(filename: str) -> str:
    """
    Remove dangerous characters from filename
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove leading dots (hidden files)
    filename = filename.lstrip('.')
    
    # Only allow alphanumeric, dash, underscore, dot, space
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Collapse multiple spaces
    filename = re.sub(r'\s+', ' ', filename)
    
    # Limit length
    if len(filename) > 255:
        # Preserve extension
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1
        filename = name[:max_name_len] + ('.' + ext if ext else '')
    
    # Ensure not empty
    if not filename or filename == '.':
        raise SecurityError("Invalid filename after sanitization")
    
    return filename


def validate_path_traversal(base_path: Path, requested_path: Path) -> Path:
    """
    Validate that requested path is within base directory (prevent path traversal)
    
    Args:
        base_path: Base directory that must contain the file
        requested_path: Requested file path
    
    Returns:
        Resolved path if valid
    
    Raises:
        SecurityError: If path traversal detected
    """
    # Resolve both paths to absolute
    base_resolved = base_path.resolve()
    requested_resolved = requested_path.resolve()
    
    # Check if requested path is within base path
    try:
        requested_resolved.relative_to(base_resolved)
    except ValueError:
        logger.warning(f"Path traversal attempt detected: {requested_path} not in {base_path}")
        raise SecurityError("Invalid file path - access denied")
    
    return requested_resolved


def validate_file_upload(file: FileStorage, allowed_extensions: set) -> Tuple[str, int]:
    """
    Validate uploaded file for security
    
    Args:
        file: Uploaded file object
        allowed_extensions: Set of allowed file extensions
    
    Returns:
        Tuple of (sanitized_filename, file_size)
    
    Raises:
        SecurityError: If validation fails
    """
    # Check if file exists
    if not file or file.filename == '':
        raise SecurityError("No file provided")
    
    # Sanitize filename
    try:
        safe_filename = sanitize_filename(file.filename)
    except SecurityError as e:
        raise SecurityError(f"Invalid filename: {str(e)}")
    
    # Check extension
    if '.' not in safe_filename:
        raise SecurityError("File must have an extension")
    
    ext = safe_filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise SecurityError(
            f"File type .{ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if size == 0:
        raise SecurityError("File is empty")
    
    if size > Config.MAX_FILE_SIZE:
        size_mb = size / (1024 * 1024)
        max_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
        raise SecurityError(f"File too large: {size_mb:.1f}MB (max: {max_mb:.1f}MB)")
    
    # Try to detect MIME type (optional, requires python-magic)
    try:
        import magic
        
        # Read first 2048 bytes for MIME detection
        file_header = file.read(2048)
        file.seek(0)
        
        mime = magic.from_buffer(file_header, mime=True)
        
        # Validate MIME type matches extension
        if mime in Config.ALLOWED_MIME_TYPES:
            if ext not in [e.lstrip('.') for e in Config.ALLOWED_MIME_TYPES[mime]]:
                logger.warning(f"MIME type {mime} doesn't match extension .{ext}")
                raise SecurityError(f"File type mismatch: extension .{ext} but MIME type is {mime}")
        else:
            logger.warning(f"Unrecognized MIME type: {mime}")
            # Don't fail - just log warning
    except ImportError:
        logger.debug("python-magic not installed - skipping MIME type validation")
    except Exception as e:
        logger.warning(f"MIME type detection failed: {e}")
        # Don't fail the upload if MIME detection fails
    
    logger.info(f"File validated: {safe_filename} ({size} bytes)")
    
    return safe_filename, size


def validate_statement_name(statement_name: str) -> str:
    """
    Validate statement name for security
    
    Args:
        statement_name: Statement name to validate
    
    Returns:
        Validated statement name
    
    Raises:
        SecurityError: If validation fails
    """
    if not statement_name:
        raise SecurityError("Statement name is required")
    
    # Basic sanitization
    statement_name = statement_name.strip()
    
    # Check for path traversal attempts
    if '..' in statement_name or '/' in statement_name or '\\' in statement_name:
        raise SecurityError("Invalid statement name")
    
    # Check length
    if len(statement_name) > 255:
        raise SecurityError("Statement name too long")
    
    return statement_name


def validate_row_number(row_number: any, max_rows: int = 10000) -> int:
    """
    Validate row number input
    
    Args:
        row_number: Row number to validate
        max_rows: Maximum allowed row number
    
    Returns:
        Validated row number as integer
    
    Raises:
        SecurityError: If validation fails
    """
    try:
        row_num = int(row_number)
    except (ValueError, TypeError):
        raise SecurityError("Invalid row number - must be an integer")
    
    if row_num < 1:
        raise SecurityError("Row number must be positive")
    
    if row_num > max_rows:
        raise SecurityError(f"Row number too large (max: {max_rows})")
    
    return row_num
