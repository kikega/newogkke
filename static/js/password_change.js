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
    buttonElement.setAttribute("aria-pressed", isVisible ? "false" : "true");
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

  const cambioPasswordDialog = document.getElementById("modalCambioPassword");
  const cambioPasswordForm = document.getElementById("cambioPassword");
  const password1 = document.getElementById("newPassword");
  const password2 = document.getElementById("newPasswordConf");
  const alertBox = document.getElementById("alertPassword");

  if (password2) {
    password2.addEventListener("input", () => {
      password2.setCustomValidity("");
      alertBox?.classList.add("d-none");
    });
  }

  if (cambioPasswordForm) {
    cambioPasswordForm.addEventListener("submit", (event) => {
      if (password1 && password2 && password1.value !== password2.value) {
        event.preventDefault();
        password2.setCustomValidity("Las contraseñas introducidas no coinciden.");
        alertBox?.classList.remove("d-none");
        password2.focus();
      } else {
        password2?.setCustomValidity("");
        alertBox?.classList.add("d-none");
      }
    });
  }

  if (cambioPasswordDialog) {
    cambioPasswordDialog.addEventListener("close", () => {
      cambioPasswordDialog.returnValue = "";
      cambioPasswordForm?.reset();
      password2?.setCustomValidity("");
      alertBox?.classList.add("d-none");
    });
  }
});
