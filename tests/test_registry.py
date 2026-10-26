"""Модульные тесты для depviz.registry (без обращения к сети)."""
import http.server
from http import HTTPStatus
import json
import os
import threading
import unittest
from unittest import mock

from depviz.registry import (ConnectionFailed, DataError, Dependency,
                             check_index, fetch_text, index_path,
                             make_dependency, parse_index,
                             remote_dependencies, select_version,
                             sort_dependencies)

REPO = "https://index.example.org"
CONFIG = json.dumps({"dl": "https://example.org/crates"})


def entry(version, deps=(), yanked=False):
    """Создать запись индекса о версии."""
    return {"name": "demo", "vers": version, "deps": list(deps),
            "yanked": yanked}


def index_text(*entries):
    """Собрать текст файла индекса из записей."""
    return "\n".join(json.dumps(item) for item in entries) + "\n"


class FakeRepo:
    """Подмена загрузки: словарь {URL: текст}, иначе пакета нет."""

    def __init__(self, files):
        """Запомнить файлы репозитория."""
        self.files = files
        self.urls = []

    def __call__(self, url):
        """Вернуть текст файла или сообщить, что его нет."""
        self.urls.append(url)
        if url not in self.files:
            raise DataError("пакет не найден в репозитории (" + url + ")")
        return self.files[url]


class IndexPathTest(unittest.TestCase):
    """Проверка путей к файлам пакетов в sparse-индексе."""

    def test_paths(self):
        """Правила Cargo для имён разной длины, нижний регистр."""
        cases = [("a", "1/a"), ("ab", "2/ab"), ("log", "3/l/log"),
                 ("serde", "se/rd/serde"), ("Serde_JSON",
                                            "se/rd/serde_json"),
                 ("syn2", "sy/n2/syn2")]
        for name, path in cases:
            with self.subTest(name=name):
                self.assertEqual(index_path(name), path)


class ParseIndexTest(unittest.TestCase):
    """Проверка разбора файла индекса."""

    def test_parse(self):
        """Каждая непустая строка — запись о версии."""
        text = index_text(entry("1.0.0"), entry("1.1.0")) + "\n"
        self.assertEqual(len(parse_index(text, "demo")), 2)

    def test_errors(self):
        """Не JSON, нет версии, пустой файл — ошибки."""
        cases = [("not json\n", "не JSON"),
                 ('{"name": "demo"}\n', "нет версии"),
                 ("[1, 2]\n", "нет версии"),
                 ("\n", "нет ни одной версии")]
        for text, message in cases:
            with self.subTest(text=text):
                with self.assertRaisesRegex(DataError, message):
                    parse_index(text, "demo")


class SelectVersionTest(unittest.TestCase):
    """Проверка выбора версии."""

    def test_latest_skips_yanked_and_prerelease(self):
        """latest — наибольшая неотозванная версия без пререлиза."""
        entries = [entry("1.2.0"), entry("1.10.0"),
                   entry("1.11.0", yanked=True), entry("2.0.0-beta.1")]
        self.assertEqual(select_version(entries, "latest")["vers"],
                         "1.10.0")

    def test_latest_prerelease_only(self):
        """Если есть только пререлизы, берётся наибольший из них."""
        entries = [entry("0.1.0-alpha"), entry("0.1.0-beta")]
        self.assertEqual(select_version(entries, "latest")["vers"],
                         "0.1.0-beta")

    def test_latest_all_yanked(self):
        """Если все версии отозваны, latest выбрать нельзя."""
        with self.assertRaisesRegex(DataError, "отозваны"):
            select_version([entry("1.0.0", yanked=True)], "latest")

    def test_exact_version(self):
        """Точная версия выбирается, даже если она отозвана."""
        entries = [entry("1.0.0", yanked=True), entry("1.1.0")]
        self.assertEqual(select_version(entries, "1.0.0")["vers"], "1.0.0")

    def test_missing_version_lists_recent(self):
        """Для отсутствующей версии подсказываются последние версии."""
        entries = [entry("1.0." + str(patch)) for patch in range(7)]
        with self.assertRaises(DataError) as context:
            select_version(entries, "9.9.9")
        self.assertIn("1.0.2, 1.0.3, 1.0.4, 1.0.5, 1.0.6",
                      str(context.exception))


class DependencyTest(unittest.TestCase):
    """Проверка описания зависимостей."""

    def test_defaults(self):
        """Отсутствующие поля получают значения по умолчанию."""
        dependency = make_dependency({"name": "libc", "kind": None,
                                      "target": None})
        self.assertEqual(dependency, Dependency("libc", "*"))

    def test_renamed(self):
        """При переименовании настоящее имя пакета берётся из package."""
        dependency = make_dependency({"name": "rand_old", "req": "^0.7",
                                      "package": "rand"})
        self.assertEqual(dependency.crate(), "rand")

    def test_sort(self):
        """Порядок: normal, build, dev, затем по имени."""
        items = [Dependency("z", "1", "dev"), Dependency("b", "1"),
                 Dependency("c", "1", "build"), Dependency("a", "1")]
        self.assertEqual([item.name for item in sort_dependencies(items)],
                         ["a", "b", "c", "z"])


class RemoteDependenciesTest(unittest.TestCase):
    """Проверка получения прямых зависимостей с подменой загрузки."""

    def setUp(self):
        """Подготовить репозиторий с пакетом demo."""
        deps = [{"name": "serde", "req": "^1", "kind": "normal",
                 "optional": True, "target": None},
                {"name": "cc", "req": "^1.0", "kind": "build"}]
        self.fetch = FakeRepo({
            REPO + "/config.json": CONFIG,
            REPO + "/de/mo/demo": index_text(entry("0.9.0"),
                                             entry("1.0.0", deps)),
        })

    def test_dependencies(self):
        """Возвращаются запись о версии и отсортированные зависимости."""
        version, deps = remote_dependencies(REPO + "/", "demo", "latest",
                                            self.fetch)
        self.assertEqual(version["vers"], "1.0.0")
        self.assertEqual([(d.name, d.kind, d.optional) for d in deps],
                         [("serde", "normal", True), ("cc", "build", False)])
        self.assertEqual(self.fetch.urls[0], REPO + "/config.json")

    def test_old_version_without_dependencies(self):
        """У версии может не быть зависимостей."""
        _, deps = remote_dependencies(REPO, "demo", "0.9.0", self.fetch)
        self.assertEqual(deps, [])

    def test_missing_package(self):
        """Отсутствующий пакет — ошибка «не найден»."""
        with self.assertRaisesRegex(DataError, "не найден"):
            remote_dependencies(REPO, "nope", "latest", self.fetch)

    def test_broken_dependencies(self):
        """Зависимость без имени — ошибка формата."""
        self.fetch.files[REPO + "/de/mo/demo"] = index_text(
            entry("1.0.0", [{"req": "^1"}]))
        with self.assertRaisesRegex(DataError, "неверный формат"):
            remote_dependencies(REPO, "demo", "latest", self.fetch)


class CheckIndexTest(unittest.TestCase):
    """Проверка того, что по URL находится индекс Cargo."""

    def test_valid(self):
        """config.json с полем dl — это индекс."""
        check_index(REPO, FakeRepo({REPO + "/config.json": CONFIG}))

    def test_invalid(self):
        """Нет config.json, не JSON, нет поля dl — не индекс."""
        for files in ({}, {REPO + "/config.json": "<html>"},
                      {REPO + "/config.json": '{"api": "x"}'}):
            with self.subTest(files=files):
                with self.assertRaisesRegex(DataError, "нет индекса"):
                    check_index(REPO, FakeRepo(files))

    def test_connection_error_is_kept(self):
        """Ошибка соединения сообщается как есть."""
        def fail(url):
            """Имитировать недоступный сервер."""
            raise ConnectionFailed("не удалось подключиться")
        with self.assertRaisesRegex(DataError, "не удалось подключиться"):
            check_index(REPO, fail)


class Handler(http.server.BaseHTTPRequestHandler):
    """Локальный HTTP-сервер для проверки fetch_text."""

    def do_GET(self):  # noqa: N802 (имя задано http.server)
        """Ответить в зависимости от пути запроса."""
        codes = {"/ok": HTTPStatus.OK, "/missing": HTTPStatus.NOT_FOUND,
                 "/broken": HTTPStatus.INTERNAL_SERVER_ERROR}
        code = codes.get(self.path, HTTPStatus.NOT_FOUND)
        body = "привет" if code == HTTPStatus.OK else ""
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        """Не печатать журнал запросов."""


class FetchTextTest(unittest.TestCase):
    """Проверка загрузки по HTTP на локальном сервере."""

    @classmethod
    def setUpClass(cls):
        """Запустить локальный сервер в отдельном потоке."""
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)
        threading.Thread(target=cls.server.serve_forever,
                         daemon=True).start()
        cls.env = mock.patch.dict(os.environ, {"no_proxy": "127.0.0.1",
                                               "NO_PROXY": "127.0.0.1"})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        """Остановить сервер."""
        cls.env.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def test_ok(self):
        """Ответ 200 возвращается как текст UTF-8."""
        self.assertEqual(fetch_text(self.base + "/ok"), "привет")

    def test_not_found(self):
        """404 — пакет не найден."""
        with self.assertRaisesRegex(DataError, "не найден"):
            fetch_text(self.base + "/missing")

    def test_server_error(self):
        """Другие коды HTTP сообщаются с номером."""
        with self.assertRaisesRegex(DataError, "HTTP 500"):
            fetch_text(self.base + "/broken")

    def test_connection_refused(self):
        """Закрытый порт — ошибка подключения."""
        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_port
        server.server_close()
        with self.assertRaises(ConnectionFailed):
            fetch_text("http://127.0.0.1:" + str(port) + "/ok")


if __name__ == "__main__":
    unittest.main()
