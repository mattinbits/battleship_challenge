from battleship_challenge.main import hello_world


def test_hello_world():
    """Test the hello_world function."""
    result = hello_world()
    assert result == "Hello, World!"
    assert isinstance(result, str)