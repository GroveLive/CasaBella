
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;
    const navLogoImg = document.querySelector('.nav-logo-img');
    const footerLogoImg = document.querySelector('.logo-img');

    // Verificar tema almacenado o establecer modo oscuro por defecto
    const currentTheme = localStorage.getItem('theme') || 'dark';
    body.setAttribute('data-theme', currentTheme);
    updateLogos(currentTheme);

    // Alternar tema
    themeToggle.addEventListener('click', () => {
        const newTheme = body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Cambiar ícono del botón
        themeToggle.innerHTML = newTheme === 'dark' ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';

        // Actualizar logos
        updateLogos(newTheme);
    });

    // Función para actualizar los logos
    function updateLogos(theme) {
        navLogoImg.src = theme === 'dark'
            ? '{{ url_for("static", filename="images/casa-bella-nav-logo-dark.jpeg") }}'
            : '{{ url_for("static", filename="images/casa-bella-nav-logo-light.jpeg") }}';
        footerLogoImg.src = theme === 'dark'
            ? '{{ url_for("static", filename="images/casa-bella-logo-glam-dark.jpeg") }}'
            : '{{ url_for("static", filename="images/casa-bella-logo-glam-light.jpeg") }}';
    }
});
