"""FastAPI inference service for the AGRIBORA crop recommendation model."""

from __future__ import annotations

import logging
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parent
MODEL_DIR = Path(os.getenv("AGRIBORA_MODEL_DIR", ROOT / "models"))
MODEL_PATH = MODEL_DIR / "crop_rf_model.pkl"
ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"
FEATURES = ["Nitrogen", "Phosphorus", "Potassium", "Temperature", "Humidity", "pH_Value", "Rainfall"]
logger = logging.getLogger("agribora")

model = None
label_encoder = None
model_load_error: str | None = None


class PredictionRequest(BaseModel):
    """Measurements in the same feature names and order used for training."""

    model_config = ConfigDict(extra="forbid")

    Nitrogen: Annotated[float, Field(ge=0)]
    Phosphorus: Annotated[float, Field(ge=0)]
    Potassium: Annotated[float, Field(ge=0)]
    Temperature: float
    Humidity: Annotated[float, Field(ge=0, le=100)]
    pH_Value: Annotated[float, Field(ge=0, le=14)]
    Rainfall: Annotated[float, Field(ge=0)]

    @field_validator(*FEATURES)
    @classmethod
    def values_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Measurements must be finite numbers.")
        return value


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load the trusted model artifacts once when the service starts."""
    global model, label_encoder, model_load_error
    try:
        if not MODEL_PATH.is_file() or not ENCODER_PATH.is_file():
            raise FileNotFoundError(
                "Model artifacts are missing. Add the trained model files under backend/models."
            )
        model = joblib.load(MODEL_PATH)
        label_encoder = joblib.load(ENCODER_PATH)
        model_load_error = None
        logger.info("Loaded AGRIBORA model and crop label encoder.")
    except Exception as exc:  # Keep health endpoints available while setup is incomplete.
        model = None
        label_encoder = None
        model_load_error = str(exc)
        logger.warning("AGRIBORA model is not ready: %s", exc)
    yield


app = FastAPI(
    title="AGRIBORA Crop Recommendation API",
    description="Predicts one crop label from soil and environmental measurements.",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "AGRIBORA_ALLOWED_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5501,http://localhost:5501",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, bool | str]:
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/predict")
def predict(request: PredictionRequest) -> dict[str, str]:
    if model is None or label_encoder is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "The prediction model is not installed. Follow the README to train the model "
                "and place its artifacts in backend/models."
            ),
        )

    row = pd.DataFrame([request.model_dump()], columns=FEATURES)
    try:
        predicted_class = model.predict(row)
        crop = str(label_encoder.inverse_transform(predicted_class)[0])
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="The model could not process these measurements.") from exc

    return {"crop": crop}
