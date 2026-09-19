# `inject` does not rewrite the view's signature

The wrapper `inject` returns keeps `*args, **kwargs` and `functools.wraps`; it does not build a
`__signature__` with the `FromDI`-annotated parameters stripped out. The sibling adapters
`modern-di-celery` and `modern-di-aiogram` do exactly that rewrite, so porting it here looks like
an obvious fix, but they need it because their frameworks read the callable's signature to decide
what to pass and would otherwise try to supply, or reject the call over, a parameter DI owns.
Flask never reads it: its URL dispatcher calls `app.view_functions[endpoint](**url_args)` with the
arguments taken from the matched URL rule alone, so a rewrite would change nothing about dispatch
while adding a synthetic signature to keep in step with the wrapped function and hiding the real
one from anything that introspects views. `functools.wraps` stays load-bearing for `__name__`,
which Flask turns into the endpoint name at `@app.route` time. Only something in the dispatch path
within the supported `flask>=3,<4` range reading view signatures would earn the rewrite.
