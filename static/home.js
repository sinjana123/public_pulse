// Home Form: Validate email/phone and redirect to report.html
document.getElementById('home-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const email = document.getElementById('user-email').value;
    const phone = document.getElementById('user-phone').value;
    const message = document.getElementById('home-message');

    if (email && phone) {
        if (!email.includes('@') || !email.includes('.')) {
            message.textContent = 'Please enter a valid email address.';
            message.style.color = 'red';
            return;
        }
        if (!/^\d{10,}$/.test(phone.replace(/[-\s]/g, ''))) {
            message.textContent = 'Please enter a valid phone number (10+ digits).';
            message.style.color = 'red';
            return;
        }
        message.textContent = 'Details saved! Redirecting to report...';
        message.style.color = 'green';
        localStorage.setItem('user', JSON.stringify({ email, phone }));
        setTimeout(() => window.location.href = 'report.html', 1000);
        this.reset();
    } else {
        message.textContent = 'Please fill both email and phone fields.';
        message.style.color = 'red';
    }
});