# skills/file_operations.py
"""
Comprehensive file manipulation operations for Bittu
Supports: create, read, write, delete, copy, move, rename, search, and more
"""
import os
import shutil
import re
from typing import Optional

from skills.path_utils import (
    get_base_output_dir,
    resolve_access_path,
    resolve_directory_path,
    resolve_output_path,
)

def handle(command: str) -> str:
    """Handle file manipulation commands"""
    command_lower = command.lower().strip()
    
    # Delete operations
    if any(keyword in command_lower for keyword in ["delete file", "remove file", "delete", "remove"]):
        return delete_file_operation(command)
    
    # Read operations
    elif any(keyword in command_lower for keyword in ["read file", "show file", "display file", "open file", "view file"]):
        return read_file_operation(command)
    
    # Write/Append operations
    elif any(keyword in command_lower for keyword in ["write to file", "append to file", "add to file"]):
        return write_file_operation(command)
    
    # Copy operations
    elif any(keyword in command_lower for keyword in ["copy file", "duplicate file"]):
        return copy_file_operation(command)
    
    # Move/Rename operations
    elif any(keyword in command_lower for keyword in ["move file", "rename file", "rename"]):
        return move_rename_operation(command)
    
    # Search in files
    elif any(keyword in command_lower for keyword in ["search in file", "find in file", "grep"]):
        return search_in_file_operation(command)
    
    # File info
    elif any(keyword in command_lower for keyword in ["file size", "file info", "file details"]):
        return file_info_operation(command)
    
    # List with details
    elif any(keyword in command_lower for keyword in ["list files detailed", "detailed list", "ls -l"]):
        return list_files_detailed(command)
    
    # Create directory
    elif any(keyword in command_lower for keyword in ["create folder", "create directory", "mkdir"]):
        return create_directory_operation(command)
    
    # Delete directory
    elif any(keyword in command_lower for keyword in ["delete folder", "remove folder", "delete directory", "rmdir"]):
        return delete_directory_operation(command)
    
    else:
        return get_file_operations_help()

def extract_filename(command: str) -> Optional[str]:
    """Extract filename from command"""
    patterns = [
        r'(?:file|filename)\s+([^\s]+)',
        r'([^\s]+\.(?:txt|py|js|html|css|json|md|log|csv|xml|yml|yaml|ini|cfg|conf))',
        r'["\']([^"\']+)["\']',
        r'(\S+\.\w+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1)
    # Try to extract last word as filename
    words = command.split()
    for word in reversed(words):
        if '.' in word or len(word) > 2:
            return word
    return None

def extract_path(command: str) -> Optional[str]:
    """Extract path from command"""
    patterns = [
        r'(?:to|in|from)\s+([^\s]+)',
        r'["\']([^"\']+)["\']',
        r'(\S+[/\\]\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_text_content(command: str) -> Optional[str]:
    """Extract text content to write from command"""
    # Look for content in quotes
    quote_match = re.search(r'["\']([^"\']+)["\']', command)
    if quote_match:
        return quote_match.group(1)
    
    # Look for content after keywords
    patterns = [
        r'(?:write|append|add|with text|containing)\s+(.+?)(?:\s+to|\s+in|$)',
        r'text\s+["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def delete_file_operation(command: str) -> str:
    """Delete a file"""
    filename = extract_filename(command)
    if not filename:
        return "❌ Please specify a filename. Example: 'delete file test.txt'"
    
    path = resolve_access_path(filename)
    if not path.exists():
        return f"❌ File '{path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    if path.is_dir():
        return f"❌ '{path.name}' is a directory. Use 'delete folder' instead."
    
    try:
        path.unlink()
        return f"✅ Deleted file: {path.name}\n📁 Location: {path}"
    except PermissionError:
        return f"❌ Permission denied. Cannot delete '{filename}'"
    except Exception as e:
        return f"❌ Error deleting file: {str(e)}"

def read_file_operation(command: str) -> str:
    """Read and display file contents"""
    filename = extract_filename(command)
    if not filename:
        return "❌ Please specify a filename. Example: 'read file test.txt'"
    
    path = resolve_access_path(filename)
    if not path.exists():
        return f"❌ File '{path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    if path.is_dir():
        return f"❌ '{path.name}' is a directory, not a file"
    
    try:
        # Check file size first (don't read huge files)
        file_size = path.stat().st_size
        if file_size > 1_000_000:  # 1MB limit
            return f"⚠️ File is too large ({file_size:,} bytes). Showing first 1000 characters only."
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if len(content) > 2000:
            content = content[:2000] + "\n... (truncated)"
        
        return f"📄 Contents of '{path.name}' (located at {path}):\n\n{content}"
    except UnicodeDecodeError:
        return f"❌ Cannot read '{filename}' as text file (binary file)"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"

def write_file_operation(command: str) -> str:
    """Write or append text to a file"""
    command_lower = command.lower()
    filename = extract_filename(command)
    text_content = extract_text_content(command)
    
    if not filename:
        return "❌ Please specify a filename. Example: 'write to file test.txt with text Hello World'"
    
    if not text_content:
        return "❌ Please specify text content. Example: 'write to file test.txt with text Hello World'"
    
    try:
        file_path = resolve_output_path(filename)
        if "append" in command_lower or "add" in command_lower:
            mode = 'a'
            action = "Appended"
        else:
            mode = 'w'
            action = "Wrote"
        
        with open(file_path, mode, encoding='utf-8') as f:
            if mode == 'a':
                f.write('\n' + text_content)
            else:
                f.write(text_content)
        
        return (
            f"✅ {action} to file: {file_path.name}\n"
            f"   Content: {text_content[:50]}{'...' if len(text_content) > 50 else ''}\n"
            f"📁 Location: {file_path}"
        )
    except Exception as e:
        return f"❌ Error writing to file: {str(e)}"

def copy_file_operation(command: str) -> str:
    """Copy a file to another location"""
    command_lower = command.lower()
    
    # Try to extract source and destination
    parts = command_lower.split()
    source = None
    dest = None
    
    # Look for "copy file X to Y" pattern
    if "to" in parts:
        to_index = parts.index("to")
        if to_index > 0:
            # Get filename before "to"
            source_candidates = parts[parts.index("file") + 1:to_index] if "file" in parts else parts[:to_index]
            source = ' '.join(source_candidates) if source_candidates else None
            # Get destination after "to"
            dest_candidates = parts[to_index + 1:]
            dest = ' '.join(dest_candidates) if dest_candidates else None
    
    if not source:
        source = extract_filename(command)
    if not dest:
        dest = extract_path(command)
    
    if not source:
        return "❌ Please specify source file. Example: 'copy file test.txt to backup.txt'"
    if not dest:
        return "❌ Please specify destination. Example: 'copy file test.txt to backup.txt'"
    
    source_path = resolve_access_path(source)
    dest_path = resolve_output_path(dest)
    
    if not source_path.exists():
        return f"❌ Source file '{source_path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    if source_path.is_dir():
        return f"❌ '{source_path.name}' is a directory. Use 'copy folder' instead."
    
    try:
        shutil.copy2(source_path, dest_path)
        return f"✅ Copied '{source_path.name}' to '{dest_path.name}'\n📁 Destination: {dest_path}"
    except Exception as e:
        return f"❌ Error copying file: {str(e)}"

def move_rename_operation(command: str) -> str:
    """Move or rename a file"""
    command_lower = command.lower()
    
    # Try to extract source and destination
    parts = command_lower.split()
    source = None
    dest = None
    
    # Look for "rename/move X to Y" pattern
    if "to" in parts:
        to_index = parts.index("to")
        if to_index > 0:
            source_candidates = parts[1:to_index] if len(parts) > 1 else []
            source = ' '.join(source_candidates) if source_candidates else None
            dest_candidates = parts[to_index + 1:]
            dest = ' '.join(dest_candidates) if dest_candidates else None
    
    if not source:
        source = extract_filename(command)
    if not dest:
        dest = extract_path(command)
    
    if not source:
        return "❌ Please specify source file. Example: 'rename file old.txt to new.txt'"
    if not dest:
        return "❌ Please specify new name. Example: 'rename file old.txt to new.txt'"
    
    source_path = resolve_access_path(source)
    dest_path = resolve_output_path(dest)
    
    if not source_path.exists():
        return f"❌ Source file '{source_path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    if source_path.is_dir():
        return f"❌ '{source_path.name}' is a directory. Use 'rename folder' instead."
    
    try:
        shutil.move(str(source_path), str(dest_path))
        action = "Renamed" if "rename" in command_lower else "Moved"
        return f"✅ {action} '{source_path.name}' to '{dest_path.name}'\n📁 Location: {dest_path}"
    except Exception as e:
        return f"❌ Error moving/renaming file: {str(e)}"

def search_in_file_operation(command: str) -> str:
    """Search for text in a file"""
    filename = extract_filename(command)
    search_text = extract_text_content(command)
    
    if not filename:
        return "❌ Please specify a filename. Example: 'search in file test.txt for hello'"
    
    if not search_text:
        # Try to extract search term
        patterns = [
            r'(?:for|search|find)\s+["\']?([^"\']+)["\']?',
            r'["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                search_text = match.group(1)
                break
    
    if not search_text:
        return "❌ Please specify search text. Example: 'search in file test.txt for hello'"
    
    path = resolve_access_path(filename)
    if not path.exists():
        return f"❌ File '{path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    if path.is_dir():
        return f"❌ '{path.name}' is a directory, not a file"
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        matches = []
        for line_num, line in enumerate(lines, 1):
            if search_text.lower() in line.lower():
                matches.append(f"Line {line_num}: {line.strip()}")
        
        if matches:
            result = f"🔍 Found '{search_text}' in '{path.name}':\n\n"
            result += "\n".join(matches[:20])  # Limit to 20 matches
            if len(matches) > 20:
                result += f"\n... and {len(matches) - 20} more matches"
            return result
        else:
            return f"❌ No matches found for '{search_text}' in '{path.name}'"
    except Exception as e:
        return f"❌ Error searching in file: {str(e)}"

def file_info_operation(command: str) -> str:
    """Get file information"""
    filename = extract_filename(command)
    if not filename:
        return "❌ Please specify a filename. Example: 'file info test.txt'"
    
    path = resolve_access_path(filename)
    if not path.exists():
        return f"❌ File '{path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    try:
        stat = path.stat()
        size = stat.st_size
        size_str = f"{size:,} bytes"
        if size > 1024:
            size_str += f" ({size/1024:.2f} KB)"
        if size > 1024*1024:
            size_str += f" ({size/(1024*1024):.2f} MB)"
        
        from datetime import datetime
        created = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        info = f"📄 File Information: {path.name}\n"
        info += f"   Size: {size_str}\n"
        info += f"   Created: {created}\n"
        info += f"   Modified: {modified}\n"
        info += f"   Type: {'Directory' if path.is_dir() else 'File'}\n"
        info += f"   Location: {path}\n"
        
        if path.is_file():
            ext = path.suffix
            info += f"   Extension: {ext if ext else 'None'}\n"
        
        return info
    except Exception as e:
        return f"❌ Error getting file info: {str(e)}"

def list_files_detailed(command: str) -> str:
    """List files with detailed information"""
    try:
        base_dir = get_base_output_dir()
        files = os.listdir(base_dir)
        if not files:
            return f"📁 Sandbox directory ({base_dir}) is empty"
        
        from datetime import datetime
        result = f"📁 Detailed contents of {base_dir}:\n\n"
        
        for f in sorted(files):
            try:
                full_path = base_dir / f
                stat = full_path.stat()
                size = stat.st_size
                size_str = f"{size:,} B"
                if size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                file_type = "📁" if full_path.is_dir() else "📄"
                result += f"{file_type} {f:<30} {size_str:>10} {modified}\n"
            except:
                result += f"❓ {f}\n"
        
        return result
    except Exception as e:
        return f"❌ Error listing files: {str(e)}"

def create_directory_operation(command: str) -> str:
    """Create a directory"""
    folder_name = extract_path(command) or extract_filename(command)
    if not folder_name:
        return "❌ Please specify folder name. Example: 'create folder myfolder'"
    
    try:
        folder_path = resolve_directory_path(folder_name)
        return f"✅ Created folder: {folder_path.name}\n📁 Location: {folder_path}"
    except Exception as e:
        return f"❌ Error creating folder: {str(e)}"

def delete_directory_operation(command: str) -> str:
    """Delete a directory"""
    folder_name = extract_path(command) or extract_filename(command)
    if not folder_name:
        return "❌ Please specify folder name. Example: 'delete folder myfolder'"
    
    folder_path = resolve_access_path(folder_name)
    if not folder_path.exists():
        return f"❌ Folder '{folder_path.name}' does not exist in sandbox directory ({get_base_output_dir()})"
    
    if not folder_path.is_dir():
        return f"❌ '{folder_path.name}' is not a directory"
    
    try:
        # Check if directory is empty
        if os.listdir(folder_path):
            # Ask for confirmation for non-empty directories
            if "force" not in command.lower() and "now" not in command.lower():
                return f"⚠️ Folder '{folder_path.name}' is not empty. Use 'delete folder {folder_path.name} force' to delete it."
            shutil.rmtree(folder_path)
            return f"✅ Deleted folder: {folder_path.name} (and all contents)"
        else:
            folder_path.rmdir()
            return f"✅ Deleted empty folder: {folder_path.name}"
    except Exception as e:
        return f"❌ Error deleting folder: {str(e)}"

def get_file_operations_help() -> str:
    """Return help text for file operations"""
    return """📁 File Operations Available:

**Create:**
• create file filename.txt
• create folder myfolder

**Read:**
• read file filename.txt
• show file filename.txt
• view file filename.txt

**Write:**
• write to file filename.txt with text "content"
• append to file filename.txt with text "content"

**Delete:**
• delete file filename.txt
• delete folder myfolder
• delete folder myfolder force (for non-empty folders)

**Copy/Move:**
• copy file source.txt to destination.txt
• move file old.txt to new.txt
• rename file old.txt to new.txt

**Search:**
• search in file filename.txt for "text"
• find in file filename.txt "text"

**Info:**
• file info filename.txt
• file size filename.txt
• list files detailed

**Navigation:**
• cd folder_name
• navigate to path
"""

