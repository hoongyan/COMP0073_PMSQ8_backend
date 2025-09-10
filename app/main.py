import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.route import router
from app.routers.auth import auth_router


app = FastAPI(title="Persona Based Conversational AI Agent")

    
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],  # update FRONTEND_URL to match Next.js app
    allow_credentials=True,
    allow_methods=["*"],  # Allow POST
    allow_headers=["*"],  # Allow Content-Type
)

#Include routers 
app.include_router(router)
app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)