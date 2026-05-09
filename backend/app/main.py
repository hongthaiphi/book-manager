from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Book Manager API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok"}


from app.api.routes import auth, books, community, loans, notifications, public, stats, trust, uploads

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(books.router, prefix="/api", tags=["books"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])
app.include_router(community.router, prefix="/api", tags=["community"])
app.include_router(loans.router, prefix="/api", tags=["loans"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(trust.router, prefix="/api", tags=["trust"])
app.include_router(public.router, prefix="/api", tags=["public"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
