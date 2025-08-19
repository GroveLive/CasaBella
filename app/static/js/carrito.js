// static/js/carrito.js

// Función para eliminar un item del carrito usando AJAX
function eliminarItem(detalleId) {
    if (confirm('¿Estás seguro de que deseas eliminar este item del carrito?')) {
        fetch(`/client/eliminar_del_carrito/${detalleId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Error al eliminar el item');
        })
        .then(data => {
            if (data.success) {
                const row = document.querySelector(`tr[data-detalle-id="${detalleId}"]`);
                if (row) row.remove();
                alert('Item eliminado del carrito.');
                // Actualizar el total si es necesario
                actualizarTotal();
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ocurrió un error al eliminar el item. Por favor, intenta de nuevo.');
        });
    }
}

// Función para actualizar la cantidad de un item (a implementar si lo deseas)
function actualizarCantidad(detalleId, nuevaCantidad) {
    fetch(`/client/actualizar_cantidad/${detalleId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify({ cantidad: nuevaCantidad })
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Error al actualizar la cantidad');
    })
    .then(data => {
        if (data.success) {
            const row = document.querySelector(`tr[data-detalle-id="${detalleId}"]`);
            if (row) {
                row.querySelector('td:nth-child(2)').textContent = nuevaCantidad; // Actualizar cantidad
                row.querySelector('td:nth-child(4)').textContent = `$${data.subtotal.toFixed(2)}`; // Actualizar subtotal
                actualizarTotal();
            }
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Ocurrió un error al actualizar la cantidad. Por favor, intenta de nuevo.');
    });
}

// Función para actualizar el total (simplificada)
function actualizarTotal() {
    const subtotales = document.querySelectorAll('td:nth-child(4)');
    let total = 0;
    subtotales.forEach(subtotal => {
        total += parseFloat(subtotal.textContent.replace('$', ''));
    });
    document.querySelector('tfoot td:nth-child(2)').textContent = `$${total.toFixed(2)}`;
}

// Escuchar eventos (ejemplo para cantidades, a implementar en HTML)
document.addEventListener('DOMContentLoaded', () => {
    // Ejemplo: agregar evento para inputs de cantidad si los añades
    // document.querySelectorAll('.cantidad-input').forEach(input => {
    //     input.addEventListener('change', (e) => {
    //         actualizarCantidad(input.dataset.detalleId, e.target.value);
    //     });
    // });
});