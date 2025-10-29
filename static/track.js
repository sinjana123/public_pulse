// Vote Form: Select and vote
document.getElementById('vote-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const title = document.getElementById('issue-select').value;
    const message = document.getElementById('vote-message');

    if (title) {
        vote(title);
        message.textContent = `Voted for "${title}"!`;
        message.style.color = 'green';
    } else {
        message.textContent = 'Please select an issue.';
        message.style.color = 'red';
    }
});

// Dashboard: Load issues into three checkbox sections
function loadDashboard() {
    const issues = JSON.parse(localStorage.getItem('issues') || '[]');
    issues.sort((a, b) => b.votes - a.votes); // Sort by votes (descending)

    // First Checkbox: Reported Issues List
    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = issues.map(issue => `
        <div class="issue-item ${issue.status === 'Resolved' ? 'resolved' : ''}">
            <input type="checkbox" id="issue-${issue.title}" onchange="resolve('${issue.title}', this.checked)">
            <label for="issue-${issue.title}">${issue.title} (${issue.votes} votes, ${issue.status})</label>
        </div>
    `).join('');

    // Second Checkbox: Select & Vote
    const select = document.getElementById('issue-select');
    select.innerHTML = '<option value="">Select an Issue</option>' + 
        issues.map(issue => `<option value="${issue.title}">${issue.title}</option>`).join('');

    // Third Checkbox: Most Voted Issue
    const mostVoted = document.getElementById('most-voted');
    const topIssue = issues[0];
    mostVoted.innerHTML = topIssue ? `
        <div class="issue-item">
            <input type="checkbox" id="top-issue" checked disabled>
            <label for="top-issue">${topIssue.title} (${topIssue.votes} votes, ${topIssue.status}) - Highest Priority</label>
        </div>
    ` : '<p>No issues reported yet.</p>';
}

// Voting function
function vote(title) {
    const issues = JSON.parse(localStorage.getItem('issues') || '[]');
    const issue = issues.find(i => i.title === title);
    if (issue) issue.votes++;
    localStorage.setItem('issues', JSON.stringify(issues));
    loadDashboard();
}

// Resolve function
function resolve(title, checked) {
    const issues = JSON.parse(localStorage.getItem('issues') || '[]');
    const issue = issues.find(i => i.title === title);
    if (issue) issue.status = checked ? 'Resolved' : 'Pending';
    localStorage.setItem('issues', JSON.stringify(issues));
    loadDashboard();
}

// Initial load with example data if empty
if (!localStorage.getItem('issues')) {
    const initialIssues = [
        { title: 'Pothole near school', desc: 'Large pothole causing accidents.', loc: '17.3850, 78.4867', votes: 25, status: 'Pending' },
        { title: 'Broken streetlight', desc: 'Streetlight out on Main St.', loc: '17.3851, 78.4868', votes: 10, status: 'In Progress' },
        { title: 'Garbage dumping area', desc: 'Illegal dumping near park.', loc: '17.3852, 78.4869', votes: 5, status: 'Pending' }
    ];
    localStorage.setItem('issues', JSON.stringify(initialIssues));
}
loadDashboard();