(function () {
  const dropzone = document.getElementById("dropzone");
  const inputArchivos = document.getElementById("input-archivos");
  const inputCarpeta = document.getElementById("input-carpeta");
  const btnCarpeta = document.getElementById("btn-carpeta");
  const lista = document.getElementById("dropzone-lista");

  if (!dropzone || !inputArchivos) return;

  const EXTENSIONES_VALIDAS = [".zip", ".pdf"];

  function tieneExtensionValida(nombre) {
    const nombreLower = nombre.toLowerCase();
    return EXTENSIONES_VALIDAS.some((ext) => nombreLower.endsWith(ext));
  }

  function mostrarNombres(files) {
    if (!files.length) {
      lista.textContent = "";
      return;
    }
    lista.textContent = Array.from(files).map((f) => f.name).join(", ");
  }

  function asignarArchivos(files) {
    const dt = new DataTransfer();
    let descartados = 0;

    Array.from(files).forEach((file) => {
      if (tieneExtensionValida(file.name)) {
        dt.items.add(file);
      } else {
        descartados++;
      }
    });

    inputArchivos.files = dt.files;
    mostrarNombres(dt.files);

    if (descartados > 0) {
      lista.textContent += ` (se ignoraron ${descartados} archivo(s) con extensión no permitida; la validación real ocurre en el servidor)`;
    }
  }

  dropzone.addEventListener("click", () => inputArchivos.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dropzone--activo");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dropzone--activo");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dropzone--activo");
    if (e.dataTransfer && e.dataTransfer.files.length) {
      asignarArchivos(e.dataTransfer.files);
    }
  });

  inputArchivos.addEventListener("change", () => {
    mostrarNombres(inputArchivos.files);
  });

  if (btnCarpeta && inputCarpeta) {
    btnCarpeta.addEventListener("click", (e) => {
      e.preventDefault();
      inputCarpeta.click();
    });

    inputCarpeta.addEventListener("change", () => {
      asignarArchivos(inputCarpeta.files);
    });
  }

  const turnstileEnvoltura = document.getElementById("turnstile-envoltura");
  const turnstileVerificado = document.getElementById("turnstile-verificado");

  window.onTurnstileVerificado = function () {
    if (turnstileEnvoltura) turnstileEnvoltura.hidden = true;
    if (turnstileVerificado) turnstileVerificado.hidden = false;
  };
})();
