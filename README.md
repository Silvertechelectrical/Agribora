# AGRIBORA

A responsive crop recommendation website paired with a small FastAPI inference service. The frontend sends the seven model features to a Python API; the API loads the trained artifacts once at startup and returns the predicted crop label.

> Predictions reflect patterns in the training dataset. They are not guarantees of crop success and are not a substitute for local agricultural advice.

## Project layout

- `frontend/` — static HTML, CSS and JavaScript site; suitable for GitHub Pages.
- `backend/` — FastAPI application, training script, dependency list and local artifact/data folders.
- `backend/data/Crop_Recommendation.csv` — training data is kept local and excluded from Git.
- `backend/models/` — trusted trained `crop_rf_model.pkl` and `label_encoder.pkl` artifacts used by the API.

## Start the website and API locally

1. Install Python 3.10+ and create/activate a virtual environment.
2. From the repository root, install the backend requirements with `pip install -r backend/requirements.txt`.
3. The trained model artifacts are already included in `backend/models/`. The CSV is needed only if you want to retrain; copy it into `backend/data/` or pass its path with `--dataset`.
4. Optional retraining: `python backend/train_model.py`.
5. Start the API: `uvicorn main:app --app-dir backend --reload`.
6. Serve the `frontend/` folder using a local static server (for example, VS Code Live Server). Keep `frontend/config.js` set to `http://127.0.0.1:8000`.
7. Open the static site and try the sample values from the notebook: N 90, P 42, K 43, temperature 21, humidity 82, pH 6.5, rainfall 203. The included model predicts rice for these values.

You can check the service at `http://127.0.0.1:8000/health` and inspect its interactive API docs at `http://127.0.0.1:8000/docs`.

## Model and inputs

The notebook describes a `RandomForestClassifier` with 100 trees and a `LabelEncoder`. Input feature order is `Nitrogen`, `Phosphorus`, `Potassium`, `Temperature`, `Humidity`, `pH_Value`, `Rainfall`. The trainer cleans the dataset, encodes the labels, performs a stratified 80/20 split with random state 42 and exports both artifacts. The API returns the crop name only; it does not report a fabricated confidence score.

The dataset's nutrient, temperature and rainfall units/ranges must be verified against the original data owner before production use. The interface labels rainfall as dataset units (typically mm), and does not claim agronomic suitability outside the dataset's context.

## GitHub Pages and API deployment

GitHub Pages hosts the static website only; it cannot run FastAPI. Deploy `frontend/` to Pages and deploy `backend/` to a separate Python-capable host:

1. Push the source to a GitHub repository. Do not commit private training data, virtual environments, or credentials. The trusted inference artifacts are included.
2. Deploy the FastAPI service using the command `uvicorn main:app --host 0.0.0.0 --port $PORT` (use the host's required port syntax if different).
3. Configure `AGRIBORA_ALLOWED_ORIGINS` on the API to the exact production site origin, such as `https://<account>.github.io`, and include a local development origin when required.
4. Set `window.AGRIBORA_CONFIG.apiBaseUrl` in `frontend/config.js` to the API's public HTTPS base URL.
5. Enable GitHub Pages for the `frontend/` folder, then test the API URL, CORS, validation errors, unavailable-service state, and mobile layout.

For deployment systems that build from a repository root, set their Python working directory to `backend/`. Serialized joblib/pickle artifacts must only be loaded from trusted sources.

## Notes

The original notebook is at the repository root. The trained model and label encoder have been recreated from the supplied 2,200-row dataset and are included so the API can predict immediately. The dataset itself remains local and is not committed.
