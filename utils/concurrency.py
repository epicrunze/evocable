import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

class BoundedRAMSemaphore:
    """Semaphore to cap RAM usage."""
    def __init__(self, max_workers):
        self.semaphore = threading.BoundedSemaphore(max_workers)
    def acquire(self):
        self.semaphore.acquire()
    def release(self):
        self.semaphore.release()

async def run_async_pool(coros, max_workers=4):
    """Run coroutines with a bounded pool."""
    sem = asyncio.Semaphore(max_workers)
    async def sem_task(coro):
        async with sem:
            return await coro
    return await asyncio.gather(*(sem_task(c) for c in coros))

def run_thread_pool(func, items, max_workers=4):
    """Run function in a thread pool with progress bar."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(executor.map(func, items), total=len(items))) 