from main import app
import uvicorn

def main():
    return app

# THIS is what they are crying about
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
    
