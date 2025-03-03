document.addEventListener('DOMContentLoaded', () => {
    const extractBtn = document.getElementById('extractBtn');
    const responseContainer = document.getElementById('responseContainer');

    // Extract Data button event
    extractBtn.addEventListener('click', () => {
        // Add loading state
        extractBtn.disabled = true;
        extractBtn.style.opacity = '0.7';
        showMessage('Processing request...', 'success');

        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            const url = tabs[0].url;
            console.log('Extracted URL:', url);

            // Send request to local backend
            fetch('http://localhost:3000/api/endpoint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                showMessage('Successfully started extraction!', 'success');
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('Unable to fetch data. Please try again.', 'error');
            })
            .finally(() => {
                // Reset button state
                extractBtn.disabled = false;
                extractBtn.style.opacity = '1';
            });
        });
    });

    const icons = {
        success: '&#x2713;',
        error: '&#x26A0;'
    };

    // Function to show message
    function showMessage(message, type) {
        responseContainer.className = type;
        responseContainer.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 15px; line-height: 1;" aria-hidden="true">${icons[type]}</span>
                <span style="font-weight: 500; letter-spacing: -0.2px;">${message}</span>
            </div>
        `;
    }
});
