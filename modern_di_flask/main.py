import typing

import flask
from flask import Flask, Request, g
from modern_di import Container, Scope, providers


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


def setup_di(app: Flask, container: Container) -> Container:
    app.extensions[_ROOT_CONTAINER_KEY] = container
    container.add_providers(*_CONNECTION_PROVIDERS)

    def _enter_request() -> None:
        child = container.build_child_container(
            scope=Scope.REQUEST,
            context={Request: flask.request._get_current_object()},  # noqa: SLF001  # ty: ignore[unresolved-attribute]
        )
        setattr(g, _CHILD_CONTAINER_ATTR, child)

    app.before_request(_enter_request)
    app.teardown_appcontext(_close_request)
    return container
