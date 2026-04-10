import uvicorn
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).parent.parent))

if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
    