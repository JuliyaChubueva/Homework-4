"""
Задание 2. Реальный I/O и обработка ошибок

Замеры (20 картинок + 2 битых URL):
    robust: 21.30 s
    Результат: успешно 20, ошибок 2
        https://no-such-site.invalid -> ConnectError
        https://httpbin.org/delay/10 -> ReadTimeout

Что сделано:
    - Таймаут: TIMEOUT = 5 секунд на каждый запрос. httpbin.org/delay/10
      отвечает только через 10 секунд, поэтому на нём срабатывает ReadTimeout.
    - Ретраи: не больше MAX_ATTEMPTS = 3 попыток. Перед повтором ждём
      2 ** attempt секунд (1 с, потом 2 с — пауза растёт вдвое) плюс
      небольшую случайную добавку до 0,5 с (jitter), чтобы повторные
      запросы не уходили на сервер все в один момент.
    - Повторяем только временные сбои, которые могут пройти со второго раза:
      таймауты, ошибки соединения, ответы 5xx и 429 (Too Many Requests).
      Ошибки вроде 400 или 404 повтор не исправит, поэтому такая ошибка
      сразу считается окончательной. raise_for_status() нужен потому, что
      httpx сам не выбрасывает исключение на ответы 4xx и 5xx.
    - Устойчивость: по умолчанию asyncio.gather выбрасывает первую же ошибку,
      и результаты остальных задач теряются. Поэтому каждый URL обрабатывается
      в safe_fetch, которая ловит исключение внутри задачи и возвращает его
      как обычный результат. Один битый URL не роняет остальные, а
      robust_main возвращает кортеж (список результатов, список ошибок).

Почему получилось ~21 секунда:
    Дольше всех работает httpbin.org/delay/10: три попытки по 5 с таймаута
    и паузы 1.2 с и 2.5 с между ними — около 19 с, плюс время на соединение.
    Картинки за это время успевают скачаться параллельно, поэтому общее время
    определяется именно этим URL.
    Для no-such-site.invalid первые две попытки закончились ConnectTimeout:
    поиск несуществующего домена (DNS) на Windows занял дольше таймаута.
    Третья попытка вернула ConnectError — домена не существует.
"""

import asyncio
import random
import time

import httpx
import requests

# 20 разных картинок (у каждой свой номер в адресе)
URLS = [f"https://picsum.photos/seed/{i}/800/600" for i in range(20)]

# Битые адреса для проверки
URLS += [
    "https://no-such-site.invalid",  # домена не существует
    "https://httpbin.org/delay/10",  # отвечает 10 секунд, сработает таймаут
]

TIMEOUT = 5
MAX_ATTEMPTS = 3


def timed(label, fn, *args):
    """Запускает fn(*args) и печатает, сколько секунд она работала."""
    start = time.perf_counter()
    fn(*args)
    print(f"{label}: {time.perf_counter() - start:.2f}s")


def is_retryable(error: httpx.HTTPError) -> bool:
    """Повторяем только временные сбои: таймауты, соединение, 5xx и 429."""
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status >= 500 or status == 429
    return True


async def robust_fetch(client: httpx.AsyncClient, url: str) -> int:
    """Скачивает URL с таймаутом и не более чем MAX_ATTEMPTS попытками."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.status_code

        except httpx.HTTPError as error:
            if attempt == MAX_ATTEMPTS - 1 or not is_retryable(error):
                raise

            delay = 2 ** attempt + random.uniform(0, 0.5)
            print(f"{url}: попытка {attempt + 1} — {type(error).__name__}, "
                  f"повтор через {delay:.1f} с")
            await asyncio.sleep(delay)


async def safe_fetch(client: httpx.AsyncClient, url: str):
    """Обёртка: вместо исключения возвращает ("error", описание)."""
    try:
        return "ok", await robust_fetch(client, url)
    except httpx.HTTPError as error:
        message = str(error) or "нет ответа за отведённое время"
        return "error", f"{type(error).__name__}: {message}"


async def robust_main():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        outcomes = await asyncio.gather(*(safe_fetch(client, url) for url in URLS))

    results = []
    errors = []
    for url, (kind, value) in zip(URLS, outcomes):
        if kind == "ok":
            results.append({"url": url, "status": value})
        else:
            errors.append({"url": url, "error": value})
    return results, errors


def run():
    results, errors = asyncio.run(robust_main())
    print(f"\nУспешно: {len(results)}")
    print(f"Ошибок: {len(errors)}")
    for error in errors:
        print(f"  {error['url']} -> {error['error']}")


if __name__ == "__main__":
    timed("robust", run)