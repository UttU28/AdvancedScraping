from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import subprocess
import threading
import time

app = FastAPI()

# Enable CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def hello():
    return "hello dunitya"

@app.post("/api/endpoint")
async def api_endpoint(request: Request):
    # Get the JSON data sent in the POST request
    data = await request.json()
    
    if 'url' in data:
        url = data['url']
        print(f'Received URL: {url}')
        
        response = {
            'message': f'Data received from URL: {url}',
            'success': True
        }
        return JSONResponse(content=response, status_code=200)
    else:
        return JSONResponse(content={'error': 'No URL provided'}, status_code=400)

def start_ngrok():
    time.sleep(2)  # Wait for FastAPI server to start
    subprocess.run(['ngrok', 'http', '--domain=optimum-titmouse-willingly.ngrok-free.app', '3000'])

if __name__ == '__main__':
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok, daemon=True)
    ngrok_thread.start()
    
    # Start FastAPI server using uvicorn
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=3000)
