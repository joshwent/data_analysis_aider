// Global state
let globalData = null;
let pyodide = null;

// Define common plot theme and layout settings
const PLOT_THEME = {
    template: 'plotly_dark',
    paper_bgcolor: '#2c3136',
    plot_bgcolor: '#2c3136',
    font: { color: '#ffffff' },
    height: 300,  // Fixed height
    margin: { t: 40, b: 50, l: 60, r: 40 },
    autosize: true
};

const PLOT_COLORS = {
    primary: '#7cb5ff',
    success: '#7cb5ff',
    danger: '#ff4d4d',
    warning: '#ffff00'
};

// Helper function to create plot layout with common theme
function createPlotLayout(title, xaxis = {}, yaxis = {}, additionalConfig = {}) {
    return {
        ...PLOT_THEME,
        title,
        xaxis: {
            gridcolor: '#404448',
            ...xaxis
        },
        yaxis: {
            gridcolor: '#404448',
            ...yaxis
        },
        ...additionalConfig
    };
}

// Data filtering
function getFilteredData() {
    if (!globalData) return [];
    
    const selectedOperators = [...document.querySelectorAll('#operator-checklist input:checked')]
        .map(cb => cb.value);
    const selectedGameTypes = [...document.querySelectorAll('#game-type-checklist input:checked')]
        .map(cb => cb.value);
    const selectedMaps = [...document.querySelectorAll('#map-checklist input:checked')]
        .map(cb => cb.value);
    
    const startDate = new Date(document.getElementById('date-start').value);
    const endDate = new Date(document.getElementById('date-end').value);
    
    return globalData.filter(d => {
        const date = new Date(d['UTC Timestamp']);
        return selectedOperators.includes(d.Operator) &&
               selectedGameTypes.includes(d['Game Type']) &&
               selectedMaps.includes(d.Map) &&
               date >= startDate &&
               date <= endDate;
    });
}

// Stats calculation and display
function updateStats() {
    const filteredData = getFilteredData();
    if (!filteredData.length) {
        document.getElementById('stats-container').innerHTML = 
            '<div class="alert alert-info">Select filters to display statistics</div>';
        return;
    }

    // Calculate lifetime stats
    const totalKills = globalData.reduce((sum, d) => sum + Number(d.Kills), 0);
    const totalDeaths = globalData.reduce((sum, d) => sum + Number(d.Deaths), 0);
    const lifetimeKD = (totalKills / totalDeaths).toFixed(2);
    const totalWins = globalData.filter(d => d['Match Outcome'].toLowerCase().includes('win')).length;
    const lifetimeWinRate = ((totalWins / globalData.length) * 100).toFixed(1);
    const totalShots = globalData.reduce((sum, d) => sum + Number(d.Shots), 0);
    const totalHits = globalData.reduce((sum, d) => sum + Number(d.Hits), 0);
    const lifetimeAccuracy = ((totalHits / totalShots) * 100).toFixed(1);
    
    // Calculate filtered stats
    const filteredKills = filteredData.reduce((sum, d) => sum + Number(d.Kills), 0);
    const filteredDeaths = filteredData.reduce((sum, d) => sum + Number(d.Deaths), 0);
    const filteredKD = (filteredKills / filteredDeaths).toFixed(2);
    const filteredWins = filteredData.filter(d => d['Match Outcome'].toLowerCase().includes('win')).length;
    const filteredWinRate = ((filteredWins / filteredData.length) * 100).toFixed(1);
    const avgSkill = (filteredData.reduce((sum, d) => sum + Number(d.Skill), 0) / filteredData.length).toFixed(0);
    const bestStreak = Math.max(...filteredData.map(d => Number(d['Longest Streak'])));

    // Create stats cards HTML
    const statsHtml = `
        <div class="row g-4 mb-4">
            <div class="col-12">
                <div class="card bg-dark">
                    <div class="card-body">
                        <h3 class="text-primary text-center mb-4">Lifetime Statistics</h3>
                        <div class="row text-center">
                            <div class="col-3">
                                <div class="mb-2"><strong>Total K/D</strong></div>
                                <div class="h4">${lifetimeKD}</div>
                            </div>
                            <div class="col-3">
                                <div class="mb-2"><strong>Overall Win Rate</strong></div>
                                <div class="h4">${lifetimeWinRate}%</div>
                            </div>
                            <div class="col-3">
                                <div class="mb-2"><strong>Lifetime Accuracy</strong></div>
                                <div class="h4">${lifetimeAccuracy}%</div>
                            </div>
                            <div class="col-3">
                                <div class="mb-2"><strong>Total Matches</strong></div>
                                <div class="h4">${globalData.length}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-12">
                <div class="card bg-dark">
                    <div class="card-body">
                        <h3 class="text-primary text-center mb-4">Filtered Performance</h3>
                        <div class="row text-center">
                            <div class="col-3">
                                <div class="mb-2"><strong>Avg Skill Rating</strong></div>
                                <div class="h4">${avgSkill}</div>
                            </div>
                            <div class="col-3">
                                <div class="mb-2"><strong>Filtered K/D</strong></div>
                                <div class="h4">${filteredKD}</div>
                            </div>
                            <div class="col-3">
                                <div class="mb-2"><strong>Win Rate</strong></div>
                                <div class="h4">${filteredWinRate}%</div>
                            </div>
                            <div class="col-3">
                                <div class="mb-2"><strong>Best Streak</strong></div>
                                <div class="h4">${bestStreak}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('stats-container').innerHTML = statsHtml;
}

// Plot creation and update
function updatePlots() {
    const filteredData = getFilteredData();
    if (!filteredData.length) {
        document.getElementById('plots-container').innerHTML = 
            '<div class="alert alert-info">Select filters to display charts</div>';
        return;
    }

    const plotsContainer = document.getElementById('plots-container');
    plotsContainer.innerHTML = ''; // Clear existing plots

    // Create plot containers
    const plotIds = [
        'skill-plot', 'kd-by-hour-plot', 'accuracy-hist', 'kd-hist',
        'skill-hist', 'metrics-plot', 'accuracy-time-plot', 'map-performance', 
        'headshot-plot', 'damage-plot', 'outcome-plot'
    ];

    plotIds.forEach(id => {
        const div = document.createElement('div');
        div.id = id;
        div.className = 'plot-container';
        plotsContainer.appendChild(div);
    });

    // Skill progression over time
    const skillData = {
        x: filteredData.map(d => d['UTC Timestamp']),
        y: filteredData.map(d => Number(d.Skill)),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#5B9AFF', width: 2 }
    };
    Plotly.newPlot('skill-plot', [skillData], createPlotLayout(
        'Skill Progression Over Time',
        { title: 'Time' },
        { title: 'Skill Rating', tickformat: 'd' }
    ));

    // KD ratio by hour
    const hourlyData = {};
    filteredData.forEach(d => {
        const hour = new Date(d['UTC Timestamp']).getHours();
        if (!hourlyData[hour]) hourlyData[hour] = { kills: 0, deaths: 0 };
        hourlyData[hour].kills += Number(d.Kills);
        hourlyData[hour].deaths += Number(d.Deaths);
    });

    const hourlyKD = Object.entries(hourlyData).map(([hour, data]) => ({
        hour: Number(hour),
        kd: data.deaths > 0 ? data.kills / data.deaths : data.kills
    })).sort((a, b) => a.hour - b.hour);

    Plotly.newPlot('kd-by-hour-plot', [{
        x: hourlyKD.map(d => `${d.hour}:00`),
        y: hourlyKD.map(d => d.kd),
        type: 'bar',
        marker: { color: PLOT_COLORS.primary }
    }], createPlotLayout('Average K/D Ratio by Hour'));

    // Accuracy distribution
    const accuracyData = filteredData.map(d => Number(d.Hits) / Number(d.Shots) * 100);
    Plotly.newPlot('accuracy-hist', [{
        x: accuracyData,
        type: 'histogram',
        nbinsx: 30,
        marker: { color: PLOT_COLORS.primary }
    }], createPlotLayout(
        'Accuracy Distribution',
        { title: 'Accuracy %' },
        { title: 'Number of Matches' }
    ));

    // K/D distribution
    const kdData = filteredData.map(d => Number(d.Kills) / Math.max(1, Number(d.Deaths)));
    Plotly.newPlot('kd-hist', [{
        x: kdData,
        type: 'histogram',
        nbinsx: 30,
        marker: { color: '#ff66b2' }  // Different color for this plot
    }], createPlotLayout(
        'K/D Ratio Distribution',
        { title: 'K/D Ratio' },
        { title: 'Number of Matches' }
    ));

    // Skill distribution
    Plotly.newPlot('skill-hist', [{
        x: filteredData.map(d => Number(d.Skill)),
        type: 'histogram',
        nbinsx: 30,
        marker: { color: '#00ffcc' }  // Different color for this plot
    }], createPlotLayout(
        'Skill Distribution',
        { title: 'Skill Rating' },
        { title: 'Number of Matches' }
    ));

    // K/D Ratio over time
    const kdTimeData = {
        x: filteredData.map(d => d['UTC Timestamp']),
        y: filteredData.map(d => Number(d.Kills) / Math.max(1, Number(d.Deaths))),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#5B9AFF', width: 2 }
    };
    Plotly.newPlot('metrics-plot', [kdTimeData], createPlotLayout(
        'K/D Ratio Over Time',
        { title: 'Time' },
        { title: 'K/D Ratio' }
    ));

    // Accuracy over time
    const accuracyTimeData = {
        x: filteredData.map(d => d['UTC Timestamp']),
        y: filteredData.map(d => (Number(d.Hits) / Math.max(1, Number(d.Shots))) * 100),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#00ff00', width: 2 }
    };
    Plotly.newPlot('accuracy-time-plot', [accuracyTimeData], createPlotLayout(
        'Accuracy Over Time',
        { title: 'Time' },
        { title: 'Accuracy %' }
    ));

    // Map performance
    const mapStats = {};
    filteredData.forEach(d => {
        if (!mapStats[d.Map]) mapStats[d.Map] = { kills: 0, deaths: 0 };
        mapStats[d.Map].kills += Number(d.Kills);
        mapStats[d.Map].deaths += Number(d.Deaths);
    });

    const mapKD = Object.entries(mapStats).map(([map, data]) => ({
        map,
        kd: data.kills / Math.max(1, data.deaths)
    })).sort((a, b) => b.kd - a.kd);

    Plotly.newPlot('map-performance', [{
        x: mapKD.map(d => d.map),
        y: mapKD.map(d => d.kd),
        type: 'bar',
        marker: { color: '#9966ff' }  // Different color for this plot
    }], createPlotLayout(
        'K/D Ratio by Map',
        { tickangle: 45 },
        {},
        { margin: { b: 100 } }  // Extra bottom margin for rotated labels
    ));

    // Headshot ratio over time
    const headshotData = {
        x: filteredData.map(d => d['UTC Timestamp']),
        y: filteredData.map(d => Number(d.Headshots) / Math.max(1, Number(d.Kills))),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#ff4d4d', width: 2 }
    };
    Plotly.newPlot('headshot-plot', [headshotData], createPlotLayout(
        'Headshot Ratio Over Time',
        {},
        { title: 'Headshot Ratio' }
    ));

    // Damage efficiency
    Plotly.newPlot('damage-plot', [{
        x: filteredData.map(d => Number(d['Damage Taken'])),
        y: filteredData.map(d => Number(d['Damage Done'])),
        mode: 'markers',
        type: 'scatter',
        marker: {
            color: filteredData.map(d => d['Match Outcome'].toLowerCase().includes('win') ? 
                PLOT_COLORS.success : PLOT_COLORS.danger),
            size: 8
        }
    }], createPlotLayout(
        'Damage Efficiency (Done vs Taken)',
        { title: 'Damage Taken' },
        { title: 'Damage Done' }
    ));

    // Match outcomes pie chart
    const outcomes = {};
    filteredData.forEach(d => {
        const outcome = d['Match Outcome'];
        outcomes[outcome] = (outcomes[outcome] || 0) + 1;
    });

    Plotly.newPlot('outcome-plot', [{
        values: Object.values(outcomes),
        labels: Object.keys(outcomes),
        type: 'pie',
        marker: {
            colors: [PLOT_COLORS.success, PLOT_COLORS.danger, PLOT_COLORS.warning]
        }
    }], createPlotLayout(
        'Match Outcomes Distribution',
        {},
        {},
        { showlegend: true }
    ));
}

// Utility functions
function showError(message) {
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = `<div class="alert alert-danger">${message}</div>`;
}

function showSuccess(message) {
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = `<div class="alert alert-success">${message}</div>`;
}

// File handling
async function handleFileUpload(file) {
    try {
        const content = await file.text();
        globalData = parseHtmlFile(content);
        console.log("Data loaded:", globalData.length, "records");
        
        updateFilters();
        updateStats();
        updatePlots();
        showSuccess("Data loaded successfully");
        
    } catch (error) {
        console.error("Error processing file:", error);
        showError("Error processing file: " + error.message);
    }
}

// Filter management
function updateFilters() {
    if (!globalData) return;
    
    // Get unique values
    const operators = [...new Set(globalData.map(d => d.Operator))].sort();
    const gameTypes = [...new Set(globalData.map(d => d['Game Type']))].sort();
    const maps = [...new Set(globalData.map(d => d.Map))].sort();
    
    // Update operator checklist
    const operatorList = document.getElementById('operator-checklist');
    operatorList.innerHTML = operators.map(op => `
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="${op}" id="op-${op}" checked>
            <label class="form-check-label" for="op-${op}">${op}</label>
        </div>
    `).join('');
    
    // Update game type checklist
    const gameTypeList = document.getElementById('game-type-checklist');
    gameTypeList.innerHTML = gameTypes.map(type => `
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="${type}" id="gt-${type}" checked>
            <label class="form-check-label" for="gt-${type}">${type}</label>
        </div>
    `).join('');
    
    // Update maps checklist
    const mapList = document.getElementById('map-checklist');
    mapList.innerHTML = maps.map(map => `
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="${map}" id="map-${map}" checked>
            <label class="form-check-label" for="map-${map}">${map}</label>
        </div>
    `).join('');
    
    // Update date range
    const dates = globalData.map(d => new Date(d['UTC Timestamp']));
    const minDate = new Date(Math.min(...dates));
    const maxDate = new Date(Math.max(...dates));
    
    document.getElementById('date-start').value = minDate.toISOString().split('T')[0];
    document.getElementById('date-end').value = maxDate.toISOString().split('T')[0];
}

// Event Listeners
// Add resize handler
function resizePlots() {
    const plots = document.querySelectorAll('.js-plotly-plot');
    plots.forEach(plot => {
        const update = {
            width: plot.parentElement.clientWidth
        };
        Plotly.relayout(plot, update);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    // Add window resize listener
    window.addEventListener('resize', resizePlots);
    // No initialization needed
    
    // Load example data button
    document.getElementById('load-example-data').addEventListener('click', async () => {
        try {
            const response = await fetch('https://raw.githubusercontent.com/joshwent/data_analysis_aider/refs/heads/non-dash2/data.html');
            const content = await response.text();
            globalData = parseHtmlFile(content);
            console.log("Example data loaded:", globalData.length, "records");
            
            updateFilters();
            updateStats();
            updatePlots();
            showSuccess("Example data loaded successfully");
            
        } catch (error) {
            console.error("Error loading example data:", error);
            showError("Error loading example data: " + error.message);
        }
    });
    
    // File upload handling
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFileUpload(file);
    });
    
    uploadZone.addEventListener('click', () => fileInput.click());
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });
    
    // Select/Deselect all buttons
    document.getElementById('operator-select-all').addEventListener('click', () => {
        document.querySelectorAll('#operator-checklist input[type="checkbox"]')
            .forEach(cb => cb.checked = true);
        updateStats();
        updatePlots();
    });
    
    document.getElementById('operator-deselect-all').addEventListener('click', () => {
        document.querySelectorAll('#operator-checklist input[type="checkbox"]')
            .forEach(cb => cb.checked = false);
        updateStats();
        updatePlots();
    });
    
    document.getElementById('game-type-select-all').addEventListener('click', () => {
        document.querySelectorAll('#game-type-checklist input[type="checkbox"]')
            .forEach(cb => cb.checked = true);
        updateStats();
        updatePlots();
    });
    
    document.getElementById('game-type-deselect-all').addEventListener('click', () => {
        document.querySelectorAll('#game-type-checklist input[type="checkbox"]')
            .forEach(cb => cb.checked = false);
        updateStats();
        updatePlots();
    });

    document.getElementById('map-select-all').addEventListener('click', () => {
        document.querySelectorAll('#map-checklist input[type="checkbox"]')
            .forEach(cb => cb.checked = true);
        updateStats();
        updatePlots();
    });
    
    document.getElementById('map-deselect-all').addEventListener('click', () => {
        document.querySelectorAll('#map-checklist input[type="checkbox"]')
            .forEach(cb => cb.checked = false);
        updateStats();
        updatePlots();
    });
    
    // Add change listeners for all filters
    ['operator-checklist', 'game-type-checklist', 'map-checklist'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            updateStats();
            updatePlots();
        });
    });

    // Date range listeners
    ['date-start', 'date-end'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            updateStats();
            updatePlots();
        });
    });
});
