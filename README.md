# Homework 4 — Асинхронное программирование в Python

Сквозной сюжет — асинхронный загрузчик URL (20 картинок с picsum.photos).

| Файл | Задание |
|---|---|
| `src/task0.py` | Задание 0. Разминка-ловушка «Почему не быстрее?» |
| `src/task1.py` | Задание 1. Синхронно (`requests`) vs асинхронно (`httpx` + `asyncio.gather`) |
| `src/task2.py` | Задание 2. Таймаут, ретраи с экспоненциальным backoff, обработка ошибок |
| `src/task3.py` | Задание 3*. Вынос CPU-bound-вычислений в `ProcessPoolExecutor` |
| `theory.md` | Теоретическая часть |

Объяснения и замеры времени находятся в docstring в начале каждого файла.

## Установка

Нужен Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux, macOS
pip install -r requirements.txt
```

## Запуск

Из корневой папки проекта:

```bash
python src/task0.py
python src/task1.py
python src/task2.py
python src/task3.py
```
