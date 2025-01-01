// Toggle password visibility
function togglePasswordVisibility(inputElement, iconElement) {
  const isVisible = inputElement.type === "text";
  inputElement.type = isVisible ? "password" : "text";
  iconElement.classList.replace(
    isVisible ? "bi-eye-fill" : "bi-eye-slash-fill",
    isVisible ? "bi-eye-slash-fill" : "bi-eye-fill"
  );
}

document.querySelectorAll('.view-password').forEach(button => {
  button.addEventListener('click', (e) => {
    const inputId = button.getAttribute('data-target');
    const inputElement = document.getElementById(inputId);
    const iconElement = button.querySelector('i');
    if (inputElement && iconElement){
       togglePasswordVisibility(inputElement,iconElement)
    }
  })
});