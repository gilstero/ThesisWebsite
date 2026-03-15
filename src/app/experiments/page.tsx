"use client";

import { useMemo, useState } from "react";
import "./page.css";

type PolicyKey = "lfp" | "pag" | "pag_star" | "ifp" | "pgp";

type PolicyEvaluation = {
  policy_key: PolicyKey;
  policy_name: string;
  toc: number[];
  avg_ate: number[];
  total_effect: number[];
  area: number;
  allocation_by_level: number[][];
};

type ExperimentResult = {
  datasetPath: string;
  costPath: string;
  deltaShape: {
    patients: number;
    levels: number;
  };
  costMatrix: number[][];
  evaluation: {
    shape: {
      patients: number;
      levels: number;
      budget: number;
    };
    baseline: number[];
    policies: Record<string, PolicyEvaluation>;
    summary: Record<string, number>;
  };
  timingsMs: Record<string, number>;
};

const API_BASE = "http://127.0.0.1:8000";
const POLICY_ORDER: PolicyKey[] = ["lfp", "pag", "pag_star", "ifp", "pgp"];
const TIME_ANALYSIS_ORDER: PolicyKey[] = ["ifp", "lfp", "pgp", "pag", "pag_star"];
const POLICY_COLORS: Record<PolicyKey, string> = {
  lfp: "#1d4ed8",
  pag: "#d97706",
  pag_star: "#059669",
  ifp: "#dc2626",
  pgp: "#7c3aed",
};
const LEVEL_COLORS = ["#1d4ed8", "#0f766e", "#d97706", "#dc2626", "#7c3aed", "#0891b2"];

function formatPolicyName(policyKey: string) {
  const displayNames: Record<string, string> = {
    lfp: "LFP",
    pag: "PAG",
    pag_star: "PAG*",
    ifp: "IFP",
    pgp: "PGP",
  };

  return displayNames[policyKey] || policyKey.toUpperCase();
}

function formatDuration(milliseconds: number) {
  if (milliseconds >= 1000) {
    return `${(milliseconds / 1000).toFixed(3)} s`;
  }

  return `${milliseconds.toFixed(3)} ms`;
}

function buildLinePath(values: number[], width: number, height: number, min: number, max: number) {
  if (values.length === 0) {
    return "";
  }

  const safeRange = max - min || 1;

  return values
    .map((value, index) => {
      const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
      const y = height - ((value - min) / safeRange) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function ChartGrid({
  width,
  height,
  horizontalFractions,
  verticalFractions,
}: {
  width: number;
  height: number;
  horizontalFractions: number[];
  verticalFractions: number[];
}) {
  return (
    <>
      {horizontalFractions.map((fraction) => {
        const y = height * fraction;
        return <line key={`h-${fraction}`} x1="0" y1={y} x2={width} y2={y} className="chartGrid" />;
      })}
      {verticalFractions.map((fraction) => {
        const x = width * fraction;
        return <line key={`v-${fraction}`} x1={x} y1="0" x2={x} y2={height} className="chartGrid" />;
      })}
    </>
  );
}

function getTickValues(min: number, max: number) {
  if (min === max) {
    return [min];
  }

  return [max, min + (max - min) * 0.75, min + (max - min) * 0.5, min + (max - min) * 0.25, min];
}

function TocChart({ result }: { result: ExperimentResult }) {
  const policies = POLICY_ORDER
    .map((key) => result.evaluation?.policies?.[key])
    .filter(Boolean) as PolicyEvaluation[];

  const allTocValues = policies.flatMap((policy) => policy.toc);
  const min = Math.min(0, ...allTocValues);
  const max = Math.max(0, ...allTocValues);
  const svgWidth = 680;
  const svgHeight = 320;
  const margin = { top: 12, right: 10, bottom: 34, left: 58 };
  const width = svgWidth - margin.left - margin.right;
  const height = svgHeight - margin.top - margin.bottom;
  const zeroY = height - ((0 - min) / (max - min || 1)) * height;
  const maxLabel = max.toFixed(3);
  const minLabel = min.toFixed(3);
  const yTicks = getTickValues(min, max);

  return (
    <div className="chartCard">
      <div className="chartHeader">
        <div>
          <h3>ML-TOC by Budget</h3>
          <p>Each line shows the per-budget ML-TOC curve returned by the backend.</p>
        </div>
      </div>

      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="chartSvg" role="img" aria-label="ML-AUTOC line chart">
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          <ChartGrid
            width={width}
            height={height}
            horizontalFractions={[0.25, 0.5, 0.75]}
            verticalFractions={[0.25, 0.5, 0.75]}
          />
          <line x1="0" y1="0" x2="0" y2={height} className="chartAxis" />
          <line x1="0" y1={height} x2={width} y2={height} className="chartAxis" />
          <line x1="0" y1={zeroY} x2={width} y2={zeroY} className="chartAxisSecondary" />
          {yTicks.map((tick) => {
            const y = height - ((tick - min) / (max - min || 1)) * height;
            return (
              <text key={tick} x="-10" y={y + 4} textAnchor="end" className="chartTickLabel">
                {tick.toFixed(3)}
              </text>
            );
          })}
          <text x="0" y={height + 24} textAnchor="start" className="chartTickLabel">
            1
          </text>
          <text x={width / 2} y={height + 24} textAnchor="middle" className="chartTickLabel">
            {Math.round(result.evaluation.shape.budget / 2)}
          </text>
          <text x={width} y={height + 24} textAnchor="end" className="chartTickLabel">
            {result.evaluation.shape.budget}
          </text>
          {policies.map((policy) => (
            <path
              key={policy.policy_key}
              d={buildLinePath(policy.toc, width, height, min, max)}
              fill="none"
              stroke={POLICY_COLORS[policy.policy_key]}
              strokeWidth="3"
              strokeLinecap="round"
            />
          ))}
        </g>
      </svg>
    </div>
  );
}

function AllocationChart({
  result,
  selectedPolicy,
  onSelectPolicy,
}: {
  result: ExperimentResult;
  selectedPolicy: PolicyKey;
  onSelectPolicy: (policy: PolicyKey) => void;
}) {
  const policy = result.evaluation?.policies?.[selectedPolicy];
  const series = policy?.allocation_by_level || [];
  const svgWidth = 680;
  const svgHeight = 320;
  const margin = { top: 12, right: 10, bottom: 34, left: 58 };
  const width = svgWidth - margin.left - margin.right;
  const height = svgHeight - margin.top - margin.bottom;
  const maxAllocation = Math.max(1, ...series.flat());
  const yTicks = getTickValues(0, maxAllocation);

  return (
    <div className="chartCard">
      <div className="chartHeader chartHeaderSplit">
        <div>
          <h3>Per-Budget Allocations</h3>
          <p>Cumulative allocations by treatment level for the selected policy.</p>
        </div>

        <select
          value={selectedPolicy}
          onChange={(event) => onSelectPolicy(event.target.value as PolicyKey)}
          className="chartSelect"
        >
          {POLICY_ORDER.filter((key) => result.evaluation?.policies?.[key]).map((key) => (
            <option key={key} value={key}>
              {formatPolicyName(key)}
            </option>
          ))}
        </select>
      </div>

      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="chartSvg" role="img" aria-label="Allocation line chart">
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          <ChartGrid
            width={width}
            height={height}
            horizontalFractions={[0.25, 0.5, 0.75]}
            verticalFractions={[0.25, 0.5, 0.75]}
          />
          <line x1="0" y1="0" x2="0" y2={height} className="chartAxis" />
          <line x1="0" y1={height} x2={width} y2={height} className="chartAxis" />
          {yTicks.map((tick) => {
            const y = height - (tick / (maxAllocation || 1)) * height;
            return (
              <text key={tick} x="-10" y={y + 4} textAnchor="end" className="chartTickLabel">
                {Math.round(tick)}
              </text>
            );
          })}
          <text x="0" y={height + 24} textAnchor="start" className="chartTickLabel">
            1
          </text>
          <text x={width / 2} y={height + 24} textAnchor="middle" className="chartTickLabel">
            {Math.round(result.evaluation.shape.budget / 2)}
          </text>
          <text x={width} y={height + 24} textAnchor="end" className="chartTickLabel">
            {result.evaluation.shape.budget}
          </text>
          {series[0]?.map((_, levelIndex) => {
            const levelSeries = series.map((row) => row[levelIndex] || 0);
            return (
              <path
                key={`${selectedPolicy}-${levelIndex}`}
                d={buildLinePath(levelSeries, width, height, 0, maxAllocation)}
                fill="none"
                stroke={LEVEL_COLORS[levelIndex % LEVEL_COLORS.length]}
                strokeWidth="3"
                strokeLinecap="round"
              />
            );
          })}
        </g>
      </svg>
    </div>
  );
}

function TimeChart({ result }: { result: ExperimentResult }) {
  const entries = TIME_ANALYSIS_ORDER.filter((key) => key in result.timingsMs).map((key) => ({
    key,
    label: formatPolicyName(key),
    value: result.timingsMs[key] || 0,
  }));

  const maxValue = Math.max(1, ...entries.map((entry) => entry.value));

  return (
    <div className="chartCard">
      <div className="chartHeader">
        <div>
          <h3>Policy Runtime</h3>
        </div>
      </div>

      <div className="barChart" role="img" aria-label="Policy runtime bar chart">
        {entries.map((entry) => (
          <div key={entry.key} className="barRow">
            <div className="barLabel">{entry.label}</div>
            <div className="barTrack">
              <div
                className="barFill"
                style={{
                  width: `${(entry.value / maxValue) * 100}%`,
                  backgroundColor: POLICY_COLORS[entry.key],
                }}
              />
            </div>
            <div className="barValue">{formatDuration(entry.value)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ExperimentsPage() {
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  const [patients, setPatients] = useState("1000");
  const [levels, setLevels] = useState("3");
  const [error, setError] = useState("");
  const [costStructure, setCostStructure] = useState("default");
  const [marginalStructure, setMarginalStructure] = useState("random");
  const [datasetFile, setDatasetFile] = useState<File | null>(null);
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [activeTab, setActiveTab] = useState<"area" | "budget" | "time">("area");
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyKey>("lfp");

  const availablePolicyKeys = useMemo(() => {
    if (!result?.evaluation?.policies) {
      return [];
    }

    return POLICY_ORDER.filter((key) => result.evaluation.policies[key]);
  }, [result]);

  const pollProgress = (experimentId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/progress/${experimentId}`);

        if (!res.ok) {
          throw new Error("Failed to retrieve progress.");
        }

        const data = await res.json();

        setProgress(data.progress);

        if (data.status === "failed") {
          clearInterval(interval);
          setRunning(false);
          setProgress(0);
          setError(data.error || "Experiment failed.");
          return;
        }

        if (data.progress >= 100 && data.status === "complete") {
          clearInterval(interval);
          setRunning(false);

          const resultRes = await fetch(`${API_BASE}/result/${experimentId}`);

          if (!resultRes.ok) {
            throw new Error("Failed to retrieve experiment result.");
          }

          const resultData = await resultRes.json();
          const nextResult = resultData.result as ExperimentResult;
          setResult(nextResult);
          setSelectedPolicy(POLICY_ORDER.find((key) => nextResult.evaluation?.policies?.[key]) || "lfp");
          return;
        }
      } catch {
        clearInterval(interval);
        setRunning(false);
        setProgress(0);
        setError("Failed to retrieve progress or result.");
      }
    }, 1000);
  };

  const runExperiment = async () => {
    const patientCount = Number(patients);
    const levelCount = Number(levels);

    if (patientCount < 10) {
      setError("Number of patients must be at least 10.");
      return;
    }

    if (levelCount < 1) {
      setError("Treatment levels must be at least 1.");
      return;
    }

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
        datasetFile.type === "text/csv" || datasetFile.type === "application/vnd.ms-excel";
      const isCsvByName = datasetFile.name.toLowerCase().endsWith(".csv");

      if (!isCsvByType && !isCsvByName) {
        setError("The uploaded dataset must be a CSV file.");
        return;
      }
    }

    setError("");
    setRunning(true);
    setProgress(0);
    setActiveTab("area");
    setResult(null);

    const formData = new FormData();

    formData.append("levels", String(levelCount));
    formData.append("costStructure", costStructure);
    formData.append("marginalStructure", marginalStructure);

    if (datasetFile) {
      formData.append("mode", "csv");
      formData.append("datasetFile", datasetFile);
    } else {
      formData.append(
        "datasetConfig",
        JSON.stringify({
          patients: patientCount,
          levels: levelCount,
          costStructure,
          marginalStructure,
        })
      );
      formData.append("mode", "generate");
    }

    try {
      const res = await fetch(`${API_BASE}/run-experiment`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        setRunning(false);
        setProgress(0);
        setError("Failed to start experiment.");
        return;
      }

      const data = await res.json();
      pollProgress(data.experimentId);
    } catch {
      setRunning(false);
      setProgress(0);
      setError("Local backend is not running. Please start the backend and try again.");
    }
  };

  return (
    <main className="page">
      <div className="experimentsPage">
        <div className="backendNotice">
          <h2 className="backendNoticeTitle">Local Backend Required</h2>

          <p>
            Experiments are executed locally on your computer for performance and reproducibility.
            To run experiments, you must first download and start the Python backend.
          </p>

          <ol className="backendSteps">
            <li>Download the backend folder.</li>
            <li>Open a terminal in the folder.</li>
            <li>
              Run: <code>uvicorn main:app --reload --host 127.0.0.1 --port 8000</code>
            </li>
            <li>Return to this page and run your experiment.</li>
          </ol>

          <a href="/mlautoc-backend.zip" download className="backendDownloadButton">
            Download Backend
          </a>
        </div>

        <div className="experimentWrapper">
          <div className="experimentLayout">
            <section className="controls">
              <h1 className="sectionTitle">Experiment Controls</h1>

              <div className="controlGroup">
                <label>Number of Patients</label>
                <input type="number" min={10} value={patients} onChange={(e) => setPatients(e.target.value)} />
              </div>

              <div className="controlGroup">
                <label>Treatment Levels</label>
                <input type="number" min={1} value={levels} onChange={(e) => setLevels(e.target.value)} />
              </div>

              <div className="controlGroup">
                <label>Cost Structure</label>
                <select value={costStructure} onChange={(e) => setCostStructure(e.target.value)}>
                  <option value="default">Default (all costs = 1)</option>
                  <option value="increasing">Increasing</option>
                  <option value="decreasing">Decreasing</option>
                  <option value="random">Random</option>
                </select>
              </div>

              <div className="controlGroup">
                <label>Marginal Structure</label>
                <select value={marginalStructure} onChange={(e) => setMarginalStructure(e.target.value)}>
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
                        file.type === "text/csv" || file.type === "application/vnd.ms-excel";
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

              <button className="createButton">Create Dataset</button>
              <button className="runButton" onClick={runExperiment}>
                Run Experiment
              </button>
            </section>

            <section className="output">
              <h1 className="sectionTitle">Experiment Output</h1>

              {!result ? (
                <div className="placeholder">Output from the experiment will appear here.</div>
              ) : (
                <div className="visualizationPanel">
                  <div className="visualizationTabs">
                    <button
                      className={`tabButton ${activeTab === "area" ? "activeTab" : ""}`}
                      onClick={() => setActiveTab("area")}
                    >
                      Area Output
                    </button>

                    <button
                      className={`tabButton ${activeTab === "budget" ? "activeTab" : ""}`}
                      onClick={() => setActiveTab("budget")}
                    >
                      Per Budget Allocations
                    </button>

                    <button
                      className={`tabButton ${activeTab === "time" ? "activeTab" : ""}`}
                      onClick={() => setActiveTab("time")}
                    >
                      Time Analysis
                    </button>
                  </div>

                  <div className="tabContent">
                    {activeTab === "area" && (
                      <div className="resultsStack">
                        <div className="areaOutputGrid">
                          {Object.entries(result.evaluation?.summary || {}).map(([key, value]) => (
                            <div key={key} className="areaCard">
                              <div className="areaCardTitle">{formatPolicyName(key)}</div>
                              <div className="areaCardValue">{Number(value).toFixed(4)}</div>
                            </div>
                          ))}
                        </div>

                        <TocChart result={result} />
                      </div>
                    )}

                    {activeTab === "budget" && availablePolicyKeys.length > 0 && (
                      <AllocationChart
                        result={result}
                        selectedPolicy={selectedPolicy}
                        onSelectPolicy={setSelectedPolicy}
                      />
                    )}

                    {activeTab === "time" && <TimeChart result={result} />}
                  </div>
                </div>
              )}
            </section>
          </div>

          <section className="progressbackground">
            <div className="progressContainer">
              <div className="progressBar">
                <div className="progressFill" style={{ width: `${progress}%` }} />
              </div>

              <p className="progressText">{running ? `Experiment running: ${progress}%` : "Idle"}</p>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
