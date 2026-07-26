async function auditURL() {
    const url = document.getElementById('url').value;
    const btn = document.getElementById('auditBtn');
    const btnText = document.getElementById('btnText');
    const result = document.getElementById('result');

    btn.disabled = true;
    btnText.innerHTML = '<span class="spinner"></span>Auditing...';
    result.style.display = 'none';

    try {
        const response = await fetch('/api/v1/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        result.className = 'result ' + (response.ok ? 'success' : 'error');
        document.getElementById('resultTitle').textContent = response.ok ? '✅ Audit Complete' : '❌ Audit Failed';
        document.getElementById('resultBody').textContent = JSON.stringify(data, null, 2);
        result.style.display = 'block';
    } catch (err) {
        result.className = 'result error';
        document.getElementById('resultTitle').textContent = '❌ Network Error';
        document.getElementById('resultBody').textContent = err.message;
        result.style.display = 'block';
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Audit URL';
    }
}

document.getElementById('url').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') auditURL();
});
