document.getElementById('upload-form').onsubmit = async (e) => {
  e.preventDefault();
  
  const form = document.getElementById('upload-form');
  const submitButton = form.querySelector('button[type="submit"]');
  const resultDiv = document.getElementById('result');
  const loadingDiv = document.getElementById('loading');
  
  try {
    // Disable submit button and show loading
    submitButton.disabled = true;
    loadingDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    
    const formData = new FormData(form);

    const response = await fetch('/evaluate', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const resultText = await response.text();
    resultDiv.innerHTML = resultText.replace(/\n/g, '<br>');
    resultDiv.style.display = 'block';
  } catch (error) {
    console.error('Error:', error);
    resultDiv.innerHTML = `오류가 발생했습니다: ${error.message}`;
    resultDiv.style.display = 'block';
    resultDiv.classList.add('error');
  } finally {
    // Re-enable submit button and hide loading
    submitButton.disabled = false;
    loadingDiv.style.display = 'none';
  }
};
