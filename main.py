import os
import uuid
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from video_engine import VideoEngine

app = FastAPI(title="Chess2Video Server")

# Ensure output directory exists
os.makedirs("./output", exist_ok=True)

# Mount static files
app.mount("/static/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/output", StaticFiles(directory="output"), name="output")

# Video Engine instance
ve = VideoEngine()

# Global state to keep track of tasks
# task_id -> {"status": "pending"|"processing"|"completed"|"failed", "progress": int, "message": str, "video_url": str|None}
tasks_status = {}
# task_id -> list of WebSockets
ws_clients = {}

class GenerateRequest(BaseModel):
    pgn: str
    board_theme: str = "green"
    piece_theme: str = "cburnett"
    aspect_ratio: str = "16:9"
    hold_duration: float = 0.8
    volume: float = 1.0

def video_generation_worker(task_id: str, req: GenerateRequest):
    """Background worker to compile the video and update WebSocket clients"""
    tasks_status[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Initializing video generation task...",
        "video_url": None
    }
    
    # Define a helper progress callback
    def progress_callback(message, percent):
        tasks_status[task_id]["progress"] = percent
        tasks_status[task_id]["message"] = message
        # Trigger sending update
        # (WebSocket readers will poll or be notified via task_status changes)

    output_filename = f"{task_id}.mp4"
    output_path = os.path.join("./output", output_filename)

    try:
        ve.generate_chess_video(
            pgn_text=req.pgn,
            output_path=output_path,
            board_theme=req.board_theme,
            piece_theme=req.piece_theme,
            aspect_ratio=req.aspect_ratio,
            hold_duration=req.hold_duration,
            volume=req.volume,
            progress_callback=progress_callback
        )
        
        # Complete
        tasks_status[task_id]["status"] = "completed"
        tasks_status[task_id]["progress"] = 100
        tasks_status[task_id]["message"] = "Chess video compiled successfully!"
        tasks_status[task_id]["video_url"] = f"/output/{output_filename}"
        
    except Exception as e:
        tasks_status[task_id]["status"] = "failed"
        tasks_status[task_id]["progress"] = 0
        tasks_status[task_id]["message"] = f"Video compilation failed: {str(e)}"
        print(f"Error compiling video {task_id}: {e}")

@app.post("/api/generate")
async def generate_video(req: GenerateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Enqueuing video job...",
        "video_url": None
    }
    
    # Start thread
    t = threading.Thread(target=video_generation_worker, args=(task_id, req))
    t.daemon = True
    t.start()
    
    return {"task_id": task_id}

@app.websocket("/ws/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    
    if task_id not in tasks_status:
        await websocket.send_json({
            "status": "failed",
            "progress": 0,
            "message": "Task ID not found."
        })
        await websocket.close()
        return

    last_progress = -1
    last_message = ""
    last_status = ""

    try:
        while True:
            status_data = tasks_status.get(task_id)
            if not status_data:
                break
                
            # Only send if there are changes to avoid overwhelming client
            if (status_data["progress"] != last_progress or 
                status_data["message"] != last_message or 
                status_data["status"] != last_status):
                
                await websocket.send_json({
                    "status": status_data["status"],
                    "progress": status_data["progress"],
                    "message": status_data["message"],
                    "video_url": status_data["video_url"]
                })
                
                last_progress = status_data["progress"]
                last_message = status_data["message"]
                last_status = status_data["status"]

            if status_data["status"] in ["completed", "failed"]:
                break
                
            # Wait a short duration before checking again
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.get("/")
async def get_index():
    index_path = os.path.join("./templates", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend index file not found.")
        
    with open(index_path, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    # Bind to loopback interface on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
