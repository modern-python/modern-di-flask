import typing

import flask
import pytest
from flask import Flask, g
from modern_di import Container, Group, Scope, exceptions, providers

import modern_di_flask
from modern_di_flask import FromDI, fetch_di_container, inject, setup_di
from tests.dependencies import SimpleCreator


def test_fetch_returns_the_same_container(app: Flask, container: Container) -> None:
    setup_di(app, container)
    assert fetch_di_container(app) is container


def test_setup_di_returns_the_container(app: Flask, container: Container) -> None:
    assert modern_di_flask.setup_di(app, container) is container


def test_request_builds_and_closes_child(app: Flask) -> None:
    teardowns: list[str] = []

    class Deps(Group):
        resource = providers.Factory(
            scope=Scope.REQUEST,
            creator=SimpleCreator,
            kwargs={"dep1": "x"},
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda _: teardowns.append("closed")),
        )

    @app.route("/touch")
    def touch() -> dict[str, typing.Any]:
        # the before_request middleware put the REQUEST child on g
        child = g.modern_di_request_container
        instance = child.resolve_dependency(Deps.resource)
        return {"ok": isinstance(instance, SimpleCreator)}

    with Container(groups=[Deps], validate=True) as root:
        setup_di(app, root)
        with app.test_client() as client:
            assert client.get("/touch").json == {"ok": True}
    assert teardowns == ["closed"]  # teardown_appcontext closed the child


def test_teardown_outside_request_is_noop(app: Flask, container: Container) -> None:
    setup_di(app, container)
    # an app context with no request never sets the child on g; teardown must no-op
    with app.app_context():
        pass  # popping the context fires teardown_appcontext with no child


def test_child_closed_when_view_raises(app: Flask) -> None:
    teardowns: list[str] = []

    class Deps(Group):
        resource = providers.Factory(
            scope=Scope.REQUEST,
            creator=SimpleCreator,
            kwargs={"dep1": "x"},
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda _: teardowns.append("closed")),
        )

    @app.route("/boom")
    def boom() -> str:
        g.modern_di_request_container.resolve_dependency(Deps.resource)
        msg = "kaboom"
        raise RuntimeError(msg)

    with Container(groups=[Deps], validate=True) as root:
        setup_di(app, root)
        with app.test_client() as client, pytest.raises(RuntimeError, match="kaboom"):
            client.get("/boom")
    assert teardowns == ["closed"]  # teardown always runs, incl. the error path


def _needs_request(request: flask.Request) -> str:
    # non-optional, no default — validate=True only succeeds once
    # flask_request_provider is registered, i.e. after setup_di has run
    return request.method


class _HardRequestDeps(Group):
    req_method = providers.Factory(scope=Scope.REQUEST, creator=_needs_request)


def test_setup_di_then_open_resolves_hard_request_dependency(app: Flask) -> None:
    # correct order: setup_di registers flask_request_provider, THEN open()
    # runs validate=True — the reverse order is the documented defect this
    # test guards against
    root = Container(groups=[_HardRequestDeps], validate=True)
    setup_di(app, root)
    root.open()

    @app.route("/method")
    @inject
    def method_view(req_method: typing.Annotated[str, FromDI(_HardRequestDeps.req_method)]) -> dict[str, str]:
        return {"method": req_method}

    try:
        with app.test_client() as client:
            assert client.get("/method").json == {"method": "GET"}
    finally:
        root.close_sync()


def test_open_before_setup_di_fails_validation_for_hard_request_dependency() -> None:
    # documents the contract: opening before setup_di runs validate=True
    # before flask_request_provider exists, so a non-optional flask.Request
    # dependency cannot be resolved
    root = Container(groups=[_HardRequestDeps], validate=True)
    with pytest.raises(exceptions.ValidationFailedError):
        root.open()
