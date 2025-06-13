from fastapi import FastAPI, HTTPException, Request

from alfred_sdk.auth.verify import verify

app = FastAPI()
@app.middleware("http")
async def _auth(req: Request, call_next):
    if req.url.path == "/health":
        return await call_next(req)
    try:
        auth_header = req.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        token = auth_header.split(" ")[-1]
        verify(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    return await call_next(req)

@app.get("/health")
def health():
    return {"status": "ok"}

# TODO: implement core endpoint (e.g., /recommend, /summary, /embed)
