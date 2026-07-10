import typing

from flask import Flask
from modern_di import Container

from modern_di_flask import FromDI, inject, setup_di
from tests.dependencies import Dependencies, DependentCreator, SimpleCreator


def test_inject_resolves_app_request_and_context(app: Flask, container: Container) -> None:
    @app.route("/hello/<name>")
    @inject
    def hello(
        name: str,
        app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
        request_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.request_factory)],
        request_path: typing.Annotated[str, FromDI(Dependencies.request_path)],
    ) -> dict[str, typing.Any]:
        return {
            "name": name,
            "app_ok": isinstance(app_instance, SimpleCreator),
            "request_ok": isinstance(request_instance, DependentCreator),
            "distinct": request_instance.dep1 is not app_instance,
            "path": request_path,
        }

    setup_di(app, container)
    with app.test_client() as client:
        assert client.get("/hello/world").json == {
            "name": "world",
            "app_ok": True,
            "request_ok": True,
            "distinct": True,
            "path": "/hello/world",
        }


def test_inject_is_noop_without_fromdi(app: Flask, container: Container) -> None:
    @app.route("/plain")
    @inject
    def plain() -> dict[str, str]:
        return {"where": "plain"}

    setup_di(app, container)
    with app.test_client() as client:
        assert client.get("/plain").json == {"where": "plain"}
