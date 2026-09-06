# modern-di-flask

A Flask adapter over [`modern-di`](https://github.com/modern-python/modern-di): it hangs a
container on a Flask app, builds a `Scope.REQUEST` child container per request, and resolves a
view's `FromDI`-marked parameters from that child.

## Language

A term is listed only when there is a synonym to reject, or a meaning subtle enough that code and
docs must agree on it. General programming vocabulary does not belong here, however heavily this
package uses it.

The domain terms are `modern-di`'s — `Container`, `Provider`, `Group`, `Scope`, `Resolution`,
`Override`. That project's `CONTEXT.md` is the authority for all of them; nothing here redefines
one. One of its entries needs a local reading: `Connection` deliberately rejects _request_ as too
HTTP-specific, because a connection is whatever object a unit of work carries. Flask carries
exactly one kind and it is literally `flask.Request`, so **request** is the right word for it in
this repo; `connection` survives only in `_CONNECTION_PROVIDERS` and when speaking about the
upstream contract. The three terms below are this package's own.

**Root container**:
The `Container` the caller constructs and hands to `setup_di`, stored on `app.extensions` and read
back by `fetch_di_container`. "Root" is its position in modern-di's scope hierarchy — it is at
`Scope.APP` — and says nothing about the Flask `app` it is attached to. This package never
constructs, validates, or closes it.
_Avoid_: app container — reads as Flask's app object, and its lifetime is the process, not any
Flask app context.

**Child container**:
The `Scope.REQUEST` container `before_request` builds per request and stashes on `flask.g`;
`inject` resolves from it and `teardown_appcontext` closes it. Its lifetime is bounded by Flask's
**app context**, not by Flask's request context: an app context pushed without a request (a CLI
command, a bare `app.app_context()`) fires the same teardown with no child ever built, which is
why the close is guarded.
_Avoid_: request context — Flask's own object, which this is not; request scope — `Scope.REQUEST`
is the child's scope, not the child.

**View**:
The function Flask dispatches for a route, and the thing `inject` decorates and `auto_inject`
wraps. Its **endpoint** (the key under which `app.view_functions` holds it) and its **route** (the
URL rule) are different things, not looser names for it.
_Avoid_: handler — modern-di's generic word for the callable a resolved value is passed into; in
Flask that callable is a view.
