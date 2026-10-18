"""Запуск приложения из командной строки.

На этапе 1 приложение разбирает и проверяет параметры и выводит их в
формате ``ключ=значение``. При ошибках каждое сообщение выводится в
стандартный поток ошибок, а программа завершается с кодом 2.
"""
import sys

from depviz.config import ConfigError, load_config

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def format_config(config):
    """Вернуть параметры в виде строк ``ключ=значение``."""
    return "\n".join(key + "=" + value for key, value in config.items())


def main(argv=None, stdout=None, stderr=None):
    """Разобрать параметры argv, вывести их и вернуть код завершения."""
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    try:
        config = load_config(sys.argv[1:] if argv is None else argv)
    except ConfigError as error:
        for message in error.errors:
            print("ошибка: " + message, file=stderr)
        return EXIT_CONFIG_ERROR
    print(format_config(config), file=stdout)
    return EXIT_OK
