from typing import Optional
from pathlib import Path
import json
import uuid
import threading
import traceback

import numpy as np
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from strictlyincreasing import generatestrictlyincreasing
from strictlydecreasing import generatestrictlydecreasing
from nonnegativemarginals import generatenonnegative

from solvers import (
    solve_lfp,
    solve_pag,
    solve_pag_star,
    solve_ifp,
    solve_pgp,
)
from evaluation import evaluate_policy_outputs

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://www.mlautoc.com",
        "https://mlautoc.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GENERATED_DIR = Path("generated_datasets")
GENERATED_DIR.mkdir(exist_ok=True)

experiments: dict[str, dict] = {}


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/progress/{experiment_id}")
def get_progress(experiment_id: str):
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")

    exp = experiments[experiment_id]
    return {
        "status": exp["status"],
        "progress": exp["progress"],
        "message": exp["message"],
        "error": exp["error"],
    }


@app.get("/result/{experiment_id}")
def get_result(experiment_id: str):
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return experiments[experiment_id]


def set_experiment(
    experiment_id: str,
    *,
    progress: int,
    status: str,
    message: str,
):
    experiments[experiment_id]["progress"] = progress
    experiments[experiment_id]["status"] = status
    experiments[experiment_id]["message"] = message


def make_cost_matrix(
    patients: int,
    levels: int,
    structure: str,
) -> np.ndarray:
    if structure == "default":
        row = np.ones(levels, dtype=float)
    elif structure == "increasing":
        row = np.arange(1, levels + 1, dtype=float)
    elif structure == "decreasing":
        row = np.arange(levels, 0, -1, dtype=float)
    elif structure == "random":
        rng = np.random.default_rng(0)
        row = rng.uniform(0.5, 3.0, size=levels)
    else:
        raise ValueError(f"Unknown cost structure: {structure}")

    return np.tile(row, (patients, 1))


def generate_delta_matrix(
    *,
    patients: int,
    levels: int,
    marginal_structure: str,
    seed: int = 0,
) -> np.ndarray:
    if marginal_structure == "increasing":
        _, delta, _ = generatestrictlyincreasing(
            n=patients,
            L=levels,
            sigma=0.5,
            seed=seed,
            gap=1.0,
        )
        return delta

    if marginal_structure == "decreasing":
        _, delta, _ = generatestrictlydecreasing(
            n=patients,
            L=levels,
            sigma=0.5,
            seed=seed,
            gap=1.0,
        )
        return delta

    if marginal_structure == "random":
        _, delta, _ = generatenonnegative(
            n=patients,
            L=levels,
            sigma=0.5,
            seed=seed,
        )
        return delta

    raise ValueError(f"Unknown marginal structure: {marginal_structure}")


def load_or_create_dataset(
    *,
    mode: str,
    levels: int,
    cost_structure: str,
    marginal_structure: str,
    dataset_config: Optional[str],
    uploaded_bytes: Optional[bytes],
    uploaded_filename: Optional[str],
    experiment_id: str,
) -> tuple[np.ndarray, np.ndarray, str, str]:
    if mode == "csv":
        if uploaded_bytes is None or uploaded_filename is None:
            raise ValueError("CSV mode selected but no file was uploaded.")

        dataset_path = GENERATED_DIR / f"delta_{experiment_id}.csv"
        dataset_path.write_bytes(uploaded_bytes)

        delta = np.loadtxt(dataset_path, delimiter=",")

        if delta.ndim != 2:
            raise ValueError("Uploaded CSV must be a 2D matrix.")

        patients, actual_levels = delta.shape

        if actual_levels != levels:
            raise ValueError(
                f"Uploaded CSV has {actual_levels} levels, but frontend sent {levels}."
            )

        cost_matrix = np.ones((patients, levels), dtype=float)
        cost_path = GENERATED_DIR / f"costs_{experiment_id}.npy"
        np.save(cost_path, cost_matrix)

        return delta, cost_matrix, str(dataset_path), str(cost_path)

    if mode == "generate":
        if dataset_config is None:
            raise ValueError("Generate mode selected but datasetConfig is missing.")

        config = json.loads(dataset_config)

        patients = int(config["patients"])
        config_levels = int(config["levels"])
        config_cost_structure = str(config["costStructure"])
        config_marginal_structure = str(config["marginalStructure"])

        if patients < 10:
            raise ValueError("Patients must be at least 10.")
        if config_levels < 1:
            raise ValueError("Levels must be at least 1.")
        if patients * config_levels > 5000:
            raise ValueError("Patients × Levels must be ≤ 5000.")
        if config_levels != levels:
            raise ValueError("Form levels and datasetConfig levels do not match.")

        delta = generate_delta_matrix(
            patients=patients,
            levels=config_levels,
            marginal_structure=config_marginal_structure,
            seed=0,
        )

        cost_matrix = make_cost_matrix(
            patients=patients,
            levels=config_levels,
            structure=config_cost_structure,
        )

        dataset_path = GENERATED_DIR / f"delta_{experiment_id}.csv"
        cost_path = GENERATED_DIR / f"costs_{experiment_id}.npy"

        np.savetxt(dataset_path, delta, delimiter=",")
        np.save(cost_path, cost_matrix)

        return delta, cost_matrix, str(dataset_path), str(cost_path)

    raise ValueError("Invalid mode.")


def run_experiment_job(
    *,
    experiment_id: str,
    mode: str,
    levels: int,
    cost_structure: str,
    marginal_structure: str,
    dataset_config: Optional[str],
    uploaded_bytes: Optional[bytes],
    uploaded_filename: Optional[str],
):
    try:
        set_experiment(
            experiment_id,
            progress=10,
            status="running",
            message="Preparing dataset",
        )

        delta, cost_matrix, dataset_path, cost_path = load_or_create_dataset(
            mode=mode,
            levels=levels,
            cost_structure=cost_structure,
            marginal_structure=marginal_structure,
            dataset_config=dataset_config,
            uploaded_bytes=uploaded_bytes,
            uploaded_filename=uploaded_filename,
            experiment_id=experiment_id,
        )

        set_experiment(
            experiment_id,
            progress=20,
            status="running",
            message="Dataset and cost matrix ready",
        )

        policy_outputs = {}

        set_experiment(
            experiment_id,
            progress=35,
            status="running",
            message="Running LFP",
        )
        policy_outputs["lfp"] = solve_lfp(delta)

        set_experiment(
            experiment_id,
            progress=50,
            status="running",
            message="Running PAG",
        )
        policy_outputs["pag"] = solve_pag(delta)

        set_experiment(
            experiment_id,
            progress=65,
            status="running",
            message="Running PAG*",
        )
        policy_outputs["pag_star"] = solve_pag_star(delta)

        set_experiment(
            experiment_id,
            progress=78,
            status="running",
            message="Running IFP",
        )
        policy_outputs["ifp"] = solve_ifp(delta)

        set_experiment(
            experiment_id,
            progress=90,
            status="running",
            message="Running PGP",
        )
        policy_outputs["pgp"] = solve_pgp(delta)

        set_experiment(
            experiment_id,
            progress=95,
            status="running",
            message="Evaluating policy outputs",
        )

        evaluation = evaluate_policy_outputs(
            policy_outputs,
            delta,
            n_mc_random=200,
            random_seed=0,
        )

        experiments[experiment_id]["result"] = {
            "datasetPath": dataset_path,
            "costPath": cost_path,
            "deltaShape": {
                "patients": int(delta.shape[0]),
                "levels": int(delta.shape[1]),
            },
            "costMatrix": cost_matrix.tolist(),
            "evaluation": evaluation,
        }

        set_experiment(
            experiment_id,
            progress=100,
            status="complete",
            message="Experiment complete",
        )

    except Exception as e:
        experiments[experiment_id]["status"] = "failed"
        experiments[experiment_id]["progress"] = 0
        experiments[experiment_id]["message"] = "Experiment failed"
        experiments[experiment_id]["error"] = f"{e}\n\n{traceback.format_exc()}"


@app.post("/run-experiment")
async def run_experiment(
    mode: str = Form(...),
    levels: int = Form(...),
    costStructure: str = Form(...),
    marginalStructure: str = Form(...),
    datasetConfig: Optional[str] = Form(None),
    datasetFile: Optional[UploadFile] = File(None),
):
    experiment_id = str(uuid.uuid4())

    uploaded_bytes = None
    uploaded_filename = None

    if datasetFile is not None:
        uploaded_bytes = await datasetFile.read()
        uploaded_filename = datasetFile.filename

    experiments[experiment_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Experiment queued",
        "error": None,
        "result": None,
    }

    thread = threading.Thread(
        target=run_experiment_job,
        kwargs={
            "experiment_id": experiment_id,
            "mode": mode,
            "levels": levels,
            "cost_structure": costStructure,
            "marginal_structure": marginalStructure,
            "dataset_config": datasetConfig,
            "uploaded_bytes": uploaded_bytes,
            "uploaded_filename": uploaded_filename,
        },
        daemon=True,
    )
    thread.start()

    return {
        "experimentId": experiment_id,
        "message": "Experiment started",
    }