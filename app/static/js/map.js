// Inicializar el mapa
function initMap() {
    // Coordenadas aproximadas para Calle 5 4, Guavatá, Colombia
    const location = { lat: 5.9339, lng: -73.7174 };
    const map = new google.maps.Map(document.getElementById("map"), {
        center: location,
        zoom: 15, // Nivel de zoom inicial
        styles: [
            { elementType: "geometry", stylers: [{ color: "#f5f5f5" }] },
            { elementType: "labels.text.stroke", stylers: [{ color: "#ffffff" }] },
            { elementType: "labels.text.fill", stylers: [{ color: "#1e40af" }] },
            {
                featureType: "administrative.locality",
                elementType: "labels.text.fill",
                stylers: [{ color: "#1e40af" }]
            },
            {
                featureType: "poi",
                elementType: "labels.text.fill",
                stylers: [{ color: "#1e40af" }]
            },
            {
                featureType: "road",
                elementType: "geometry",
                stylers: [{ color: "#ffffff" }]
            },
            {
                featureType: "road",
                elementType: "labels.text.fill",
                stylers: [{ color: "#1e40af" }]
            }
        ] // Estilo personalizado para usar tu paleta azul
    });

    // Añadir un marcador
    new google.maps.Marker({
        position: location,
        map: map,
        title: "Casa Bella - Calle 5 4, Guavatá, Colombia"
    });
}

window.initMap = initMap; // Exponer initMap para que Google Maps lo llame