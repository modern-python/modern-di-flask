import functools
import inspect
import typing

import flask
from flask import Flask, Request, Response, g
from modern_di import Container, Scope, integrations, providers


flask_request_provider = providers.ContextProvider(Request, scope=Scope.REQUEST)
_CONNECTION_PROVIDERS = (flask_request_provider,)

# Root container on ``app.extensions``; per-request child on ``flask.g``. Named
# constants keep each writer and reader in provable agreement.
_ROOT_CONTAINER_KEY = "modern_di_container"
_CHILD_CONTAINER_ATTR = "modern_di_request_container"
_CHILD_REQUEST_ATTR = "modern_di_request"
_DEFERRED_CHILD_ATTR = "modern_di_deferred_request_container"
_NO_CHILD_CONTAINER_MSG = (
    "No modern-di container found for this request. Call setup_di(app, container) "
    "so requests pass through the modern-di request hooks before using @inject."
)


def fetch_di_container(app: Flask) -> Container:
    return typing.cast(Container, app.extensions[_ROOT_CONTAINER_KEY])


def _fetch_child_container() -> Container:
    if flask.has_request_context():
        return _request_child_container()
    try:
        return typing.cast(Container, getattr(g, _CHILD_CONTAINER_ATTR))
    except AttributeError:
        raise RuntimeError(_NO_CHILD_CONTAINER_MSG) from None


def _request_child_container() -> Container:
    connection = flask.request._get_current_object()  # noqa: SLF001  # ty: ignore[unresolved-attribute]
    if getattr(g, _CHILD_REQUEST_ATTR, None) is connection:
        return typing.cast(Container, getattr(g, _CHILD_CONTAINER_ATTR))
    try:
        container = fetch_di_container(flask.current_app)
    except KeyError:
        raise RuntimeError(_NO_CHILD_CONTAINER_MSG) from None
    match = integrations.bind(flask_request_provider, connection)
    child = container.build_child_container(scope=match.scope, context=match.context)
    setattr(g, _CHILD_CONTAINER_ATTR, child)
    setattr(g, _CHILD_REQUEST_ATTR, connection)
    return child


def _enter_request() -> None:
    _request_child_container()


def _defer_close_to_response(_sender: Flask, response: Response, **_extra: typing.Any) -> None:  # noqa: ANN401
    child: Container | None = getattr(g, _CHILD_CONTAINER_ATTR, None)
    if child is None or not response.is_streamed or response.direct_passthrough:
        child = None
    else:
        response.call_on_close(child.close_sync)
    setattr(g, _DEFERRED_CHILD_ATTR, child)


def _close_request(_exception: BaseException | None) -> None:
    child: Container | None = getattr(g, _CHILD_CONTAINER_ATTR, None)
    if child is not None and child is not getattr(g, _DEFERRED_CHILD_ATTR, None):
        child.close_sync()


def setup_di(app: Flask, container: Container, *, auto_inject: bool = False) -> Container:
    app.extensions[_ROOT_CONTAINER_KEY] = container
    container.add_providers(*_CONNECTION_PROVIDERS)

    app.before_request(_enter_request)
    app.teardown_appcontext(_close_request)
    # Flask runs these in reverse, so putting the close first makes it run last.
    funcs = app.teardown_appcontext_funcs
    funcs[:] = [_close_request, *(func for func in funcs if func is not _close_request)]
    flask.request_finished.connect(_defer_close_to_response, app)
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

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:  # noqa: ANN401
            resolved = integrations.resolve_markers(_fetch_child_container(), markers)
            return await func(*args, **kwargs, **resolved)

        integrations.mark_injected(async_wrapper)
        return typing.cast(typing.Callable[..., T], async_wrapper)

    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> T:  # noqa: ANN401
        resolved = integrations.resolve_markers(_fetch_child_container(), markers)
        return func(*args, **kwargs, **resolved)

    integrations.mark_injected(wrapper)
    return wrapper
