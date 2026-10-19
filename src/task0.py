"""
Задание 0. Разминка-ловушка «Почему не быстрее?»

Замеры (20 картинок с picsum.photos):
    slow  (await внутри цикла for): 11.03 s
    fixed (asyncio.gather):         1.31 s

Почему async не дал ускорения:
    В slow_main стоит await fetch(...) прямо внутри цикла for. await —
    это точка переключения, но он дожидается результата «здесь и сейчас»:
    корутина приостанавливается до получения ответа, и следующий запрос
    даже не начинается, пока не закончится предыдущий. В event loop в каждый
    момент есть всего одна задача, переключаться не на что. Запросы идут
    строго по очереди, как обычный цикл с requests, и время всех 20 запросов
    складывается. Ключевое слово async само по себе ничего не ускоряет:
    выигрыш появляется, только когда задачи запущены вместе и их ожидания
    накладываются друг на друга.

Как починила:
    В fixed_main сначала создаются корутины для всех 20 URL, а потом они
    запускаются вместе через asyncio.gather. Пока один запрос ждёт сервер,
    event loop отправляет остальные, поэтому общее время примерно равно
    времени самого медленного запроса, а не сумме всех. Получилось
    примерно в 8 раз быстрее (11.03 s -> 1.31 s).
    follow_redirects=True нужен, потому что picsum отвечает редиректом 302,
    а httpx по умолчанию по нему не переходит.
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


async def slow_main():
    """Исходная версия: запросы идут по очереди."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for url in URLS:
            await fetch(client, url)  # ждём каждый ответ, прежде чем идти дальше


async def fixed_main():
    """Исправленная версия: все запросы запускаются конкурентно."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch(client, url) for url in URLS]
        statuses = await asyncio.gather(*tasks)
    print(f"Получено ответов: {len(statuses)}, со статусом 200: {statuses.count(200)}")


if __name__ == "__main__":
    timed("slow ", lambda: asyncio.run(slow_main()))
    timed("fixed", lambda: asyncio.run(fixed_main()))