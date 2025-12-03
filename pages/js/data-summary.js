// Dark theme colors for Plotly
const plotlyLayout = {
    paper_bgcolor: '#161b22',
    plot_bgcolor: '#0d1117',
    font: {
        color: '#c9d1d9',
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
    },
    xaxis: {
        gridcolor: '#30363d',
        linecolor: '#30363d',
        tickfont: { color: '#8b949e' }
    },
    yaxis: {
        gridcolor: '#30363d',
        linecolor: '#30363d',
        tickfont: { color: '#8b949e' }
    },
    hoverlabel: {
        bgcolor: '#161b22',
        bordercolor: '#58a6ff',
        font: { color: '#c9d1d9' }
    }
};

const plotlyConfig = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
};

async function loadJSON(url) {
    try {
        console.log(`Fetching ${url}...`);
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
        }
        const data = await response.json();
        console.log(`Loaded ${url}`, data);
        return data;
    } catch (error) {
        console.error(`Error loading ${url}:`, error);
        throw error;
    }
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="error">${message}</div>`;
}

async function loadAndDisplayData() {
    try {
        console.log('Loading summary statistics...');
        
        // Load the pre-aggregated JSON files
        const [summaryStats, gamesByDate, skillDistribution] = await Promise.all([
            loadJSON('data/optimized/summary_stats.json'),
            loadJSON('data/optimized/summary_games_by_date.json'),
            loadJSON('data/optimized/summary_skill_distribution.json')
        ]);
        
        console.log('All data loaded successfully');
        console.log('Games by date:', gamesByDate);
        console.log('Skill distribution:', skillDistribution);
        
        // Display summary statistics
        document.getElementById('totalGames').textContent = summaryStats.total_games.toLocaleString();
        document.getElementById('totalPlayers').textContent = summaryStats.total_players.toLocaleString();
        document.getElementById('dateRange').textContent = `${summaryStats.date_range.min} to ${summaryStats.date_range.max}`;
        document.getElementById('avgSkill').textContent = summaryStats.avg_skill;
        
        // Create games over time chart
        const gamesTimeTrace = [{
            x: gamesByDate.dates,
            y: gamesByDate.games,
            type: 'bar',
            marker: {
                color: '#58a6ff',
                line: {
                    color: '#30363d',
                    width: 1
                }
            },
            hovertemplate: 'Date: %{x}<br>Games: %{y}<extra></extra>'
        }];
        
        const gamesTimeLayout = {
            ...plotlyLayout,
            title: {
                text: '',
                font: { color: '#c9d1d9' }
            },
            xaxis: {
                ...plotlyLayout.xaxis,
                title: 'Date',
                type: 'date'
            },
            yaxis: {
                ...plotlyLayout.yaxis,
                title: 'Number of Games'
            },
            margin: { t: 30, r: 30, b: 80, l: 60 }
        };
        
        // Clear loading spinner and create chart
        document.getElementById('gamesTimeChart').innerHTML = '';
        Plotly.newPlot('gamesTimeChart', gamesTimeTrace, gamesTimeLayout, plotlyConfig);
        console.log('Games over time chart created');
        
        // Create skill distribution chart
        const skillTrace = [{
            x: skillDistribution.skill_values,
            type: 'histogram',
            nbinsx: 50,
            marker: {
                color: '#58a6ff',
                line: {
                    color: '#30363d',
                    width: 1
                }
            },
            hovertemplate: 'Skill: %{x}<br>Players: %{y}<extra></extra>'
        }];
        
        const skillLayout = {
            ...plotlyLayout,
            title: {
                text: '',
                font: { color: '#c9d1d9' }
            },
            xaxis: {
                ...plotlyLayout.xaxis,
                title: 'Skill Rating (OpenSkill)'
            },
            yaxis: {
                ...plotlyLayout.yaxis,
                title: 'Number of Players'
            },
            margin: { t: 30, r: 30, b: 80, l: 60 }
        };
        
        // Clear loading spinner and create chart
        document.getElementById('skillDistChart').innerHTML = '';
        Plotly.newPlot('skillDistChart', skillTrace, skillLayout, plotlyConfig);
        console.log('Skill distribution chart created');
        
        console.log('All charts created successfully');
        
    } catch (error) {
        console.error('Error loading data:', error);
        showError('gamesTimeChart', `Error loading game distribution: ${error.message}`);
        showError('skillDistChart', `Error loading skill distribution: ${error.message}`);
    }
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadAndDisplayData();
});
