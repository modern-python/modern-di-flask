from examples.app import app


def test_example_resolves_and_greets() -> None:
    with app.test_client() as client:
        assert client.get("/greet/world").data.decode() == "Hello, world!"
