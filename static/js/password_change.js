// Alternar visibilidad de campos de contraseña de forma accesible
function togglePasswordVisibility(inputElement, iconElement, buttonElement) {
  const isVisible = inputElement.type === "text";
  inputElement.type = isVisible ? "password" : "text";
  iconElement.classList.replace(
    isVisible ? "bi-eye-fill" : "bi-eye-slash-fill",
    isVisible ? "bi-eye-slash-fill" : "bi-eye-fill"
  );
  if (buttonElement) {
    buttonElement.setAttribute(
      "aria-label",
      isVisible ? "Mostrar contraseña" : "Ocultar contraseña"
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".view-password").forEach((button) => {
    button.addEventListener("click", () => {
      const inputId = button.getAttribute("data-target");
      const inputElement = document.getElementById(inputId);
      const iconElement = button.querySelector("i");
      if (inputElement && iconElement) {
        togglePasswordVisibility(inputElement, iconElement, button);
      }
    });
  });

  const cambioPasswordForm = document.getElementById("cambioPassword");
  if (cambioPasswordForm) {
    cambioPasswordForm.addEventListener("submit", function (event) {
      const password1 = document.getElementById("newPassword");
      const password2 = document.getElementById("newPasswordConf");
      const alertBox = document.getElementById("alertPassword");

      if (password1 && password2 && password1.value !== password2.value) {
        event.preventDefault();
        alertBox?.classList.remove("d-none");
        password2.classList.add("is-invalid");
        password2.focus();
      } else {
        alertBox?.classList.add("d-none");
        password2?.classList.remove("is-invalid");
      }
    });
  }
});
