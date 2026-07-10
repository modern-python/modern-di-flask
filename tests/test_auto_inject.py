import typing

import flask
from flask import Flask
from modern_di import Container

from modern_di_flask import FromDI, inject, setup_di
from tests.dependencies import SimpleCreator


def test_auto_inject_app_and_blueprint(app: Flask, container: Container) -> None:
    blueprint = flask.Blueprint("bp", __name__)

    @blueprint.route("/bp/<name>")
    def bp_view(name: str, app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)]) -> dict[str, str]:
        return {"where": "blueprint", "name": name, "dep1": app_instance.dep1}

    @app.route("/app/<name>")
    def app_view(name: str, app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)]) -> dict[str, str]:
        return {"where": "app", "name": name, "dep1": app_instance.dep1}

    app.register_blueprint(blueprint)
    setup_di(app, container, auto_inject=True)  # AFTER routes/blueprints are registered

    with app.test_client() as client:
        assert client.get("/app/x").json == {"where": "app", "name": "x", "dep1": "original"}
        assert client.get("/bp/y").json == {"where": "blueprint", "name": "y", "dep1": "original"}


def test_auto_inject_skips_already_injected(app: Flask, container: Container) -> None:
    @app.route("/pre/<name>")
    @inject
    def pre(name: str, app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)]) -> dict[str, str]:
        return {"name": name, "dep1": app_instance.dep1}

    setup_di(app, container, auto_inject=True)  # must not double-wrap the already-injected view
    with app.test_client() as client:
        assert client.get("/pre/z").json == {"name": "z", "dep1": "original"}
