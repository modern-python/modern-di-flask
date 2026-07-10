# modern-di-flask

[Modern-DI](https://github.com/modern-python/modern-di) integration for [Flask](https://flask.palletsprojects.com).

## Quickstart

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


# call setup_di AFTER registering routes (required for auto_inject)
setup_di(app, Container(groups=[Dependencies], validate=True))
```

Pass `auto_inject=True` to `setup_di` to inject every view without a per-view
`@inject`. See the [documentation](https://modern-di.modern-python.org).
