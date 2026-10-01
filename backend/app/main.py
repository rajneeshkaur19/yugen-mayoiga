from fastapi import FastAPI

app = FastAPI(
    title="Yūgen Mayoiga",
    description="Interactive, Stateful Narrative Intelligence Platform",
    version="0.1.0",
)

@app.get("/")
def root():
    return{
        "project":"Yūgen Mayoiga",
        "status":"running",
    }

@app.get("/health")
def health_check():
    return{
        "status":"healthy",
    }