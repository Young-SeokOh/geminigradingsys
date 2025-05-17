document.getElementById('upload-form').onsubmit = async (e) => {
  e.preventDefault();
  
  const form = document.getElementById('upload-form');
  const submitButton = form.querySelector('button[type="submit"]');
  const resultDiv = document.getElementById('result');
  const resultContentDiv = document.getElementById('result-content');
  const loadingDiv = document.getElementById('loading');
  
  try {
    // Disable submit button and show loading
    submitButton.disabled = true;
    loadingDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    
    // Get form elements
    const problemFile = document.getElementById('problem').files[0];
    const imageFile = document.getElementById('image').files[0];
    const rubricFile = document.getElementById('rubric').files[0];
    const customRubric = document.getElementById('custom-rubric').value;
    
    // Validate files
    if (!problemFile) {
      throw new Error('문제 PDF 파일을 업로드해주세요.');
    }
    
    if (!imageFile) {
      throw new Error('학생 답안 이미지를 업로드해주세요.');
    }
    
    if (!rubricFile && !customRubric) {
      throw new Error('채점 루브릭 PDF를 업로드하거나 직접 입력해주세요.');
    }
    
    // Create FormData for server
    const formData = new FormData();
    formData.append('problem', problemFile);
    formData.append('image', imageFile);
    if (rubricFile) {
      formData.append('rubric', rubricFile);
    }
    formData.append('custom_rubric', customRubric);
    
    // Send to server
    const response = await fetch('/evaluate', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`서버 오류 (${response.status}): ${errorText}`);
    }
    
    const resultText = await response.text();
    resultContentDiv.innerHTML = resultText.replace(/\n/g, '<br>');
    resultDiv.style.display = 'block';
    
  } catch (error) {
    console.error('Error:', error);
    resultContentDiv.innerHTML = `오류가 발생했습니다: ${error.message}`;
    resultDiv.style.display = 'block';
    resultDiv.classList.add('error');
  } finally {
    // Re-enable submit button and hide loading
    submitButton.disabled = false;
    loadingDiv.style.display = 'none';
  }
};
