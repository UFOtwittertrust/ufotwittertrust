// Populate trust rankings table
function populateRankingsTable(commId = null) {
    const tableBody = document.getElementById('rankingsTable');
    tableBody.innerHTML = '';
    
    // Update last updated timestamp
    document.getElementById('lastUpdated').textContent = trustData.lastUpdated;
    
    // Sort users by trust score
    const sortedUsers = [...trustData.users].sort((a, b) => b.trustScore - a.trustScore);
    
    let commScores = null;
    if (commId && trustData.communityTrustScores && trustData.communityTrustScores[commId]) {
        commScores = trustData.communityTrustScores[commId];
    }
    
    // Add each user to the table
    sortedUsers.forEach((user, index) => {
        const row = document.createElement('tr');
        row.dataset.username = user.username;
        
        // Add rank
        const rankCell = document.createElement('td');
        rankCell.textContent = index + 1;
        row.appendChild(rankCell);
        
        // Add username with link to Twitter
        const usernameCell = document.createElement('td');
        const usernameLink = document.createElement('a');
        usernameLink.href = `https://twitter.com/${user.username}`;
        usernameLink.target = '_blank';
        usernameLink.className = 'twitter-link';
        usernameLink.textContent = `@${user.username}`;
        usernameCell.appendChild(usernameLink);
        row.appendChild(usernameCell);
        
        // Add trust score
        const scoreCell = document.createElement('td');
        scoreCell.textContent = user.trustScore.toFixed(4);
        row.appendChild(scoreCell);
        
        if (commScores) {
            const commScoreCell = document.createElement('td');
            commScoreCell.textContent = (commScores[user.username] !== undefined) ? commScores[user.username].toFixed(4) : '-';
            row.appendChild(commScoreCell);
        }
        
        // Add number of trustors
        const trustorsCell = document.createElement('td');
        trustorsCell.textContent = user.trustors;
        row.appendChild(trustorsCell);
        
        // Add number of trustees
        const trusteesCell = document.createElement('td');
        trusteesCell.textContent = user.trustees;
        row.appendChild(trusteesCell);
        
        // Add row to table
        tableBody.appendChild(row);
        
        // Add click event to show user details
        row.addEventListener('click', () => {
            window.location.href = `network.html?user=${user.username}`;
        });
    });
    
    // Update table header
    const thead = document.querySelector('#rankingsTable').parentElement.querySelector('thead tr');
    if (thead) {
        // Remove old community column if present
        while (thead.children.length > 5) thead.removeChild(thead.lastChild);
        if (commScores) {
            const commHeader = document.createElement('th');
            commHeader.textContent = 'Community Trust Score';
            thead.insertBefore(commHeader, thead.children[3]);
        }
    }
}

// Search functionality
function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    
    searchInput.addEventListener('input', () => {
        const searchTerm = searchInput.value.toLowerCase();
        const rows = document.querySelectorAll('#rankingsTable tr');
        
        rows.forEach(row => {
            const username = row.dataset.username;
            if (!username) return;
            
            if (username.toLowerCase().includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

// Add community selector
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.card-header');
    if (!container) return;
    const label = document.createElement('label');
    label.textContent = 'View trust scores from community: ';
    label.setAttribute('for', 'communitySelect');
    label.style.marginRight = '8px';
    const select = document.createElement('select');
    select.id = 'communitySelect';
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.text = 'Global';
    select.appendChild(defaultOption);
    trustData.communities.forEach(comm => {
        const option = document.createElement('option');
        option.value = comm.id;
        option.text = comm.name;
        select.appendChild(option);
    });
    container.appendChild(label);
    container.appendChild(select);
    select.addEventListener('change', function() {
        populateRankingsTable(this.value);
    });
});

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    populateRankingsTable();
    setupSearch();
});