import typing

import flask
import pytest
from flask import Flask, Response, g, stream_with_context
from modern_di import Container, Group, Scope, exceptions, providers

from modern_di_flask import FromDI, inject, setup_di


class Session:
    pass


def _make_group(events: list[str]) -> type[Group]:
    class Deps(Group):
        session = providers.Factory(
            Session,
            scope=Scope.REQUEST,
            cache=providers.CacheSettings(finalizer=lambda _: events.append("finalized")),
        )

    return Deps


@inject
def _use(session: typing.Annotated[Session, FromDI(Session)]) -> Session:
    return session


def test_before_request_registered_before_setup_di_shares_the_request_container(app: Flask) -> None:
    events: list[str] = []
    seen: list[Session] = []

    @app.before_request
    def early() -> None:
        seen.append(_use())

    @app.route("/")
    def index() -> str:
        seen.append(_use())
        return "ok"

    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        assert app.test_client().get("/").text == "ok"
    assert len(seen) == 2  # noqa: PLR2004
    assert seen[0] is seen[1]
    assert events == ["finalized"]


@pytest.mark.parametrize("order", ["before", "after"])
def test_teardown_appcontext_handler_runs_before_the_close(app: Flask, order: str) -> None:
    events: list[str] = []

    def teardown(_exception: BaseException | None) -> None:
        _use()
        events.append("teardown")

    app.add_url_rule("/", "index", lambda: (_use(), "ok")[1])
    with Container(groups=[_make_group(events)]) as root:
        if order == "before":
            app.teardown_appcontext(teardown)
        setup_di(app, root)
        if order == "after":
            app.teardown_appcontext(teardown)
        assert app.test_client().get("/").text == "ok"
    assert events == ["teardown", "finalized"]


def test_teardown_request_after_short_circuit_builds_the_request_container(app: Flask) -> None:
    events: list[str] = []

    @app.before_request
    def short_circuit() -> str:
        return "short"

    @app.teardown_request
    def teardown(_exception: BaseException | None) -> None:
        _use()
        events.append("teardown")

    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        assert app.test_client().get("/").text == "short"
    assert events == ["teardown", "finalized"]


def test_teardown_does_not_build_a_request_container(app: Flask, container: Container) -> None:
    built: list[bool] = []

    @app.before_request
    def short_circuit() -> str:
        return "short"

    def record(_sender: Flask, **_kwargs: object) -> None:
        built.append(hasattr(g, "modern_di_request_container"))

    setup_di(app, container)
    with flask.appcontext_tearing_down.connected_to(record, app):
        assert app.test_client().get("/").text == "short"
    assert built == [False]


def test_request_container_is_not_rebuilt_after_close(app: Flask) -> None:
    events: list[str] = []
    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        with app.test_request_context("/"):
            _use()
            app.do_teardown_appcontext()
            with pytest.raises(exceptions.ContainerClosedError):
                _use()
    assert events == ["finalized"]


def test_streamed_response_keeps_the_request_container_until_the_response_closes(app: Flask) -> None:
    events: list[str] = []

    @app.route("/")
    def index() -> Response:
        session = _use()

        def generate() -> typing.Iterator[str]:
            yield "a"
            events.append("same" if _use() is session else "rebuilt")

        return Response(stream_with_context(generate()))

    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        response = app.test_client().get("/")
        assert response.text == "a"
        assert events == ["same"]
        response.close()
    assert events == ["same", "finalized"]


def test_plain_generator_response_keeps_resolved_dependencies_live(app: Flask) -> None:
    events: list[str] = []

    @app.route("/")
    def index() -> Response:
        _use()

        def generate() -> typing.Iterator[str]:
            yield "a"
            events.append("streamed")

        return Response(generate())

    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        response = app.test_client().get("/")
        assert response.text == "a"
        assert events == ["streamed"]
        response.close()
    assert events == ["streamed", "finalized"]


def test_direct_passthrough_response_closes_at_teardown(app: Flask) -> None:
    events: list[str] = []

    @app.route("/")
    def index() -> Response:
        _use()
        return Response(iter([b"a"]), direct_passthrough=True)

    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        app.test_client().get("/")
    assert events == ["finalized"]


def test_requests_in_one_app_context_get_separate_request_containers(app: Flask) -> None:
    events: list[str] = []
    seen: list[Session] = []

    @app.before_request
    def early() -> None:
        seen.append(_use())

    app.add_url_rule("/", "index", lambda: "ok")
    with Container(groups=[_make_group(events)]) as root:
        setup_di(app, root)
        with app.app_context():
            client = app.test_client()
            client.get("/")
            client.get("/")
    assert len(seen) == 2  # noqa: PLR2004
    assert seen[0] is not seen[1]


def test_setup_di_twice_registers_one_close_first(app: Flask, container: Container) -> None:
    earlier = app.teardown_appcontext(lambda _exception: None)
    setup_di(app, container)
    with Container(groups=[_make_group([])]) as other:
        setup_di(app, other)
    close = app.teardown_appcontext_funcs[0]
    assert app.teardown_appcontext_funcs == [close, earlier]


def test_apps_resolve_from_their_own_containers() -> None:
    first_events: list[str] = []
    second_events: list[str] = []
    first, second = Flask("first"), Flask("second")
    for each in (first, second):
        each.add_url_rule("/", "index", lambda: (_use(), "ok")[1])
    with (
        Container(groups=[_make_group(first_events)]) as first_root,
        Container(groups=[_make_group(second_events)]) as second_root,
    ):
        setup_di(first, first_root)
        setup_di(second, second_root)
        first.test_client().get("/")
        assert (first_events, second_events) == (["finalized"], [])
        second.test_client().get("/")
        assert (first_events, second_events) == (["finalized"], ["finalized"])


def test_inject_outside_a_request_without_container_raises(app: Flask, container: Container) -> None:
    setup_di(app, container)
    with app.app_context(), pytest.raises(RuntimeError, match=r"setup_di\(app, container\)"):
        _use()
