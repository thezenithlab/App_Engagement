# HICSS-60 Mobile App Psychographics & Motivational Drivers Classifier

Welcome to the **HICSS-60 Extension** repository by **thezenithlab**. 

This repository contains the dataset and codebase to classify and visualize **85,321 unique mobile applications** into psychographic classes and granular motivational drivers. Using a hybrid cascade pipeline, we map the entire application ecosystem to provide a psychological lens for mobile human-computer interaction (HCI) research and telemetry logs.

---

## 🌟 Theoretical Foundation

Our taxonomy divides the application ecosystem along two core theoretical frameworks:

### 1. Psychographic Classification (Geng & Guo, 2022; Hassenzahl, 2003)
*   **Hedonic Use (SELF-Type):** Driven by intrinsic motivation, leisure, play, self-expression, identity, and emotional validation (e.g., social networks, video streaming, casual gaming).
*   **Pragmatic / Utilitarian Use (ACT-Type):** Driven by extrinsic motivation, usability, efficiency, practical problem solving, and task completion (e.g., financial banking, spreadsheets, system maintenance tools).

### 2. The 4-Quadrant Motivational Drivers Matrix
To provide high-resolution mapping, we subcategorize apps into four motivational drivers:

| Category | Primary Motivation | Emotional Payoff | Success Metric for User | Typical Genres |
| :--- | :--- | :--- | :--- | :--- |
| **🏆 Achievement** | Efficiency | Relief / Control | Task Completion | Productivity, Tools, Finance, Business, Shopping |
| **💬 Connection** | Belonging | Validation / Security | Interaction / Updates | Social, Communication, Dating, Chat |
| **🎮 Escape** | Stimulation | Pleasure / Distraction | Time spent / "Flow" | Games, Video Players, Music, Themes |
| **🌱 Growth** | Competence | Pride / Mastery | Streak / New Skill | Education, Health & Fitness, Books, Meditation |

---

## ⚙️ How It Works: The Hybrid Cascade Pipeline

To process 85,000+ apps with high accuracy, the project implements a three-stage pipeline:

```
        [Raw APPS Table (85,323 rows)]
                      ↓
         [Stage 1: Deterministic Rules]  ──> Direct genre standardization & Title keywords (85%)
                      ↓
       [Stage 2: Embeddings & Projections] ──> nomic-embed-text (768-dim) for top 10,000 apps
                      ↓
         [Stage 3: LLM Audit Agent]    ──> gemma4:e4b local reasoning verification (sample)
                      ↓
    [WebGL Interactive Graph Dashboard] ──> Served at http://localhost:8500
```

1.  **Stage 1: Deterministic Rules & Keyword Mapping:** Core app categories standardly route to specific categories. For ambiguous genres (e.g., *Lifestyle*, *Tools*, *Personalization*), title keywords (e.g., *"workout"* → Growth, *"dating"* → Connection) refine the mapping. Duplicate package IDs are filtered out to ensure database uniqueness.
2.  **Stage 2: Semantic 2D Projections (Top 10,000 apps):** The top 10,000 apps by installs are embedded into high-density 768-dimensional vectors using `nomic-embed-text`. We use Principal Component Analysis (PCA) to down-project to 10 principal components, then t-SNE to project to 2D coordinates (`embedding_x`, `embedding_y`).
3.  **Stage 3: Local LLM Auditing:** A local LLM agent (`gemma4:e4b`) audits a stratified random sample of 200 apps to verify our pipeline rules against deep academic reasoning.

---

## 📊 Empirical Findings & t-SNE Cluster Insights

Our classification of **85,321 unique applications** yields the following distributions:

*   **Hedonic Use (SELF-Type):** **54,752 apps (64.17%)**
*   **Pragmatic Use (ACT-Type):** **30,569 apps (35.83%)**

### Motivational Drivers Proportions
*   **🎮 Escape:** **43,068 apps (50.48%)**
*   **🏆 Achievement:** **30,569 apps (35.83%)**
*   **🌱 Growth:** **8,279 apps (9.70%)**
*   **💬 Connection:** **3,405 apps (3.99%)**

### 🔍 Deep Cluster Insights (From t-SNE Coordinate Space)
Our 2D projection reveals fascinating structural boundaries within the mobile ecosystem:
1.  **The Escape Gaming Continent:** Over 50% of the map forms a massive, highly clustered continent representing Hedonic *Escape* (games and media players). This shows that the majority of app store real estate is dedicated to cognitive relief, stimulation, and distraction.
2.  **The Utilitarian Grid (Achievement):** Pragmatic *Achievement* apps form a highly structured semantic grid spanning finance, shopping, and utilities. They group tightly based on transactional efficiency, illustrating that users treat these apps as transient coping mechanisms.
3.  **The Scarcity vs. Engagement Paradox:** *Connection* (social) and *Growth* (fitness, meditation) represent the smallest percentages of total *app counts* (3.99% and 9.7% respectively). However, referencing our longitudinal usetime telemetry logs, **these two categories capture a disproportionate share of daily active time**. This highlights a fascinating gap between "app catalog density" and "actual user attention".

---

## 🖥️ How to Run the WebGL Dashboard

We provide two easy ways to launch the interactive, glassmorphic dark-theme WebGL dashboard.

### Option 1: Running with Docker (Recommended - Instant)
Ensure you have Docker and Docker Compose installed.

1.  Clone this repository:
    ```bash
    git clone https://github.com/thezenithlab/App_Engagement.git
    cd App_Engagement
    ```
2.  Launch the containerized dashboard:
    ```bash
    docker-compose up --build
    ```
3.  Open your browser and navigate to **[http://localhost:8500](http://localhost:8500)**.

### Option 2: Running Locally with Python
1.  Navigate to the repository folder.
2.  Install dependencies:
    ```bash
    pip install fastapi uvicorn
    ```
3.  Execute the dashboard script:
    ```bash
    python dashboard_hicss.py
    ```
4.  Navigate to **[http://localhost:8500](http://localhost:8500)** in your web browser.

---

## 🎨 Dashboard Visual Layout & Features
The WebGL interface features:
- **Obsidian Graph View Aesthetic:** Dark theme plotting 10,000 app nodes, color-coded by motivational driver (🏆 Electric Cyan, 💬 Hot Pink, 🎮 Neon Orange, 🌱 Emerald Green).
- **Search-to-Focus Zoom:** Instantly locate any app (e.g., *Replika*, *Weis Markets*, *Calm*), auto-zooming to its coordinates and populating the details drawer.
- **Dynamic Metrics Mappings:** Displays the clicked app's installs, rating, reviews, genre, along with its specific **Primary Motivation**, **Emotional Payoff**, and **Success Metric** based on your comparison matrix!
