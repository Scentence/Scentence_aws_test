from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scentmap.app.api.network_data import router as network_router

app = FastAPI(title="Scentmap Service")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(network_router)

@app.get("/")
def root():
    return {"message": "Scentmap service is running!"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "scentmap"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scentmap.main:app", host="0.0.0.0", port=8001, reload=True)