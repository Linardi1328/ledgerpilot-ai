from ledgerpilot import __version__


def test_package_import() -> None:
    assert isinstance(__version__, str)
    assert __version__
