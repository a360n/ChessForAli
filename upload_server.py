import os
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Enable CORS so our local file:/// downloader.html can upload files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("wheels", exist_ok=True)

@app.post("/upload")
async def upload(filename: str = Query(...), file: UploadFile = File(...)):
    filepath = os.path.join("wheels", filename)
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    print(f"Successfully uploaded: {filename} ({len(content)} bytes)")
    return {"status": "ok", "filename": filename, "bytes": len(content)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8099)
