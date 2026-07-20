# Dependency injection

The capability this package exists for: wiring a `modern-di` `Container` into
a Flask `app` so view parameters resolve from it, scoped per request.
Everything lives in `modern_di_flask/main.py`; the public surface is
`setup_di`, `fetch_di_container`, `FromDI`, and `inject`.

## Setup

`setup_di(app, container, *, auto_inject=False)` is the single entry point. It:

1. Stores the container on `app.extensions` under `_ROOT_CONTAINER_KEY`
   (`"modern_di_container"`), a named constant — writer (`setup_di`) and
   reader (`fetch_di_container`) stay in provable agreement instead of
   relying on a bare string literal.
2. Registers `flask_request_provider`, a `ContextProvider(Request,
   scope=Scope.REQUEST)`, on the container via `add_providers`. It is the
   package's one connection provider — `flask.Request` — there is no
   WebSocket counterpart because Flask's core has none.
3. Wires `app.before_request(_enter_request)` and
   `app.teardown_appcontext(_close_request)` to open and close a per-request
   child container (see below).
4. If `auto_inject=True`, calls `_inject_views(app)` to wrap every currently
   registered view.

`fetch_di_container(app)` reads the same key back off `app.extensions` and
returns the root container.

## No root lifecycle wiring

Unlike Celery's worker-process signals or an ASGI app's lifespan events,
Flask has no application startup/shutdown hook that `setup_di` could attach
to. `setup_di` does not open the root container — under modern-di 3.x's
mandatory-open lifecycle, a freshly-constructed container starts unopened, so
the caller must call `.open()` (or enter it with `with`) before passing it to
`setup_di` and serving traffic; passing an unopened container means the very
first request's `before_request` hook raises `ContainerClosedError` when it
tries to build the per-request child. The root container then lives for the
entire process lifetime of the app. Closing it, and finalizing any
`APP`-scoped providers, is likewise the caller's own responsibility: call
`fetch_di_container(app).close_sync()` at whatever point the application
actually shuts down (e.g. a CLI teardown step, a WSGI server's exit hook, or
an `atexit` callback the caller registers themselves). `modern-di-flask` does
not open or close the root container automatically.

## Per-request scope

`_enter_request`, connected to `before_request`, runs once per incoming
request. It unwraps Flask's request-local proxy to the real `Request` object,
then derives the child's scope and context via
`modern_di.integrations.bind(flask_request_provider, connection)` —
`bind(provider, connection)` returns a `ConnectionMatch(scope=provider.scope,
context={provider.context_type: connection})`, so this always produces
`scope=Scope.REQUEST, context={Request: connection}`, the same values the
code used to hand-write. Flask has no WebSocket counterpart, so there is only
ever one provider to derive from — `classify_connection` (which dispatches
across several providers) has nothing to dispatch across here.
`container.build_child_container(scope=match.scope, context=match.context)`
builds the child; `_enter_request` opens it immediately with `child.open()` —
required under modern-di 3.x's mandatory-open lifecycle, since building and
closing the child happen in two separate hooks (`before_request` /
`teardown_appcontext`) with no enclosing `with` block to open it implicitly.
The opened child is then stashed on `flask.g` under `_CHILD_CONTAINER_ATTR`
(`"modern_di_request_container"`).

`_close_request`, connected to `teardown_appcontext`, reads the child back off
`g` with `getattr(g, _CHILD_CONTAINER_ATTR, None)` and calls `close_sync()` on
it if present. The `getattr` default guards against app contexts that never
went through `before_request` — for example a bare `app.app_context()` opened
outside a request (CLI commands, shell sessions) — where teardown still fires
but no child container was ever built; in that case `_close_request` is a
no-op instead of raising.

## Resolution

`FromDI` is `modern_di.integrations.from_di` — its marker factory. Calling
`FromDI(dependency)` returns an inert `Marker(dependency)` wrapping a
provider or a bare type; it does nothing on its own. Parameters opt into
injection by annotating them `typing.Annotated[SomeType, FromDI(dependency)]`.

`inject`:

1. `integrations.parse_markers(func)` scans the resolved type hints
   (`typing.get_type_hints(func, include_extras=True)`) for `Annotated`
   parameters carrying a `Marker`.
2. If none are found, the function is returned unchanged — only marked via
   `integrations.mark_injected(func)` — and `inject` short-circuits without
   building a wrapper at all.
3. Otherwise `inject` builds a `wrapper`, decorated with `functools.wraps`,
   that reads the current request's child container off `flask.g`
   (`getattr(g, _CHILD_CONTAINER_ATTR)`), resolves every marker via
   `integrations.resolve_markers(child, markers)` — which calls each
   `Marker.resolve(container)`, itself `container.resolve_dependency(...)`,
   dispatching to `resolve_provider` when `dependency` is a provider instance
   and to `resolve` (by type) otherwise — and calls the original function
   with the resolved dependencies merged into the caller's `args`/`kwargs`.

Unlike the aiogram and Celery integrations, `inject` performs **no signature
rewrite**. Flask's URL dispatcher calls a view as `view(**url_args)` — it
never inspects the view's signature to decide what to pass, so there is
nothing that would trip over a signature that still lists the DI parameters.
`functools.wraps` is enough to preserve `__name__`/`__doc__`/etc. for
introspection and Flask's endpoint-naming.

## auto_inject

With `auto_inject=True`, `setup_di` calls `_inject_views(app)`, which iterates
`app.view_functions` and wraps every entry `integrations.is_injected` doesn't
already report as marked with `inject`. Flask registers **every** dispatched
view — both app-level routes and blueprint routes (the latter under dotted
endpoints like `"bp.view"`) — in that single `app.view_functions` mapping, and
always dispatches through it, so wrapping that one registry covers app and
blueprint views alike. There is no separate blueprint-iteration step.

Because `_inject_views` only sees views present in `app.view_functions` at the
moment it runs, all routes — including blueprint routes registered via
`app.register_blueprint` — must be registered **before** calling
`setup_di(app, container, auto_inject=True)`. Routes registered afterward are
not wrapped and will not have their `FromDI` parameters resolved.

## Synchronous only

Every lifecycle and resolution step here is synchronous: the per-request
child container is closed with `close_sync()`, and there is no async
counterpart anywhere in this integration, matching Flask's own WSGI,
synchronous request-handling model. The package requires `flask>=3,<4` — the
floor was raised from 2 because Flask 2.x is broken under modern Werkzeug
releases.
