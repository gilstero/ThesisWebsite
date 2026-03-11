"use client";

import { useState } from "react";
import "./page.css";

export default function ExperimentsPage() {
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);

  const [patients, setPatients] = useState("1000");
  const [levels, setLevels] = useState("3");
  const [error, setError] = useState("");

  const [costStructure, setCostStructure] = useState("default");
  const [marginalStructure, setMarginalStructure] = useState("random");

  const [datasetFile, setDatasetFile] = useState<File | null>(null);

  const pollProgress = (experimentId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${experimentId}`);
        const data = await res.json();
  
        setProgress(data.progress);
  
        if (data.progress >= 100) {
          clearInterval(interval);
          setRunning(false);
        }
      } catch (error) {
        clearInterval(interval);
        setRunning(false);
        setError("Failed to retrieve progress.");
      }
    }, 1000);
  };

  const runExperiment = async () => {
    const patientCount = Number(patients);
    const levelCount = Number(levels);
  
    if (patientCount * levelCount > 5000) {
      setError("Patients × Levels must be ≤ 5000.");
      return;
    }
  
    if (!datasetFile && !patients) {
      setError("Please upload a CSV or provide dataset generation inputs.");
      return;
    }
  
    if (datasetFile) {
      const isCsvByType =
        datasetFile.type === "text/csv" ||
        datasetFile.type === "application/vnd.ms-excel";
  
      const isCsvByName = datasetFile.name.toLowerCase().endsWith(".csv");
  
      if (!isCsvByType && !isCsvByName) {
        setError("The uploaded dataset must be a CSV file.");
        return;
      }
    }
  
    setError("");
    setRunning(true);
    setProgress(0);
  
    const formData = new FormData();
  
    formData.append("levels", String(levelCount));
    formData.append("costStructure", costStructure);
    formData.append("marginalStructure", marginalStructure);
  
    if (datasetFile) {
      formData.append("mode", "csv");
      formData.append("datasetFile", datasetFile);
    } else {
      formData.append("mode", "generate");
      formData.append(
        "datasetConfig",
        JSON.stringify({
          patients: patientCount,
          levels: levelCount,
          costStructure,
          marginalStructure,
        })
      );
    }
  
    const res = await fetch("/api/run-experiment", {
      method: "POST",
      body: formData,
    });
  
    if (!res.ok) {
      setRunning(false);
      setError("Failed to start experiment.");
      return;
    }
  
    const data = await res.json();
    pollProgress(data.experimentId);
  };


  return (
    <main className="page">
      
      <div className="experimentsPage">

        <div className="backendNotice">

        <h2 className="backendNoticeTitle">
          Local Backend Required
        </h2>

        <p>
          Experiments are executed locally on your computer for performance and reproducibility.
          To run experiments, you must first download and start the Python backend.
        </p>

        <ol className="backendSteps">
          <li>Download the backend folder.</li>
          <li>Open a terminal in the folder.</li>
          <li>Run: <code>uvicorn main:app --reload --host 127.0.0.1 --port 8000</code></li>
          <li>Return to this page and run your experiment.</li>
        </ol>

        <a
          href="/mlautoc-backend.zip"
          download
          className="backendDownloadButton"
        >
          Download Backend
        </a>

        </div>

        <div className="experimentWrapper">

          <div className="experimentLayout">

            <section className="controls">
              <h1 className="sectionTitle">Experiment Controls</h1>

              <div className="controlGroup">
                <label>Number of Patients</label>
                <input
                  type="number"
                  value={patients}
                  onChange={(e) => setPatients(e.target.value)}
                />
              </div>

              <div className="controlGroup">
                <label>Treatment Levels</label>
                <input
                  type="number"
                  value={levels}
                  onChange={(e) => setLevels(e.target.value)}
                />
              </div>

              <div className="controlGroup">
                <label>Cost Structure</label>
                <select
                  value={costStructure}
                  onChange={(e) => setCostStructure(e.target.value)}
                >
                  <option value="default">Default (all costs = 1)</option>
                  <option value="increasing">Increasing</option>
                  <option value="decreasing">Decreasing</option>
                  <option value="random">Random</option>
                </select>
              </div>

              <div className="controlGroup">
                <label>Marginal Structure</label>
                <select
                  value={marginalStructure}
                  onChange={(e) => setMarginalStructure(e.target.value)}
                >
                  <option value="random">Random</option>
                  <option value="increasing">Increasing</option>
                  <option value="decreasing">Decreasing</option>
                </select>
              </div>

              <div className="controlGroup">
                <label>Upload Dataset (CSV)</label>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null;
                    setDatasetFile(file);

                    if (file) {
                      const validType =
                        file.type === "text/csv" ||
                        file.type === "application/vnd.ms-excel";
                      const validName = file.name.toLowerCase().endsWith(".csv");

                      if (!validType && !validName) {
                        setError("The uploaded dataset must be a CSV file.");
                      } else {
                        setError("");
                      }
                    }
                  }}
                />
              </div>

              {error && <p className="inputError">{error}</p>}

              <button className="createButton" >
                Create Dataset
              </button>

              <button className="runButton" onClick={runExperiment}>
                Run Experiment
              </button>

            </section>

            <section className="output">
              <h1 className="sectionTitle">Experiment Output</h1>

              <div className="placeholder">
                Output from the experiment will appear here.
              </div>
            </section>

          </div>


          {/* PROGRESS BAR BELOW PANELS */}

          <div className="progressContainer">

            <div className="progressBar">
              <div
                className="progressFill"
                style={{ width: `${progress}%` }}
              />
            </div>

            <p className="progressText">
              {running ? `Experiment running: ${progress}%` : "Idle"}
            </p>

          </div>

        </div>
      </div>

    </main>
  );
}