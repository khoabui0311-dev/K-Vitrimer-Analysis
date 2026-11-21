"""Start the local-only VitriFit 2.0 browser service (after building the UI)."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("vitrifit2.api:app", host="127.0.0.1", port=8000, reload=False)
