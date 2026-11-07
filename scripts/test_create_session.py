import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from database.session import AsyncSessionLocal
from database.models import Session as SessionModel
import uuid

async def test():
    print("Testing direct DB session insert...")
    async with AsyncSessionLocal() as session:
        s = SessionModel(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            title="Direct Test",
            active_agent="core"
        )
        session.add(s)
        await session.commit()
        await session.refresh(s)
        print(f"Session created: {s.session_id}, id={s.id}, created_at={s.created_at}")

asyncio.run(test())
