from contextlib import asynccontextmanager

from fastapi import FastAPI

from telegram_bot import create_bot


telegram_app = create_bot()


@asynccontextmanager
async def lifespan(app: FastAPI):

    await telegram_app.initialize()

    await telegram_app.start()

    await telegram_app.updater.start_polling()

    yield

    await telegram_app.updater.stop()

    await telegram_app.stop()

    await telegram_app.shutdown()


app = FastAPI(
    lifespan=lifespan
)


@app.get("/")
async def root():

    return {
        "status": "ok"
    }