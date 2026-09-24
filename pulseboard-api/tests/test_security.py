from app.core.security import create_token,token_user,hash_password,verify_password
def test_jwt_round_trip(): assert token_user(create_token(17))==17
def test_password_hash():
 hashed=hash_password("secure demo password")
 assert verify_password("secure demo password",hashed)
 assert not verify_password("wrong",hashed)
