<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"  srcset="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-flask/lockup-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-flask/lockup-light.svg">
    <img alt="modern-di-flask" src="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-flask/lockup.png" width="420">
  </picture>
</p>

[![PyPI version](https://img.shields.io/pypi/v/modern-di-flask.svg)](https://pypi.org/project/modern-di-flask/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/modern-di-flask.svg)](https://pypi.org/project/modern-di-flask/)
[![Downloads](https://static.pepy.tech/badge/modern-di-flask/month)](https://pepy.tech/projects/modern-di-flask)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/modern-python/modern-di-flask/actions/workflows/ci.yml)
[![CI](https://github.com/modern-python/modern-di-flask/actions/workflows/ci.yml/badge.svg)](https://github.com/modern-python/modern-di-flask/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/modern-python/modern-di-flask.svg)](https://github.com/modern-python/modern-di-flask/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/modern-di-flask)](https://github.com/modern-python/modern-di-flask/stargazers)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

[Modern-DI](https://github.com/modern-python/modern-di) integration for [Flask](https://flask.palletsprojects.com).

Full guide: [Flask integration docs](https://modern-di.modern-python.org/integrations/flask/)

## Installation

```bash
uv add modern-di-flask      # or: pip install modern-di-flask
```

## Usage

Flask has no dependency-injection system of its own, so `modern-di-flask` pairs an `@inject` decorator with inert `FromDI` markers (there is no `Depends`). `setup_di` installs a `before_request`/`teardown_appcontext` pair that opens a per-request `Scope.REQUEST` child container and closes it once the request finishes. Resolution is sync-only — the child container is closed with `close_sync()`.

```python
import typing

from flask import Flask
from modern_di import Container, Group, Scope, providers
from modern_di_flask import FromDI, inject, setup_di


class Settings:
    def __init__(self) -> None:
        self.greeting = "hello"


class Dependencies(Group):
    settings = providers.Factory(scope=Scope.APP, creator=Settings)


app = Flask(__name__)


@app.route("/hello/<name>")
@inject
def hello(name: str, settings: typing.Annotated[Settings, FromDI(Dependencies.settings)]) -> str:
    return f"{settings.greeting}, {name}"


# open the root container yourself (modern-di 3.x requires it before use), then
# call setup_di AFTER registering routes — required when using auto_inject
container = Container(groups=[Dependencies], validate=True)
container.open()
setup_di(app, container)
```

Pass `auto_inject=True` to `setup_di` to wire every registered view (app and blueprint routes alike) without a per-view `@inject`; because it walks `app.view_functions` at call time, `setup_di` must run after all routes are registered. `flask.Request` is resolvable within DI via the pre-built `flask_request_provider` context provider. Flask has no application-startup/shutdown hook, so the root container's lifecycle is yours to own end-to-end: call `.open()` (or use `with`) before serving — required under modern-di 3.x's mandatory-open lifecycle — and call `fetch_di_container(app).close_sync()` at your process-shutdown point.

## API

| Symbol | Description |
|---|---|
| `setup_di(app, container, *, auto_inject=False)` | Registers the container on `app.extensions`, installs the `before_request`/`teardown_appcontext` pair that builds and closes a per-request `Scope.REQUEST` child, and — if `auto_inject=True` — wraps every currently-registered view with `inject`; returns the container |
| `FromDI(dependency)` | Inert marker (used with `@inject`) that resolves a provider or type from the per-request child container |
| `inject(view)` | Decorator for a view function; resolves its `FromDI`-annotated parameters without rewriting the function's signature |
| `fetch_di_container(app)` | Returns the root `Container` stored on `app.extensions` |
| `flask_request_provider` | `ContextProvider` for `flask.Request` (`REQUEST` scope), auto-registered by type |

## 📦 [PyPI](https://pypi.org/project/modern-di-flask)

## 📝 [License](LICENSE)

## Part of `modern-python`

Built on [`modern-di`](https://github.com/modern-python/modern-di), a dependency-injection framework with IoC container and scopes.

Browse the full list of templates and libraries in
[`modern-python`](https://github.com/modern-python) — see the org profile for the categorized index.
