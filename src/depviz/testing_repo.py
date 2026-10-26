"""Файл тестового репозитория (режим ``--mode test``).

Каждая строка файла описывает один пакет и его прямые зависимости::

    A: B C
    B: D
    D:

Имена пакетов — большие латинские буквы. Пустые строки и строки,
начинающиеся с ``#``, пропускаются. Пакет без зависимостей
записывается с пустым списком после двоеточия.
"""
from depviz.registry import DataError, Dependency
from depviz.validators import TEST_PACKAGE_RE

COMMENT_PREFIX = "#"
SEPARATOR = ":"
NO_REQUIREMENT = ""


def check_name(name, number):
    """Проверить имя пакета в строке number файла."""
    if not TEST_PACKAGE_RE.fullmatch(name):
        raise DataError("строка " + str(number) + ": имя пакета «" + name
                        + "» должно состоять из больших латинских букв")


def parse_line(line, number):
    """Разобрать строку ``ИМЯ: ЗАВИСИМОСТИ`` в пару (имя, список)."""
    if SEPARATOR not in line:
        raise DataError("строка " + str(number) + ": ожидается формат "
                        "«ПАКЕТ: ЗАВИСИМОСТЬ ...»")
    name, _, rest = line.partition(SEPARATOR)
    name = name.strip()
    check_name(name, number)
    dependencies = rest.split()
    for dependency in dependencies:
        check_name(dependency, number)
    if len(set(dependencies)) != len(dependencies):
        raise DataError("строка " + str(number) + ": зависимость указана "
                        "дважды")
    return name, dependencies


def parse_test_repo(text):
    """Разобрать текст файла в словарь {пакет: [зависимости]}."""
    graph = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        name, dependencies = parse_line(line, number)
        if name in graph:
            raise DataError("строка " + str(number) + ": пакет " + name
                            + " описан повторно")
        graph[name] = dependencies
    return graph


def load_test_repo(path):
    """Прочитать файл тестового репозитория."""
    try:
        with open(path, "r", encoding="utf-8") as repo_file:
            return parse_test_repo(repo_file.read())
    except OSError as error:
        raise DataError("не удалось прочитать тестовый репозиторий: "
                        + str(error))
    except UnicodeDecodeError:
        raise DataError("тестовый репозиторий не в кодировке UTF-8")


def file_dependencies(path, name):
    """Вернуть прямые зависимости пакета name из тестового репозитория."""
    graph = load_test_repo(path)
    if name not in graph:
        raise DataError("пакет " + name + " не описан в тестовом "
                        "репозитории " + path)
    return [Dependency(dependency, NO_REQUIREMENT)
            for dependency in graph[name]]
