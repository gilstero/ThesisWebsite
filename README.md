---

# ML-AUTOC Experiment Platform

This repository contains the software accompanying the research project on **Multi-Level AUTOC (ML-AUTOC)**. The platform is designed to facilitate reproducibility and experimentation with the algorithms and experimental configurations described in the associated paper.

The application allows users to download experiment code, explore experimental configurations, and run experiments locally on their own machines.

The platform is available online at:

**mlautoc.com**

---

# Purpose

To enable repeatability and efficiency in the experimental phase of this research, this software platform was developed to provide an interactive environment for running and analyzing ML-AUTOC experiments.

The goal of the software is to allow researchers and users to:

1. **Choose the number of patients in the dataset**
2. **Upload an individual dataset (CSV) and run an experiment**
3. **Select the number of treatment levels allocated to each patient**
4. **Define the cost structure of the experiment**
5. **Choose reporting options** including graphs, resource allocation matrices, and experiment summaries
6. **Configure the structure of marginal treatment effects**
7. **Analyze runtime performance** with execution time recorded and displayed as graphs
8. **Run multiple experiments** with optional re-allocation at individual budget levels to allow direct comparison between policies

---

# Architecture

The platform is implemented using a modern web stack designed to separate the user interface from computational workloads.

### Frontend

The user interface is built using:

**Next.js**

The frontend provides:

* A landing page for navigating the experiment archive
* Downloadable experiment code
* Interactive experiment configuration tools
* Visualization of results and performance metrics

### Backend

The computational backend runs **locally on the user's machine**.

This architecture allows users to:

* Run experiments directly on their own hardware
* Avoid server-side compute limitations
* Maintain full control over experiment parameters and datasets
* Execute potentially expensive simulations efficiently

The backend executes the Python experiment scripts used in the research.

---

# Repository Structure

```
src/app/
 ├ downloads/        # Downloadable experiment archives
 ├ experiments/      # Experiment configuration interface
 ├ globals.css       # Global styling
 ├ layout.tsx        # Root layout
 └ page.tsx          # Landing page

public/
 ├ experiment.zip
 └ exploration.zip
```

---

# Downloadable Archives

The repository provides two downloadable archives:

### Exploration Code

Contains exploratory and preliminary code used prior to the formal experiments. These scripts were used to investigate the behavior of different marginal treatment structures and prototype ideas used later in the research.

### Experiment Code

Contains the Python scripts used to generate the results presented in the paper. These scripts allow users to reproduce the experimental results independently.

---

# Running the Website

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

Open the site locally:

```
http://localhost:3000
```

---

# Build for Production

```bash
npm run build
npm start
```

---

# License

MIT License

---