// Report Form: Mock submission with verification
document.getElementById('report-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const title = document.getElementById('issue-title').value;
    const desc = document.getElementById('description').value;
    const photo = document.getElementById('photo-upload').files[0];
    const loc = document.getElementById('location').value;
    const message = document.getElementById('report-message');

    if (title && desc && loc && (photo || true)) {
        const verified = Math.random() > 0.3 ? 'Verified (Automated Check)' : 'Pending';
        message.textContent = `Report "${title}" submitted! Status: ${verified}. Track below.`;
        message.style.color = 'green';

        const issues = JSON.parse(localStorage.getItem('issues') || '[]');
        issues.push({ title, desc, loc, votes: 0, status: 'Pending' });
        localStorage.setItem('issues', JSON.stringify(issues));

        this.reset();
        setTimeout(() => window.location.href = 'track.html', 1000);
    } else {
        message.textContent = 'Please provide title, description, and location.';
        message.style.color = 'red';
    }
});

// GPS Integration for Report Form
document.getElementById('get-location').addEventListener('click', function() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            document.getElementById('location').value = `${position.coords.latitude}, ${position.coords.longitude}`;
        }, function() {
            document.getElementById('location').value = 'Location access denied';
        });
    } else {
        document.getElementById('location').value = 'GPS not supported';
    }
});