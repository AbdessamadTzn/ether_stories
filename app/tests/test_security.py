from app.core.security import get_password_hash, verify_password

def test_password_hashing():
    password = "secret_ether_story"
    hashed = get_password_hash(password)

    assert hashed != password #Hashed should not be the plain
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_story", hashed) is False