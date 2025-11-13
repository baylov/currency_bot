import asyncio
from datetime import datetime
from typing import Any, Coroutine, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


async def run_parallel(*coroutines: Coroutine) -> List[Any]:
    """Run multiple coroutines in parallel and return their results."""
    try:
        return await asyncio.gather(*coroutines, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error running parallel coroutines: {e}")
        raise


async def safe_run(coroutine: Coroutine, default: Any = None) -> Any:
    """Safely run a coroutine and return default value on error."""
    try:
        return await coroutine
    except Exception as e:
        logger.error(f"Error in safe execution: {e}")
        return default


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string."""
    if dt is None:
        return "N/A"
    try:
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return str(dt)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to specified maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """Escape special markdown characters."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def split_text(text: str, max_length: int = 4096) -> List[str]:
    """Split long text into chunks of specified maximum length."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = line
            else:
                # Line itself is too long, split it
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                current_chunk = line
        else:
            current_chunk += '\n' + line if current_chunk else line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks