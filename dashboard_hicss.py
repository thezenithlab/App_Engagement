#!/usr/bin/env python3
"""
dashboard_hicss.py - Premium Interactive Web Dashboard for HICSS60 App Classification.
Renders an interactive 2D embedding scatter plot resembling Obsidian's Graph View.
Includes filters, real-time search, KPI stats cards, and academic framework guides.
"""

import os
import sqlite3
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIED_DB = os.path.join(BASE_DIR, "exports", "HICSS60_classified_apps.db")

app = FastAPI(title="HICSS60 App Psychographics Dashboard")

def get_db_connection():
    conn = sqlite3.connect(CLASSIFIED_DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/apps")
def get_apps():
    """Retrieve all apps with valid embedding coordinates for visualization."""
    if not os.path.exists(CLASSIFIED_DB):
        return {"error": "Database not generated yet. Please run the classification pipeline."}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch only apps that have valid coordinates (top 10,000 apps)
    cursor.execute("""
        SELECT OriginalID, title, genre, realInstalls, reviews, score, 
               psychographic_class, motivational_driver, embedding_x, embedding_y 
        FROM classified_apps 
        WHERE embedding_x IS NOT NULL AND embedding_y IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.get("/api/stats")
def get_stats():
    """Compute summary statistics for the classified catalog."""
    if not os.path.exists(CLASSIFIED_DB):
        return {"error": "Database not found"}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total counts
    cursor.execute("SELECT count(*) FROM classified_apps")
    total_apps = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM classified_apps WHERE embedding_x IS NOT NULL")
    visualized_apps = cursor.fetchone()[0]
    
    # Class distribution
    cursor.execute("SELECT psychographic_class, count(*) FROM classified_apps GROUP BY psychographic_class")
    class_dist = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Driver distribution
    cursor.execute("SELECT motivational_driver, count(*) FROM classified_apps GROUP BY motivational_driver")
    driver_dist = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Top installed apps by category
    top_apps = {}
    for driver in ["Achievement", "Connection", "Escape", "Growth"]:
        cursor.execute("""
            SELECT title, genre, realInstalls 
            FROM classified_apps 
            WHERE motivational_driver = ? 
            ORDER BY CAST(REPLACE(REPLACE(realInstalls, '+', ''), ',', '') AS INTEGER) DESC 
            LIMIT 5
        """, (driver,))
        top_apps[driver] = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    
    return {
        "total_apps": total_apps,
        "visualized_apps": visualized_apps,
        "class_distribution": class_dist,
        "driver_distribution": driver_dist,
        "top_apps": top_apps
    }

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Serve the premium interactive single-page dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HICSS60 App Classification Dashboard</title>
    <!-- Sleek Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <!-- Plotly.js for premium WebGL rendering -->
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    <style>
        :root {
            --bg-dark: #0b0f19;
            --bg-card: rgba(20, 26, 42, 0.65);
            --border-glass: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-achievement: #00f2fe;
            --accent-connection: #ff007f;
            --accent-escape: #ff9f43;
            --accent-growth: #00ff87;
            --accent-glow: rgba(0, 242, 254, 0.2);
            --font-display: 'Outfit', sans-serif;
            --font-sans: 'Inter', sans-serif;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: var(--font-sans);
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Ambient glowing circles */
        .glowing-bg {
            position: absolute;
            top: -10%;
            left: -10%;
            width: 50%;
            height: 50%;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(0, 242, 254, 0.08) 0%, rgba(0,0,0,0) 70%);
            filter: blur(100px);
            z-index: 0;
            pointer-events: none;
        }
        .glowing-bg-2 {
            position: absolute;
            bottom: -10%;
            right: -10%;
            width: 50%;
            height: 50%;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255, 0, 127, 0.05) 0%, rgba(0,0,0,0) 70%);
            filter: blur(100px);
            z-index: 0;
            pointer-events: none;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem 2rem;
            border-bottom: 1px solid var(--border-glass);
            background: rgba(11, 15, 25, 0.8);
            backdrop-filter: blur(16px);
            z-index: 10;
        }

        header h1 {
            font-family: var(--font-display);
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff 30%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        header h1 span {
            font-size: 0.75rem;
            font-weight: 500;
            padding: 0.15rem 0.5rem;
            border: 1px solid var(--accent-achievement);
            border-radius: 99px;
            color: var(--accent-achievement);
            margin-left: 0.5rem;
        }

        header .subtitle {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        main {
            display: flex;
            flex: 1;
            overflow: hidden;
            position: relative;
            z-index: 1;
        }

        /* Sidebar styling */
        .sidebar {
            width: 380px;
            border-right: 1px solid var(--border-glass);
            background: rgba(15, 22, 38, 0.6);
            backdrop-filter: blur(24px);
            padding: 1.5rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Dashboard panels */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .card h2 {
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 600;
            border-left: 3px solid var(--accent-achievement);
            padding-left: 0.5rem;
        }

        /* KPI stats columns */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 0.75rem;
            text-align: center;
        }

        .stat-val {
            font-family: var(--font-display);
            font-size: 1.4rem;
            font-weight: 700;
            color: #ffffff;
        }

        .stat-label {
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Dynamic category badges */
        .category-legend {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        .legend-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            padding: 0.4rem 0.6rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.02);
            border-left: 4px solid var(--border-color);
        }

        /* Custom inputs and search styling */
        .control-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .control-group label {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .search-input {
            width: 100%;
            background: rgba(15, 22, 38, 0.8);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            color: #ffffff;
            padding: 0.6rem 0.8rem;
            font-size: 0.9rem;
            font-family: var(--font-sans);
            transition: all 0.2s;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--accent-achievement);
            box-shadow: 0 0 10px var(--accent-glow);
        }

        .filter-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
        }

        .filter-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-glass);
            color: var(--text-secondary);
            padding: 0.4rem 0.75rem;
            font-size: 0.75rem;
            font-weight: 500;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
        }

        .filter-btn.active {
            background: var(--accent-color, var(--accent-achievement));
            border-color: var(--accent-color, var(--accent-achievement));
            color: #0b0f19;
            font-weight: 600;
        }

        /* Canvas section */
        .canvas-container {
            flex: 1;
            height: 100%;
            position: relative;
            background: radial-gradient(circle at center, #111827 0%, #070a13 100%);
        }

        #graph-view {
            width: 100%;
            height: 100%;
        }

        /* Interactive App Detail Sidebar Drawer */
        .detail-panel {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 320px;
            background: rgba(15, 22, 38, 0.85);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            z-index: 100;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            transition: opacity 0.3s, transform 0.3s;
            opacity: 0;
            transform: translateY(10px);
            pointer-events: none;
        }

        .detail-panel.visible {
            opacity: 1;
            transform: translateY(0);
            pointer-events: auto;
        }

        .detail-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .detail-title {
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
        }

        .detail-package {
            font-size: 0.7rem;
            color: var(--text-secondary);
            word-break: break-all;
        }

        .detail-badge {
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-achievement { background: rgba(0, 242, 254, 0.15); color: var(--accent-achievement); border: 1px solid var(--accent-achievement); }
        .badge-connection { background: rgba(255, 0, 127, 0.15); color: var(--accent-connection); border: 1px solid var(--accent-connection); }
        .badge-escape { background: rgba(255, 159, 67, 0.15); color: var(--accent-escape); border: 1px solid var(--accent-escape); }
        .badge-growth { background: rgba(0, 255, 135, 0.15); color: var(--accent-growth); border: 1px solid var(--accent-growth); }

        .detail-metric {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            padding: 0.3rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .detail-metric span:first-child {
            color: var(--text-secondary);
        }

        /* Obsidian aesthetic framing */
        .framework-block {
            font-size: 0.75rem;
            line-height: 1.4;
            color: var(--text-secondary);
            border-left: 2px solid rgba(255,255,255,0.15);
            padding-left: 0.5rem;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="glowing-bg"></div>
    <div class="glowing-bg-2"></div>

    <header>
        <div>
            <h1>HICSS60 App Engagement Matrix<span>HICSS-60 EXTENSION</span></h1>
            <div class="subtitle">Multi-Dimensional Mapping of 85,323 Apps: Psychographics & Motivational Drivers</div>
        </div>
        <div class="subtitle" style="text-align: right">
            Stationwork A100 Active | WebGL High-Density Scatter Graph
        </div>
    </header>

    <main>
        <!-- Sidebar Controls & Summaries -->
        <div class="sidebar">
            <!-- Framework & Theory Summary Card -->
            <div class="card">
                <h2>HCI Psychographics</h2>
                <div class="framework-block" style="margin-bottom: 0.5rem">
                    <strong>Hedonic Use (SELF):</strong> Leisure, pleasure, play, self-identity, relationships. Link to <em>Connection / Escape</em>.
                </div>
                <div class="framework-block">
                    <strong>Pragmatic Use (ACT):</strong> Extrinsic goals, task completion, efficiency. Link to <em>Achievement / Growth</em>.
                </div>
            </div>

            <!-- Motivational Drivers Matrix Card -->
            <div class="card">
                <h2>Motivational Drivers Matrix</h2>
                <div style="font-size: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.25rem;">
                    <div style="border-bottom: 1px solid var(--border-glass); padding-bottom: 0.4rem;">
                        <span style="color: var(--accent-achievement); font-weight: 600;">🏆 Achievement:</span>
                        <div style="color: var(--text-secondary); margin-top: 0.15rem; padding-left: 0.5rem;">
                            • Motivation: <strong>Efficiency</strong><br>
                            • Payoff: <strong>Relief / Control</strong><br>
                            • Success: <strong>Task Completion</strong>
                        </div>
                    </div>
                    <div style="border-bottom: 1px solid var(--border-glass); padding-bottom: 0.4rem;">
                        <span style="color: var(--accent-connection); font-weight: 600;">💬 Connection:</span>
                        <div style="color: var(--text-secondary); margin-top: 0.15rem; padding-left: 0.5rem;">
                            • Motivation: <strong>Belonging</strong><br>
                            • Payoff: <strong>Validation / Security</strong><br>
                            • Success: <strong>Interaction / Updates</strong>
                        </div>
                    </div>
                    <div style="border-bottom: 1px solid var(--border-glass); padding-bottom: 0.4rem;">
                        <span style="color: var(--accent-escape); font-weight: 600;">🎮 Escape:</span>
                        <div style="color: var(--text-secondary); margin-top: 0.15rem; padding-left: 0.5rem;">
                            • Motivation: <strong>Stimulation</strong><br>
                            • Payoff: <strong>Pleasure / Distraction</strong><br>
                            • Success: <strong>Time spent / "Flow"</strong>
                        </div>
                    </div>
                    <div>
                        <span style="color: var(--accent-growth); font-weight: 600;">🌱 Growth:</span>
                        <div style="color: var(--text-secondary); margin-top: 0.15rem; padding-left: 0.5rem;">
                            • Motivation: <strong>Competence</strong><br>
                            • Payoff: <strong>Pride / Mastery</strong><br>
                            • Success: <strong>Streak / New Skill</strong>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Search & Navigation -->
            <div class="card">
                <h2>Interactive Search</h2>
                <div class="control-group">
                    <label for="app-search">Search App Title</label>
                    <input type="text" id="app-search" class="search-input" placeholder="Type app name (e.g. Replika, Calm)..." oninput="searchApp()">
                </div>
            </div>

            <!-- Filter Controls -->
            <div class="card">
                <h2>Filter Map</h2>
                <div class="control-group">
                    <label>Psychographic Class</label>
                    <div class="filter-buttons" id="psych-filters">
                        <button class="filter-btn active" onclick="filterPsych('ALL', this)">All</button>
                        <button class="filter-btn" onclick="filterPsych('HEDONIC', this)">Hedonic (SELF)</button>
                        <button class="filter-btn" onclick="filterPsych('PRAGMATIC', this)">Pragmatic (ACT)</button>
                    </div>
                </div>
                <div class="control-group" style="margin-top: 0.5rem">
                    <label>Motivational Driver</label>
                    <div class="filter-buttons" id="driver-filters">
                        <button class="filter-btn active" onclick="filterDriver('ALL', this)">All</button>
                        <button class="filter-btn" style="--accent-color: var(--accent-achievement)" onclick="filterDriver('Achievement', this)">Achievement</button>
                        <button class="filter-btn" style="--accent-color: var(--accent-connection)" onclick="filterDriver('Connection', this)">Connection</button>
                        <button class="filter-btn" style="--accent-color: var(--accent-escape)" onclick="filterDriver('Escape', this)">Escape</button>
                        <button class="filter-btn" style="--accent-color: var(--accent-growth)" onclick="filterDriver('Growth', this)">Growth</button>
                    </div>
                </div>
            </div>

            <!-- KPI stats card -->
            <div class="card">
                <h2>App Catalog Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-val" id="stat-total">85,323</div>
                        <div class="stat-label">Total Catalog</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-val" id="stat-visualized">10,000</div>
                        <div class="stat-label">Visualized</div>
                    </div>
                </div>
                <div class="category-legend">
                    <div class="legend-item" style="--border-color: var(--accent-achievement)">
                        <span>🏆 Achievement</span>
                        <strong id="legend-ach">30,569</strong>
                    </div>
                    <div class="legend-item" style="--border-color: var(--accent-connection)">
                        <span>💬 Connection</span>
                        <strong id="legend-con">3,405</strong>
                    </div>
                    <div class="legend-item" style="--border-color: var(--accent-escape)">
                        <span>🎮 Escape</span>
                        <strong id="legend-esc">43,070</strong>
                    </div>
                    <div class="legend-item" style="--border-color: var(--accent-growth)">
                        <span>🌱 Growth</span>
                        <strong id="legend-gro">8,279</strong>
                    </div>
                </div>
            </div>
        </div>

        <!-- Semantic Canvas View -->
        <div class="canvas-container">
            <div id="graph-view"></div>

            <!-- App Details Sidebar Drawer -->
            <div class="detail-panel" id="detail-card">
                <div class="detail-header">
                    <div>
                        <div class="detail-title" id="det-title">Barstool Sports</div>
                        <div class="detail-package" id="det-package">com.DesignMenace.BarstoolSports</div>
                    </div>
                    <button onclick="closeDetails()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 1.1rem">&times;</button>
                </div>
                <div>
                    <span class="detail-badge badge-achievement" id="det-badge">Achievement</span>
                </div>
                <div style="margin-top: 0.5rem; display: flex; flex-direction: column; gap: 0.25rem">
                    <div class="detail-metric">
                        <span>Psychographic Class</span>
                        <span id="det-class" style="font-weight: 600">PRAGMATIC</span>
                    </div>
                    <div class="detail-metric">
                        <span>Genre</span>
                        <span id="det-genre">Entertainment</span>
                    </div>
                    <div class="detail-metric">
                        <span>Installs</span>
                        <span id="det-installs">100,000+</span>
                    </div>
                    <div class="detail-metric">
                        <span>Total Reviews</span>
                        <span id="det-reviews">2,002</span>
                    </div>
                    <div class="detail-metric">
                        <span>Average Score</span>
                        <span id="det-score">1.96</span>
                    </div>
                    <div class="detail-metric">
                        <span>Primary Motivation</span>
                        <span id="det-motivation" style="font-weight: 500">-</span>
                    </div>
                    <div class="detail-metric">
                        <span>Emotional Payoff</span>
                        <span id="det-payoff" style="font-weight: 500">-</span>
                    </div>
                    <div class="detail-metric">
                        <span>Success Metric</span>
                        <span id="det-success" style="font-weight: 500">-</span>
                    </div>
                </div>
                <div class="framework-block" id="det-theory">
                    Relies on intrinsic motivation and leisure/pleasure (HEDONIC). Re-mapped using local semantic embedding vectors.
                </div>
            </div>
        </div>
    </main>

    <script>
        let allApps = [];
        let filteredApps = [];
        let currentPsychFilter = 'ALL';
        let currentDriverFilter = 'ALL';
        let graphData = null;

        // Fetch apps and statistics on load
        window.addEventListener('DOMContentLoaded', () => {
            fetch('/api/stats')
                .then(r => r.json())
                .then(stats => {
                    if (stats.error) return;
                    document.getElementById('stat-total').textContent = stats.total_apps.toLocaleString();
                    document.getElementById('stat-visualized').textContent = stats.visualized_apps.toLocaleString();
                    document.getElementById('legend-ach').textContent = stats.driver_distribution.Achievement.toLocaleString();
                    document.getElementById('legend-con').textContent = stats.driver_distribution.Connection.toLocaleString();
                    document.getElementById('legend-esc').textContent = stats.driver_distribution.Escape.toLocaleString();
                    document.getElementById('legend-gro').textContent = stats.driver_distribution.Growth.toLocaleString();
                });

            fetch('/api/apps')
                .then(r => r.json())
                .then(data => {
                    allApps = data;
                    filteredApps = [...allApps];
                    renderGraph();
                });
        });

        // Filter handlers
        function filterPsych(val, btn) {
            // Update button active state
            document.querySelectorAll('#psych-filters .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPsychFilter = val;
            applyFilters();
        }

        function filterDriver(val, btn) {
            // Update button active state
            document.querySelectorAll('#driver-filters .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentDriverFilter = val;
            applyFilters();
        }

        function applyFilters() {
            filteredApps = allApps.filter(app => {
                const psychMatch = (currentPsychFilter === 'ALL') || (app.psychographic_class === currentPsychFilter);
                const driverMatch = (currentDriverFilter === 'ALL') || (app.motivational_driver === currentDriverFilter);
                return psychMatch && driverMatch;
            });
            updateGraph();
        }

        // Color mapper based on motivational driver
        function getDriverColor(driver) {
            switch(driver) {
                case 'Achievement': return '#00f2fe';
                case 'Connection': return '#ff007f';
                case 'Escape': return '#ff9f43';
                case 'Growth': return '#00ff87';
                default: return '#9ca3af';
            }
        }

        function renderGraph() {
            const container = document.getElementById('graph-view');
            
            // Map datasets for Plotly
            const x_vals = filteredApps.map(app => app.embedding_x);
            const y_vals = filteredApps.map(app => app.embedding_y);
            const colors = filteredApps.map(app => getDriverColor(app.motivational_driver));
            const hover_text = filteredApps.map(app => `<b>${app.title}</b><br>Genre: ${app.genre}<br>Installs: ${app.realInstalls}<br>Driver: ${app.motivational_driver}`);
            
            const trace = {
                x: x_vals,
                y: y_vals,
                mode: 'markers',
                type: 'scattergl', // High-performance WebGL
                marker: {
                    size: 6,
                    color: colors,
                    opacity: 0.75,
                    line: {
                        color: 'rgba(255,255,255,0.1)',
                        width: 0.5
                    }
                },
                text: hover_text,
                hoverinfo: 'text'
            };

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                showlegend: false,
                margin: { l: 0, r: 0, t: 0, b: 0 },
                xaxis: { showgrid: false, zeroline: false, showticklabels: false },
                yaxis: { showgrid: false, zeroline: false, showticklabels: false },
                hovermode: 'closest',
                dragmode: 'pan'
            };

            Plotly.newPlot('graph-view', [trace], layout, {
                responsive: true,
                displayModeBar: false,
                scrollZoom: true
            });

            // Bind click event
            container.on('plotly_click', (data) => {
                if (data.points && data.points[0]) {
                    const idx = data.points[0].pointNumber;
                    showAppDetails(filteredApps[idx]);
                }
            });
        }

        function updateGraph() {
            const x_vals = filteredApps.map(app => app.embedding_x);
            const y_vals = filteredApps.map(app => app.embedding_y);
            const colors = filteredApps.map(app => getDriverColor(app.motivational_driver));
            const hover_text = filteredApps.map(app => `<b>${app.title}</b><br>Genre: ${app.genre}<br>Installs: ${app.realInstalls}<br>Driver: ${app.motivational_driver}`);

            Plotly.restyle('graph-view', {
                x: [x_vals],
                y: [y_vals],
                'marker.color': [colors],
                text: [hover_text]
            });
        }

        function showAppDetails(app) {
            document.getElementById('det-title').textContent = app.title;
            document.getElementById('det-package').textContent = app.OriginalID;
            document.getElementById('det-class').textContent = app.psychographic_class;
            document.getElementById('det-genre').textContent = app.genre;
            document.getElementById('det-installs').textContent = app.realInstalls || "Unknown";
            document.getElementById('det-reviews').textContent = (app.reviews || 0).toLocaleString();
            document.getElementById('det-score').textContent = (app.score || 0).toFixed(2);
            
            // Badge style
            const badge = document.getElementById('det-badge');
            badge.textContent = app.motivational_driver;
            badge.className = `detail-badge badge-${app.motivational_driver.toLowerCase()}`;

            // Motivational driver subcategorization lookup (from user comparison matrix PNG)
            const driverDetails = {
                'Achievement': {
                    motivation: 'Efficiency',
                    payoff: 'Relief / Control',
                    success: 'Task Completion'
                },
                'Connection': {
                    motivation: 'Belonging',
                    payoff: 'Validation / Security',
                    success: 'Interaction / Updates'
                },
                'Escape': {
                    motivation: 'Stimulation',
                    payoff: 'Pleasure / Distraction',
                    success: 'Time spent / "Flow"'
                },
                'Growth': {
                    motivation: 'Competence',
                    payoff: 'Pride / Mastery',
                    success: 'Streak / New Skill'
                }
            };
            
            const driverInfo = driverDetails[app.motivational_driver] || { motivation: '-', payoff: '-', success: '-' };
            document.getElementById('det-motivation').textContent = driverInfo.motivation;
            document.getElementById('det-payoff').textContent = driverInfo.payoff;
            document.getElementById('det-success').textContent = driverInfo.success;
            
            // Framework explanation details
            let theoryText = "";
            if (app.psychographic_class === 'HEDONIC') {
                theoryText = `Classified as <strong>HEDONIC</strong> (SELF-type) driven by intrinsic leisure and psychological emotional payoff. Matches the <strong>${app.motivational_driver}</strong> motivational driver, typical of expressive, leisure, and recreational systems.`;
            } else {
                theoryText = `Classified as <strong>PRAGMATIC</strong> (ACT-type) driven by instrumental, extrinsically motivated goals. Matches the <strong>${app.motivational_driver}</strong> motivational driver, focusing on efficiency, utility, and target task completion.`;
            }
            document.getElementById('det-theory').innerHTML = theoryText;
            
            document.getElementById('detail-card').classList.add('visible');
        }

        function closeDetails() {
            document.getElementById('detail-card').classList.remove('visible');
        }

        // Live Search app node
        function searchApp() {
            const query = document.getElementById('app-search').value.toLowerCase().trim();
            if (!query) return;

            // Find the closest app matching query
            const match = filteredApps.find(app => app.title.toLowerCase().includes(query));
            if (match) {
                showAppDetails(match);
                
                // Zoom and pan Plotly to this node's coordinate
                const x_coord = match.embedding_x;
                const y_coord = match.embedding_y;
                
                Plotly.relayout('graph-view', {
                    'xaxis.range': [x_coord - 2, x_coord + 2],
                    'yaxis.range': [y_coord - 2, y_coord + 2]
                });
            }
        }
    </script>
</body>
</html>
"""
    return html_content

if __name__ == "__main__":
    print(f"Starting dashboard at http://localhost:8500")
    uvicorn.run(app, host="0.0.0.0", port=8500)
