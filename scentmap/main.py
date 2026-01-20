from fastapi import FastAPI

app = FastAPI(title="Scentmap Service")

@app.get("/")
def root():
    return {"message": "Scentmap service is running!"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "scentmap"}