"""
Test database connection setup.
"""
import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from backend.db.database import async_engine
from backend.core.config import settings


async def test_connection():
    """Test database connection."""
    print(f"Testing connection to: {settings.database_url}")
    
    try:
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"Connection successful! Test query result: {row}")
            
    except Exception as e:
        print(f"Connection failed: {e}")
        return False
        
    finally:
        await async_engine.dispose()
        
    return True


if __name__ == "__main__":
    from sqlalchemy import text
    asyncio.run(test_connection())