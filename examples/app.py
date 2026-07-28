# Minimal modern-di + flask example.
# Run for real:  flask --app examples.app run
import dataclasses
import typing

from flask import Flask
from modern_di import Container, Group, Scope, providers

from modern_di_flask import FromDI, inject, setup_di


@dataclasses.dataclass(kw_only=True)
class Settings:
    greeting: str = "Hello"


@dataclasses.dataclass(kw_only=True)
class GreetingService:
    settings: Settings  # auto-injected by type

    def greet(self, name: str) -> str:
        return f"{self.settings.greeting}, {name}!"


class Dependencies(Group):
    settings = providers.Factory(scope=Scope.APP, creator=Settings)
    service = providers.Factory(scope=Scope.REQUEST, creator=GreetingService)


app = Flask(__name__)


@app.route("/greet/<name>")
@inject
def greet(name: str, service: typing.Annotated[GreetingService, FromDI(Dependencies.service)]) -> str:
    return service.greet(name)


# setup_di AFTER routes are registered; validate() AFTER setup_di, which
# registers the flask_request_provider that validation needs to already exist
container = Container(groups=[Dependencies])
setup_di(app, container)
container.validate()  # optional fail-fast, now that flask_request_provider is registered
