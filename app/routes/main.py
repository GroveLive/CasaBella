from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.servicios import Servicio
from app.models.productos import Producto
from app.models.citas import Cita
from flask_login import login_required, current_user
import logging

bp = Blueprint('main', __name__)

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/servicios')
@login_required
def servicios():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicios = Servicio.query.all()
    return render_template('servicios.html', servicios=servicios)

@bp.route('/productos')
@login_required
def productos():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)

@bp.route('/citas')
@login_required
def citas():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicio_id = request.args.get('servicio_id')
    servicios = Servicio.query.all()
    return render_template('citas.html', servicios=servicios, servicio_id=servicio_id)

@bp.route('/agregar_carrito/<int:producto_id>', methods=['GET'])
@login_required
def agregar_carrito(producto_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.carrito import Carrito
    from app.models.detalle_carrito import DetalleCarrito
    from app.models.productos import Producto
    carrito = Carrito.query.filter_by(cliente_id=current_user.id_usuario, estado='activo').first()
    if not carrito:
        carrito = Carrito(cliente_id=current_user.id_usuario, estado='activo')
        db.session.add(carrito)
        db.session.commit()
    producto = Producto.query.get_or_404(producto_id)
    if producto.stock > 0:
        detalle = DetalleCarrito(carrito_id=carrito.id_carrito, producto_id=producto_id, cantidad=1)
        db.session.add(detalle)
        db.session.commit()
        flash("Producto agregado al carrito.", "success")
    else:
        flash("No hay stock disponible.", "danger")
    return redirect(url_for('main.productos'))

@bp.route('/reservar_cita', methods=['POST'])
@login_required
def reservar_cita():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicio_id = request.form.get('servicio_id')
    fecha_hora = request.form.get('fecha_hora')
    if servicio_id and fecha_hora:
        cita = Cita(cliente_id=current_user.id_usuario, servicio_id=servicio_id, fecha_hora=fecha_hora, estado='pendiente')
        db.session.add(cita)
        db.session.commit()
        flash("Cita reservada con éxito. Te contactaremos para confirmación.", "success")
    else:
        flash("Error al reservar la cita. Completa todos los campos.", "danger")
    return redirect(url_for('main.citas'))

@bp.route('/contacto', methods=['POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form.get('name')
        telefono = request.form.get('phone')
        email = request.form.get('email')
        servicio = request.form.get('service')
        mensaje = request.form.get('message')
        # Aquí puedes guardar en la base de datos o enviar un email
        flash("Solicitud de contacto recibida. Te contactaremos pronto.", "success")
        return redirect(url_for('main.index'))
    return redirect(url_for('main.index'))  # Redirige si no es POST