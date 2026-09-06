# The caller owns the root container's lifecycle

**Decision:** `setup_di` registers providers and hooks on the root container it is handed; it does
not open, validate, or close it. Constructing, validating, and closing the root container stay the
caller's, and we will not add an integration-owned lifecycle for it.

The recurring proposal is for `setup_di` to take that over the way the ASGI integrations do —
theirs wrap the root container in the framework's lifespan, entering it on startup and closing it
on shutdown, so a user never writes a teardown line.

Flask (WSGI) has no application startup or shutdown hook to attach the closing half to.
`before_request` and `teardown_appcontext` are per-request-ish, not per-process; in particular
`teardown_appcontext` fires on every app-context pop, including ones no request created, so it
cannot stand in for shutdown. An integration that took ownership here could therefore own only the
opening half: it would acquire `Scope.APP` resources it has no hook to finalize, and would hide
from the caller that finalization never happens — worse than the current split, which at least
tells the truth. Dishka's Flask integration reaches the same conclusion: it closes the per-request
child only, never the root.

The price is two lines the caller writes: `fetch_di_container(app).close_sync()` at whatever
process-shutdown point the application actually has, and — since modern-di 3.1 validates nowhere
implicitly — `container.validate()` if boot-time fail-fast is wanted, after `setup_di` rather than
before it, because `setup_di` is what registers `flask_request_provider`.

**Revisit trigger:** Flask grows an application-lifecycle hook — a startup/shutdown signal, or an
ASGI-style lifespan on the app object — that `setup_di` could attach a close to. Ownership becomes
symmetric at that moment and this should be reopened.
