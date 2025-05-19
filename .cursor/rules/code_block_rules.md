# Code Block Formatting Rules

## File Path Display
- Always show the full file path in the top-left corner of code blocks
- For new files, use the format: ````python:path/to/new/file.py`
- For existing files, use the format: ````python:path/to/existing/file.py`

## Code Block Types
1. **New Files**
   - Show complete file content
   - Include all necessary imports and dependencies
   - Add file-level docstring explaining purpose

2. **File Edits**
   - Use `// ... existing code ...` to indicate unchanged sections
   - Show enough context before and after changes (2-3 lines)
   - Clearly mark where changes begin and end

## Directory Structure
- When creating new directories/files, first show the command to create the directory
- Then show the new file content
- Finally, show the resulting directory structure

## Example Format
```python:src/example/new_file.py
# New file content here
```

```python:src/example/existing_file.py
// ... existing code ...
# Changes here
// ... existing code ...
```

## Best Practices
- Always verify file/directory exists before referencing
- Show directory creation commands when needed
- Provide clear context for where changes should be made
- Use consistent indentation and formatting
