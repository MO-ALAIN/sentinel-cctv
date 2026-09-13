import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import registry_tools, coverage
from app.security import router as auth_router, access_middleware
from app.services.sighting_repository import sighting_repo
from app.paths import ensure_directories
from app.api import cameras, detections, tracks, anpr, analytics, demo, investigation
from app.services.demo_manager import demo_camera_manager
from app.db.database import init_db
from app.services.stream_manager import stream_manager, StreamCapacityError
from app.services.catalogue import catalogue_service
from app.services.yolo_service import yolo_detector
from app.services.anpr_service import anpr_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CCTV-Backend")

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing CCTV Surveillance Platform Backend...")
    # 1. Initialize DB
    ensure_directories()
    await init_db()
    sighting_repo.stats()
    
    # 2. Log YOLO ByteTrack & ANPR initialization state
    yolo_telemetry = yolo_detector.get_telemetry()
    logger.info("Vehicle model ready=%s; device=%s", yolo_telemetry["ready"], yolo_telemetry["device_name"])
    
    # 3. Warm up camera catalogue
    try:
        cams = await catalogue_service.fetch_catalogue(force_refresh=settings.FETCH_CATALOGUE_ON_START)
        logger.info(f"Loaded {len(cams)} cameras into catalogue cache on startup.")
    except Exception as e:
        logger.warning(f"Catalogue warmup failed: {e}")
        cams = []

    # Restore only network sources explicitly connected by an operator.
    for cam in cams:
        if cam.get('desired_connected') and cam.get('source_type') != 'RECORDED':
            source = await catalogue_service.get_camera_by_id(cam['id'])
            if source and source.get('rtsp_url'):
                try:
                    stream_manager.start_camera(cam['id'],source['rtsp_url'])
                except StreamCapacityError:
                    logger.warning('Camera %s not restored: configured worker limit reached', cam['id'])

    # 4. Initialize VisDrone Demo Mode Camera Manager
    try:
        demo_camera_manager.initialize()
    except Exception as e:
        logger.warning(f"DemoCameraManager initialization warning: {e}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down CCTV Surveillance Platform Backend...")
    demo_camera_manager.shutdown()
    await asyncio.to_thread(stream_manager.stop_all)
    await catalogue_service.close()
    sighting_repo.close()
    logger.info("Shutdown complete.")

app = FastAPI(
    title="AI-Powered Unified CCTV Surveillance Platform API",
    description="Official CCTV Stream Ingestion, Catalogue, ByteTrack & Real ANPR License Plate Recognition API",
    version="1.0.0",
    lifespan=lifespan
)

# Shared hosting uses an explicit host allowlist; local preview remains unchanged.
import os
from starlette.middleware.trustedhost import TrustedHostMiddleware
if os.getenv('SENTINEL_ALLOWED_HOSTS'):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[h.strip() for h in os.environ['SENTINEL_ALLOWED_HOSTS'].split(',') if h.strip()])

@app.get('/healthz', include_in_schema=False)
def healthz():
    # Liveness only. Authenticated /api/system/health reports AI readiness.
    return {'status': 'ok'}

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[s.strip() for s in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

# Register routes
app.middleware("http")(access_middleware)
app.include_router(auth_router)
app.include_router(registry_tools.router)
app.include_router(coverage.router)
app.include_router(cameras.router)
app.include_router(detections.router)
app.include_router(tracks.router)
app.include_router(anpr.router)
app.include_router(analytics.router)
app.include_router(analytics.events_router)
app.include_router(demo.router)

# New police-investigation domain: registry/GIS, vehicle trace, watchlist, alerts
app.include_router(investigation.registry_router)
app.include_router(investigation.investigation_router)
app.include_router(investigation.watchlist_router)
app.include_router(investigation.alerts_router)

# Mount frontend production build statically if available
dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/dashboard", StaticFiles(directory=dist_path, html=True), name="dashboard")

@app.get("/")
async def root():
    return {
        "status": "ONLINE",
        "service": "AI Unified CCTV Surveillance Platform Backend",
        "version": "1.0.0",
        "dashboard_ui": "/dashboard/",
        "catalogue_endpoint": "/api/cameras",
        "detections_endpoint": "/api/detections",
        "tracks_endpoint": "/api/tracks",
        "anpr_endpoint": "/api/anpr",
        "analytics_endpoint": "/api/analytics",
        "events_endpoint": "/api/events",
        "yolo_telemetry": "/api/yolo/stats"
    }

@app.get("/api/system/health")
@app.get("/health")
async def health():
    return {
        "status": "READY" if yolo_detector.model is not None else "DEGRADED",
        "ai": yolo_detector.get_telemetry(),
        "catalogue_error": catalogue_service.last_error,
        "active_streams": stream_manager.get_capacity()["active_workers"],
        "camera_capacity": stream_manager.get_capacity(),
        "yolo_device": yolo_detector.device_name,
        "ocr_gpu": anpr_manager.gpu_available
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
