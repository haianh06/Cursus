from src.services.auth.mfa_service import generate_totp


def test_generate_totp_matches_rfc_6238_sha1_vector():
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

    assert generate_totp(secret, counter=1, digits=8) == "94287082"
    assert generate_totp(secret, counter=37037036, digits=8) == "07081804"
    assert generate_totp(secret, counter=41152263, digits=8) == "89005924"
