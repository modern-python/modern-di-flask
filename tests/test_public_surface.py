import types

import modern_di_flask


def test_public_surface_is_exactly_the_five_documented_symbols() -> None:
    """INVARIANT: the package exports exactly the five symbols the README's API table lists.

    Broken by promoting a helper to a public name, in ``__all__`` or as an unprefixed binding in
    ``__init__`` -- the latter is public whether or not it was meant to be. The surface is an
    adapter's whole semver contract: every name here is one a major release has to keep working,
    and this is the only place that cost is visible before it is paid. Flask has no DI system of
    its own, so the standing pressure is to answer each gap with one more convenience exported
    from here rather than with a provider or a fix upstream in modern-di.
    """
    public = sorted(
        name
        for name, value in vars(modern_di_flask).items()
        if not name.startswith("_") and not isinstance(value, types.ModuleType)
    )

    assert public == ["FromDI", "fetch_di_container", "flask_request_provider", "inject", "setup_di"]
    assert modern_di_flask.__all__ == public
