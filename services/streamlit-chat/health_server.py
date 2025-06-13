from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ui-chat"}

@app.get("/")
async def root():
    return {"message": "UI Chat Health Server"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)