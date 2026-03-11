from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI()

# allow your frontend to talk to localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3000/experiments",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.post("/run-experiment")
async def run_experiment(
    mode: str = Form(...),
    levels: int = Form(...),
    costStructure: str = Form(...),
    marginalStructure: str = Form(...),
    datasetConfig: Optional[str] = Form(None),
    datasetFile: Optional[UploadFile] = File(None),
):
    file_info = None

    if datasetFile is not None:
        contents = await datasetFile.read()
        file_info = {
            "filename": datasetFile.filename,
            "content_type": datasetFile.content_type,
            "size_bytes": len(contents),
        }

    return {
        "message": "Request received successfully",
        "received": {
            "mode": mode,
            "levels": levels,
            "costStructure": costStructure,
            "marginalStructure": marginalStructure,
            "datasetConfig": datasetConfig,
            "datasetFile": file_info,
        },
        "experimentId": "test-experiment-123",
    }