# `inject` does not rewrite the view's signature

**Decision:** the wrapper `inject` returns keeps `*args, **kwargs` and `functools.wraps`; it does
not build a `__signature__` with the `FromDI`-annotated parameters stripped out.

The sibling adapters `modern-di-celery` and `modern-di-aiogram` do exactly that rewrite, so the
obvious move when porting a fix between integrations is to bring it here too. They need it because
their frameworks read the callable's signature to decide what to pass, and would otherwise try to
supply — or reject the call over — a parameter DI owns.

Flask never reads it. Its URL dispatcher calls `app.view_functions[endpoint](**url_args)` with the
arguments taken from the matched URL rule alone. A rewrite would change nothing about dispatch,
while adding a synthetic signature that has to be kept in step with the wrapped function and taking
the real one away from anything that introspects views.

What `functools.wraps` *is* load-bearing for is `__name__`, which Flask turns into the endpoint
name at `@app.route` time — an invariant, recorded as
`test_inject_preserves_the_view_name_flask_derives_endpoints_from` in `tests/test_inject.py`, not
as prose here.

**Revisit trigger:** something in the dispatch path starts reading view signatures — Flask itself
deriving arguments from them, or an extension within the supported `flask>=3,<4` range that wraps
`view_functions` and inspects what it wrapped. The injected parameters then become visible to a
caller that will try to fill them, and the rewrite earns its keep here too.
