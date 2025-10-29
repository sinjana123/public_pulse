// Contact Form
document.getElementById('contact-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;
    const formMessage = document.getElementById('form-message');
    if (name && email && message) {
        formMessage.textContent = 'Thank you! Your feedback will help improve transparency.';
        formMessage.style.color = 'green';
        this.reset();
    } else {
        formMessage.textContent = 'Please fill all fields.';
        formMessage.style.color = 'red';
    }
});