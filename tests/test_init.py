from aiohappyeyeballs import create_connection


def test_init():
    assert create_connection is not None
