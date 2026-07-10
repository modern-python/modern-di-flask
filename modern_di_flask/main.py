import dataclasses
import functools
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


T = typing.TypeVar("T")
T_co = typing.TypeVar("T_co", covariant=True)


@dataclasses.dataclass(slots=True, frozen=True)
class _FromDI(typing.Generic[T_co]):
    dependency: providers.AbstractProvider[T_co] | type[T_co]


def FromDI(dependency: providers.AbstractProvider[T] | type[T], /) -> T:  # noqa: N802
    return typing.cast(T, _FromDI(dependency))


def _parse_inject_params(func: typing.Callable[..., typing.Any]) -> dict[str, _FromDI[typing.Any]]:
    hints = typing.get_type_hints(func, include_extras=True)
    di_params: dict[str, _FromDI[typing.Any]] = {}
    for name, hint in hints.items():
        if name == "return":
            continue
        if typing.get_origin(hint) is typing.Annotated:
            for meta in typing.get_args(hint)[1:]:
                if isinstance(meta, _FromDI):
                    di_params[name] = meta
                    break
    return di_params


def inject(func: typing.Callable[..., T]) -> typing.Callable[..., T]:
    di_params = _parse_inject_params(func)
    if not di_params:
        func.__modern_di_injected__ = True  # ty: ignore[unresolved-attribute]
        return func

    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> T:  # noqa: ANN401
        child: Container = getattr(g, _CHILD_CONTAINER_ATTR)
        resolved = {name: child.resolve_dependency(marker.dependency) for name, marker in di_params.items()}
        return func(*args, **kwargs, **resolved)

    wrapper.__modern_di_injected__ = True  # ty: ignore[unresolved-attribute]
    return wrapper
