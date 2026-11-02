"""Сохранение изображения графа в файл SVG (этап 5).

Изображение строит программа dot из пакета Graphviz
(https://graphviz.org): текст графа на языке DOT передаётся ей на
стандартный ввод, а результат в формате SVG записывается в файл.
Graphviz используется только для рисования; зависимости пакетов
программа получает сама, без менеджеров пакетов и сторонних библиотек.
"""
import subprocess

DOT_PROGRAM = "dot"
SVG_FORMAT = "-Tsvg"
DOWNLOAD_URL = "https://graphviz.org/download/"


class RenderError(Exception):
    """Не удалось построить или сохранить изображение графа."""


def render_svg(dot_text, output, program=DOT_PROGRAM):
    """Нарисовать граф по тексту DOT и сохранить в файл SVG output."""
    command = [program, SVG_FORMAT, "-o", output]
    try:
        done = subprocess.run(command, input=dot_text, capture_output=True,
                              encoding="utf-8")
    except FileNotFoundError:
        raise RenderError("не найдена программа " + program
                          + " из пакета Graphviz, установите Graphviz: "
                          + DOWNLOAD_URL) from None
    except OSError as error:
        raise RenderError("не удалось запустить " + program + ": "
                          + str(error)) from None
    if done.returncode:
        details = done.stderr.strip() or "код " + str(done.returncode)
        raise RenderError(program + " не смог сохранить изображение в "
                          + output + ": " + details)
