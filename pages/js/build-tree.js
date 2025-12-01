// Build Order Tree Explorer JavaScript

const positions = [
    'position_front-1',
    'position_front-2',
    'position_eco',
    'position_air',
    'position_geo',
    'position_geo-sea',
    'position_pond',
    'position_long-sea'
];

let currentData = null;

// Initialize position selector
function initPositionSelector() {
    const selector = document.getElementById('positionSelector');
    positions.forEach(pos => {
        const btn = document.createElement('button');
        btn.className = 'position-btn';
        btn.textContent = pos.replace('position_', '').replace(/-/g, ' ').toUpperCase();
        btn.onclick = () => loadPosition(pos);
        selector.appendChild(btn);
    });
}

// Load CSV data for a position
async function loadPosition(positionName) {
    try {
        // Update active button
        document.querySelectorAll('.position-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent === positionName.replace('position_', '').replace(/-/g, ' ').toUpperCase()) {
                btn.classList.add('active');
            }
        });
        
        const treeContainer = document.getElementById('treeContainer');
        treeContainer.innerHTML = '<div class="loading">Loading data...</div>';
        
        const response = await fetch(`output/position_csvs/${positionName}.csv`);
        if (!response.ok) {
            throw new Error(`Failed to load CSV file: ${response.statusText}`);
        }
        const csvText = await response.text();
        
        currentData = parseCSV(csvText);
        buildTree(currentData);
        showStats(currentData);
        
    } catch (error) {
        document.getElementById('treeContainer').innerHTML = 
            `<div class="error">Error loading data: ${error.message}</div>`;
    }
}

// Parse CSV data
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');
    
    const data = {
        players: [],
        builds: []
    };
    
    // Find player name row
    const playerNameRow = lines[1].split(',');
    
    // Parse each column (player)
    for (let col = 1; col < headers.length; col++) {
        const player = {
            id: headers[col],
            name: playerNameRow[col],
            skill: 0,
            builds: []
        };
        
        // Get player skill (row 4)
        const skillRow = lines[4].split(',');
        player.skill = parseFloat(skillRow[col]) || 0;
        
        // Get build orders (starting from row with "Build 1")
        let buildNum = 1;
        for (let row = 0; row < lines.length; row++) {
            if (lines[row].startsWith(`Build ${buildNum}`)) {
                const buildRow = lines[row].split(',');
                if (buildRow[col]) {
                    const buildItem = buildRow[col].trim();
                    if (buildItem && buildItem !== '---') {
                        // Extract item name (remove timestamp)
                        const match = buildItem.match(/^(.+?)\s*\(/);
                        if (match) {
                            player.builds.push(match[1].trim());
                        }
                    }
                }
                buildNum++;
            }
        }
        
        if (player.builds.length > 0) {
            data.players.push(player);
        }
    }
    
    return data;
}

// Combine consecutive same items into "x3" format
function combineConsecutive(items) {
    if (!items || items.length === 0) return [];
    
    const combined = [];
    let current = { name: items[0], count: 1 };
    
    for (let i = 1; i < items.length; i++) {
        if (items[i] === current.name) {
            current.count++;
        } else {
            combined.push(current);
            current = { name: items[i], count: 1 };
        }
    }
    combined.push(current);
    
    return combined;
}

// Build tree structure
function buildTree(data) {
    const tree = {};
    
    // Build tree from all players' build orders
    data.players.forEach(player => {
        const combined = combineConsecutive(player.builds);
        let currentNode = tree;
        
        combined.forEach((item, depth) => {
            const key = item.count > 1 ? `${item.name} x${item.count}` : item.name;
            
            if (!currentNode[key]) {
                currentNode[key] = {
                    name: key,
                    count: 0,
                    totalSkill: 0,
                    children: {}
                };
            }
            
            currentNode[key].count++;
            currentNode[key].totalSkill += player.skill;
            
            currentNode = currentNode[key].children;
        });
    });
    
    renderTree(tree);
}

// Render tree HTML
function renderTree(tree) {
    const container = document.getElementById('treeContainer');
    container.innerHTML = '';
    
    const rootNodes = Object.values(tree);
    if (rootNodes.length === 0) {
        container.innerHTML = '<div class="loading">No build data available</div>';
        return;
    }
    
    rootNodes.forEach(node => {
        container.appendChild(createNodeElement(node, 0));
    });
}

// Create a node element
function createNodeElement(node, depth) {
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'tree-node';
    
    const avgSkill = (node.totalSkill / node.count).toFixed(1);
    const hasChildren = Object.keys(node.children).length > 0;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'node-content';
    
    const expandIcon = document.createElement('span');
    expandIcon.className = 'expand-icon';
    expandIcon.textContent = hasChildren ? '▶' : '•';
    if (!hasChildren) expandIcon.classList.add('no-children');
    
    const itemName = document.createElement('span');
    itemName.className = 'item-name';
    itemName.textContent = node.name;
    
    const countBadge = document.createElement('span');
    countBadge.className = 'item-count';
    countBadge.textContent = `${node.count} players`;
    
    const skillBadge = document.createElement('span');
    skillBadge.className = 'item-skill';
    skillBadge.textContent = `Avg: ${avgSkill}`;
    
    contentDiv.appendChild(expandIcon);
    contentDiv.appendChild(itemName);
    contentDiv.appendChild(countBadge);
    contentDiv.appendChild(skillBadge);
    
    const childrenDiv = document.createElement('div');
    childrenDiv.className = 'children';
    
    if (hasChildren) {
        const childNodes = Object.values(node.children)
            .sort((a, b) => b.count - a.count); // Sort by count descending
        
        childNodes.forEach(child => {
            childrenDiv.appendChild(createNodeElement(child, depth + 1));
        });
        
        contentDiv.onclick = () => {
            childrenDiv.classList.toggle('expanded');
            expandIcon.textContent = childrenDiv.classList.contains('expanded') ? '▼' : '▶';
        };
    }
    
    nodeDiv.appendChild(contentDiv);
    nodeDiv.appendChild(childrenDiv);
    
    return nodeDiv;
}

// Show statistics
function showStats(data) {
    const statsContainer = document.getElementById('statsContainer');
    const statsContent = document.getElementById('statsContent');
    
    statsContainer.style.display = 'block';
    
    const totalPlayers = data.players.length;
    const avgSkill = (data.players.reduce((sum, p) => sum + p.skill, 0) / totalPlayers).toFixed(1);
    const maxSkill = Math.max(...data.players.map(p => p.skill)).toFixed(1);
    const minSkill = Math.min(...data.players.map(p => p.skill)).toFixed(1);
    
    // Get most common first build
    const firstBuilds = {};
    data.players.forEach(p => {
        if (p.builds.length > 0) {
            const first = p.builds[0];
            firstBuilds[first] = (firstBuilds[first] || 0) + 1;
        }
    });
    const mostCommon = Object.entries(firstBuilds)
        .sort((a, b) => b[1] - a[1])[0];
    
    let mostCommonHtml = '';
    if (mostCommon && mostCommon.length > 0) {
        mostCommonHtml = `<p><strong>Most Common First Build:</strong> ${mostCommon[0]} (${mostCommon[1]} players, ${(mostCommon[1]/totalPlayers*100).toFixed(1)}%)</p>`;
    }
    
    statsContent.innerHTML = `
        <p><strong>Total Players:</strong> ${totalPlayers}</p>
        <p><strong>Average Skill:</strong> ${avgSkill} (range: ${minSkill} - ${maxSkill})</p>
        ${mostCommonHtml}
    `;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initPositionSelector();
});
