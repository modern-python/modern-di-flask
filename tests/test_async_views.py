import inspect
import typing
from http import HTTPStatus

from flask import Flask
from modern_di import Container

from modern_di_flask import FromDI, inject, setup_di
from tests.dependencies import Dependencies, SimpleCreator


def test_inject_async_view_resolves_and_awaits(app: Flask, container: Container) -> None:
    @app.route("/async/<name>")
    @inject
    async def hello(name: str, app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)]) -> dict[str, str]:
        return {"name": name, "dep1": app_instance.dep1}

    assert inspect.iscoroutinefunction(hello)
    setup_di(app, container)
    with app.test_client() as client:
        response = client.get("/async/world")
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "world", "dep1": "original"}


def test_auto_inject_async_view(app: Flask, container: Container) -> None:
    @app.route("/async/<name>")
    async def hello(name: str, app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)]) -> dict[str, str]:
        return {"name": name, "dep1": app_instance.dep1}

    setup_di(app, container, auto_inject=True)
    assert inspect.iscoroutinefunction(app.view_functions["hello"])
    with app.test_client() as client:
        response = client.get("/async/world")
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "world", "dep1": "original"}


def test_async_view_resolves_from_that_requests_child_container(app: Flask, container: Container) -> None:
    @inject
    def sync_resolve(cached: typing.Annotated[SimpleCreator, FromDI(Dependencies.request_cached)]) -> SimpleCreator:
        return cached

    @app.route("/cached")
    @inject
    async def cached_view(
        cached: typing.Annotated[SimpleCreator, FromDI(Dependencies.request_cached)],
    ) -> dict[str, bool]:
        return {"same": cached is sync_resolve()}

    setup_di(app, container)
    with app.test_client() as client:
        assert client.get("/cached").json == {"same": True}
