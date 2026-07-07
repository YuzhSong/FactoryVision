from fastapi import FastAPI
import uvicorn

from config import Config


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Factory AI Service",
        description="Independent AI service for video stream analysis, face recognition, and behavior detection.",
        version="0.1.0",
    )

    @app.get("/health", tags=["system"])
    def health_check():
        return {
            "service": Config.SERVICE_NAME,
            "status": "ok",
            "stage": "skeleton",
            "docs": "/docs",
        }

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
    )
