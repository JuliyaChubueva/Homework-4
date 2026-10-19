"""
Задание 3 (*). Вынос CPU-bound-вычислений

Замеры (heavy по 20 скачанным картинкам):
    heavy прямо в корутине:             2.97 s — точки ticker остановились
    heavy через ProcessPoolExecutor:    1.62 s — точки продолжали печататься
    cpu_main целиком:                   7.67 s

    Вывод программы:
        heavy в лоб (точки должны остановиться) .....
          в лоб: 2.97s
        heavy в процессах (точки бегут) ..................
          в процессах: 1.62s
    Пять точек в первой строке успели появиться за 0,5 с паузы до начала
    вычислений, а за 2.97 с самого счёта не появилось ни одной. Во второй
    строке точки печатались всё время, пока процессы считали хеши.

Объяснение:
    heavy — обычная синхронная CPU-bound функция, внутри неё нет ни одной
    точки переключения (await). Многозадачность в asyncio кооперативная:
    задача уступает управление только сама. Если вызвать heavy прямо
    в корутине, она не уступит, и event loop не сможет переключиться на
    другие задачи, пока она не закончит считать. Поэтому ticker не получает
    управления и точки замирают — loop заблокирован.
    loop.run_in_executor + ProcessPoolExecutor отправляет вычисления
    в отдельные процессы, а корутина просто ждёт результат через await.
    Event loop при этом свободен, и ticker продолжает печатать точки.
    Кроме того, процессы считают на нескольких ядрах одновременно, поэтому
    вышло почти в 2 раза быстрее (2.97 s -> 1.62 s).
    ThreadPoolExecutor здесь не подошёл бы: из-за GIL потоки не дают
    выигрыша на вычислениях в Python.
"""

import asyncio
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor

import httpx
import requests

# 20 разных картинок (у каждой свой номер в адресе)
URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]


def timed(label, fn, *args):
    """Запускает fn(*args) и печатает, сколько секунд она работала."""
    start = time.perf_counter()
    fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")


def heavy(body: bytes) -> str:
    # body * 1000 раздувает данные, чтобы хеш считался заметно долго
    return hashlib.sha256(body * 1000).hexdigest()


async def ticker():
    # «пульс» event loop: если точки перестали печататься — loop заблокирован
    while True:
        print(".", end="", flush=True)
        await asyncio.sleep(0.1)


async def download_all() -> list[bytes]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        responses = await asyncio.gather(*(client.get(url) for url in URLS))
    for response in responses:
        response.raise_for_status()
    return [response.content for response in responses]


async def cpu_main():
    # 1) ticker работает фоном всё время
    tick = asyncio.create_task(ticker())

    print("Скачиваю картинки ", end="")
    bodies = await download_all()

    # 2) «в лоб»: heavy прямо в корутине — точки замрут
    print("\nheavy в лоб (точки должны остановиться) ", end="")
    await asyncio.sleep(0.5)  # даём точкам побежать, чтобы была видна остановка
    start = time.perf_counter()
    hashes_direct = [heavy(body) for body in bodies]
    print(f"\n  в лоб: {time.perf_counter() - start:.2f}s")

    # 3) через процессы — точки продолжают печататься
    print("heavy в процессах (точки бегут) ", end="")
    await asyncio.sleep(0.5)
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    with ProcessPoolExecutor() as pool:
        hashes_pool = await asyncio.gather(
            *(loop.run_in_executor(pool, heavy, body) for body in bodies)
        )
    print(f"\n  в процессах: {time.perf_counter() - start:.2f}s")

    print(f"Хеши совпадают: {hashes_direct == list(hashes_pool)}")

    # 4) останавливаем ticker
    tick.cancel()
    try:
        await tick
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    # проверка обязательна: без неё ProcessPoolExecutor падает на Windows
    # и macOS — дочерние процессы заново импортируют этот файл
    timed("cpu  ", lambda: asyncio.run(cpu_main()))