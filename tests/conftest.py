import typing

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
def container() -> typing.Iterator[Container]:
    # caller owns opening the root container under modern-di 3.x's mandatory-open lifecycle
    with Container(groups=[Dependencies], validate=True) as container_:
        yield container_
