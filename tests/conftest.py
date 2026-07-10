import pytest
from flask import Flask
from modern_di import Container

from tests.dependencies import Dependencies


@pytest.fixture
def app() -> Flask:
    app_ = Flask("test")
    app_.config["TESTING"] = True  # views' exceptions propagate to the test client
    return app_


@pytest.fixture
def container() -> Container:
    return Container(groups=[Dependencies], validate=True)
