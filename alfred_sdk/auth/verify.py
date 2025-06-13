import functools
import json
import os

import jwt
import requests

_JWKS_CACHE = None
def _get_jwks():
    global _JWKS_CACHE
    if _JWKS_CACHE is None:
        _JWKS_CACHE = requests.get(os.getenv("JWKS_URL", "http://keycloak:8080/jwks.json")).json()
    return {k["kid"]: k for k in _JWKS_CACHE["keys"]}

def verify(token: str):
    kid = jwt.get_unverified_header(token)["kid"]
    key = _get_jwks()[kid]
    return jwt.decode(
        token,
        jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key)),
        algorithms=["RS256"],
        audience=None,
    )
