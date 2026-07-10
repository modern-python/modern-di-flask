import dataclasses

import flask
from modern_di import Group, Scope, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SimpleCreator:
    dep1: str


@dataclasses.dataclass(kw_only=True, slots=True)
class DependentCreator:
    dep1: SimpleCreator


def fetch_request_path(request: flask.Request | None = None) -> str:
    # Optional-with-default so construction-time validate=True treats the request
    # as optional (the provider is only registered by setup_di); the real request
    # still injects at runtime.
    return request.path if request else ""


class Dependencies(Group):
    app_factory = providers.Factory(creator=SimpleCreator, kwargs={"dep1": "original"})
    request_factory = providers.Factory(scope=Scope.REQUEST, creator=DependentCreator, bound_type=None)
    request_path = providers.Factory(scope=Scope.REQUEST, creator=fetch_request_path)
