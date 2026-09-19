# The caller owns the root container's lifecycle

`setup_di` registers providers and hooks on the root container it is handed and never opens,
validates, or closes it. The ASGI integrations do take that over by wrapping the root container in
the framework's lifespan, but Flask (WSGI) has no application startup or shutdown hook to attach
the closing half to: `teardown_appcontext` fires on every app-context pop, including ones no
request created, so it cannot stand in for shutdown. An integration owning only the opening half
would acquire `Scope.APP` resources it has no hook to finalize and hide from the caller that
finalization never happens, which is worse than an honest split; Dishka's Flask integration closes
the per-request child only. The price is two caller-written lines:
`fetch_di_container(app).close_sync()` at the application's own shutdown point, and, since
modern-di validates nowhere implicitly, `container.validate()` after `setup_di`, which is what
registers `flask_request_provider`. Flask growing an application lifecycle hook would reopen this.
