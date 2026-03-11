from typing import Optional
from pathlib import Path
import json
import uuid

import numpy as np
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from strictlyincreasing import generatestrictlyincreasing
from nonnegativemarginals import generatenonnegative
from strictlydecreasing import generatestrictlydecreasing

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GENERATED_DIR = Path("generated_datasets")
GENERATED_DIR.mkdir(exist_ok=True)


@app.get("/")
def root():
    return {"message": "Backend is running"}


def make_cost_matrix(
    patients: int,
    levels: int,
    structure: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Returns a (patients, levels) cost matrix.
    """

    if structure == "default":
        base = np.ones(levels, dtype=float)

    elif structure == "increasing":
        base = np.arange(1, levels + 1, dtype=float)

    elif structure == "decreasing":
        base = np.arange(levels, 0, -1, dtype=float)

    elif structure == "random":
        base = rng.uniform(0.5, 3.0, size=levels)

    else:
        raise ValueError(f"Unknown cost structure: {structure}")

    return np.tile(base, (patients, 1))


def generate_delta_matrix(
    patients: int,
    levels: int,
    marginal_structure: str,
    seed: int,
) -> np.ndarray:
    """
    Returns a (patients, levels) marginal benefit matrix.
    """

    if marginal_structure == "increasing":
        _, delta, _ = generatestrictlyincreasing(
            n=patients,
            L=levels,
            sigma=0.5,
            seed=seed,
            gap=1.0,
        )
        return delta

    elif marginal_structure == "random":
        _, delta, _ = generatenonnegative(
            n=patients,
            L=levels,
            sigma=0.5,
            seed=seed,
        )
        return delta

    elif marginal_structure == "decreasing":
        _, delta, _ = generatestrictlydecreasing(
            n=patients,
            L=levels,
            sigma=0.5,
            seed=seed,
            gap=1.0,
        )
        return delta

    else:
        raise ValueError(f"Unknown marginal structure: {marginal_structure}")


@app.post("/run-experiment")
async def run_experiment(
    mode: str = Form(...),
    levels: int = Form(...),
    costStructure: str = Form(...),
    marginalStructure: str = Form(...),
    datasetConfig: Optional[str] = Form(None),
    datasetFile: Optional[UploadFile] = File(None),
):
    if mode not in {"csv", "generate"}:
        raise HTTPException(status_code=400, detail="Invalid mode.")

    if levels < 1:
        raise HTTPException(status_code=400, detail="Levels must be at least 1.")

    experiment_id = str(uuid.uuid4())[:8]

    # -----------------------------
    # CASE 1: uploaded CSV
    # -----------------------------
    if mode == "csv":
        if datasetFile is None:
            raise HTTPException(status_code=400, detail="CSV mode selected but no file was uploaded.")

        if not datasetFile.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a CSV.")

        contents = await datasetFile.read()

        dataset_path = GENERATED_DIR / f"delta_{experiment_id}.csv"
        dataset_path.write_bytes(contents)

        try:
            delta = np.loadtxt(dataset_path, delimiter=",")
        except Exception:
            dataset_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded CSV could not be parsed.")

        if delta.ndim != 2:
            dataset_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded CSV must be a 2D matrix.")

        patients, actual_levels = delta.shape

        if actual_levels != levels:
            dataset_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded CSV has {actual_levels} levels, but frontend sent {levels}.",
            )

        cost_matrix = np.ones((patients, levels), dtype=float)

        cost_path = GENERATED_DIR / f"costs_{experiment_id}.npy"
        np.save(cost_path, cost_matrix)

        return {
            "message": "CSV uploaded and saved successfully.",
            "experimentId": experiment_id,
            "datasetPath": str(dataset_path),
            "costPath": str(cost_path),
            "shape": {
                "patients": int(patients),
                "levels": int(levels),
            },
        }

    # -----------------------------
    # CASE 2: generate dataset
    # -----------------------------
    if datasetConfig is None:
        raise HTTPException(status_code=400, detail="Generate mode selected but no datasetConfig was provided.")

    try:
        config = json.loads(datasetConfig)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="datasetConfig is not valid JSON.")

    try:
        patients = int(config["patients"])
        config_levels = int(config["levels"])
        config_cost_structure = str(config["costStructure"])
        config_marginal_structure = str(config["marginalStructure"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="datasetConfig is missing required fields or has invalid values.",
        )

    if patients < 10:
        raise HTTPException(status_code=400, detail="Patients must be at least 10.")

    if config_levels < 1:
        raise HTTPException(status_code=400, detail="Levels must be at least 1.")

    if config_levels != levels:
        raise HTTPException(
            status_code=400,
            detail="Form levels and datasetConfig levels do not match.",
        )

    if patients * levels > 5000:
        raise HTTPException(status_code=400, detail="Patients × Levels must be ≤ 5000.")

    rng = np.random.default_rng(0)

    delta = generate_delta_matrix(
        patients=patients,
        levels=levels,
        marginal_structure=config_marginal_structure,
        seed=0,
    )

    cost_matrix = make_cost_matrix(
        patients=patients,
        levels=levels,
        structure=config_cost_structure,
        rng=rng,
    )

    dataset_path = GENERATED_DIR / f"delta_{experiment_id}.csv"
    cost_path = GENERATED_DIR / f"costs_{experiment_id}.npy"

    np.savetxt(dataset_path, delta, delimiter=",")
    np.save(cost_path, cost_matrix)

    return {
        "message": "Dataset generated successfully.",
        "experimentId": experiment_id,
        "datasetPath": str(dataset_path),
        "costPath": str(cost_path),
        "shape": {
            "patients": int(patients),
            "levels": int(levels),
        },
        "selectedOptions": {
            "costStructure": config_cost_structure,
            "marginalStructure": config_marginal_structure,
        },
    }