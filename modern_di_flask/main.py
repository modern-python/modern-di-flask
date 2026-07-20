import functools
import typing

import flask
from flask import Flask, Request, g
from modern_di import Container, Scope, integrations, providers


flask_request_provider = providers.ContextProvider(Request, scope=Scope.REQUEST)
_CONNECTION_PROVIDERS = (flask_request_provider,)

# Root container on ``app.extensions``; per-request child on ``flask.g``. Named
# constants keep each writer and reader in provable agreement.
_ROOT_CONTAINER_KEY = "modern_di_container"
_CHILD_CONTAINER_ATTR = "modern_di_request_container"


def fetch_di_container(app: Flask) -> Container:
    return typing.cast(Container, app.extensions[_ROOT_CONTAINER_KEY])


def _close_request(_exception: BaseException | None) -> None:
    child: Container | None = getattr(g, _CHILD_CONTAINER_ATTR, None)
    if child is not None:
        child.close_sync()


def setup_di(app: Flask, container: Container, *, auto_inject: bool = False) -> Container:
    app.extensions[_ROOT_CONTAINER_KEY] = container
    container.add_providers(*_CONNECTION_PROVIDERS)

    def _enter_request() -> None:
        connection = flask.request._get_current_object()  # noqa: SLF001  # ty: ignore[unresolved-attribute]
        match = integrations.bind(flask_request_provider, connection)
        child = container.build_child_container(scope=match.scope, context=match.context)
        child.open()
        setattr(g, _CHILD_CONTAINER_ATTR, child)

    app.before_request(_enter_request)
    app.teardown_appcontext(_close_request)
    if auto_inject:
        _inject_views(app)
    return container


def _inject_views(app: Flask) -> None:
    # Flask registers every dispatched view (app routes and blueprint routes,
    # the latter under dotted endpoints like "bp.view") in ``app.view_functions``
    # and always dispatches through it, so wrapping that one registry covers all.
    for endpoint, view in list(app.view_functions.items()):
        if not integrations.is_injected(view):
            app.view_functions[endpoint] = inject(view)  # ty: ignore[invalid-assignment]


T = typing.TypeVar("T")


FromDI = integrations.from_di


def inject(func: typing.Callable[..., T]) -> typing.Callable[..., T]:
    markers = integrations.parse_markers(func)
    if not markers:
        integrations.mark_injected(func)
        return func

    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> T:  # noqa: ANN401
        child: Container = getattr(g, _CHILD_CONTAINER_ATTR)
        resolved = integrations.resolve_markers(child, markers)
        return func(*args, **kwargs, **resolved)

    integrations.mark_injected(wrapper)
    return wrapper
