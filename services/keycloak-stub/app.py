import json
import pathlib

from fastapi import FastAPI, Response, status

app = FastAPI()
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/jwks.json")
def jwks():
    return Response(pathlib.Path("security/jwks.json").read_text(), media_type="application/json")
