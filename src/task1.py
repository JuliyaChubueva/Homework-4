"""
Задание 1. Синхронно vs асинхронно

Замеры (20 картинок с picsum.photos):
    sync  (requests, по очереди):               28.20 s
    async (httpx.AsyncClient + asyncio.gather):  1.91 s

Объяснение разницы:
    requests ждёт каждый ответ по очереди, и время 20 запросов складывается,
    а в async-версии все 20 запросов ждут ответа одновременно, поэтому общее
    время близко к времени одного самого медленного запроса (примерно
    в 15 раз быстрее).
"""

import asyncio
import time

import httpx
import requests

# 20 разных картинок (у каждой свой номер в адресе)
URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]


def timed(label, fn, *args):
    """Запускает fn(*args) и печатает, сколько секунд она работала."""
    start = time.perf_counter()
    fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")


async def fetch(client: httpx.AsyncClient, url: str) -> int:
    resp = await client.get(url)
    return resp.status_code


def sync_main():
    """Синхронная версия: каждый запрос начинается после окончания предыдущего."""
    statuses = []
    for url in URLS:
        response = requests.get(url, timeout=10)
        statuses.append(response.status_code)
    print(f"  sync: со статусом 200 — {statuses.count(200)} из {len(URLS)}")


async def fast_main():
    """Асинхронная версия: все запросы запускаются сразу через asyncio.gather."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        statuses = await asyncio.gather(*(fetch(client, url) for url in URLS))
    print(f"  async: со статусом 200 — {statuses.count(200)} из {len(URLS)}")


if __name__ == "__main__":
    timed("sync ", sync_main)
    timed("async", lambda: asyncio.run(fast_main()))