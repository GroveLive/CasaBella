from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.servicios import Servicio
from app.models.productos import Producto
from app.models.citas import Cita
from app.models.carrito import Carrito
from app.models.detalle_carrito import DetalleCarrito
from flask_login import login_required, current_user
import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime

bp = Blueprint('client', __name__, url_prefix='/client')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    try:
        logger.debug(f"Intentando agregar producto {producto_id} para usuario {current_user.id_usuario}")
        carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
        if not carrito:
            logger.debug(f"No se encontró carrito activo, creando nuevo para id_usuario={current_user.id_usuario}")
            carrito = Carrito(id_usuario=current_user.id_usuario, estado='activo')
            db.session.add(carrito)
            db.session.commit()
            carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()  # Refresca el objeto
        producto = Producto.query.get_or_404(producto_id)
        if producto.stock > 0:
            detalle = DetalleCarrito(carrito_id=carrito.id_carrito, producto_id=producto_id, cantidad=1, precio_unitario=producto.precio, id_servicio=None)
            db.session.add(detalle)
            db.session.commit()
            flash("Producto agregado al carrito.", "success")
        else:
            flash("No hay stock disponible.", "danger")
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Error de integridad al agregar al carrito: {str(e)} - Usuario: {current_user.id_usuario}, Producto: {producto_id}, Carrito: {carrito.id_carrito if carrito else 'None'}")
        flash("Error de integridad al agregar el producto. Verifica los datos e intenta de nuevo.", "danger")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al agregar al carrito: {str(e)} - Usuario: {current_user.id_usuario}, Producto: {producto_id}, Carrito: {carrito.id_carrito if carrito else 'None'}")
        flash("Ocurrió un error al agregar el producto al carrito. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.productos'))

@bp.route('/carrito')
@login_required
def carrito():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
    if not carrito:
        flash("No tienes un carrito activo.", "info")
    return render_template('carrito.html', carrito=carrito)

@bp.route('/reservar_cita', methods=['POST'])
@login_required
def reservar_cita():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicio_id = request.form.get('servicio_id')
    fecha_hora = request.form.get('fecha_hora')
    if not current_user.is_authenticated or not current_user.id_usuario:
        flash("Error: Usuario no autenticado correctamente.", "danger")
        return redirect(url_for('auth.login'))
    if not servicio_id or not fecha_hora:
        flash("Error al reservar la cita. Completa todos los campos.", "danger")
        return redirect(url_for('client.citas'))
    try:
        servicio_id = int(servicio_id)
        servicio = Servicio.query.get(servicio_id)
        if not servicio:
            flash("Servicio no encontrado.", "danger")
            return redirect(url_for('client.citas'))
        fecha_hora = fecha_hora.replace('T', ' ')
        fecha_hora = datetime.strptime(fecha_hora, '%Y-%m-%d %H:%M')
        cita = Cita(id_usuario=current_user.id_usuario, id_servicio=servicio_id, fecha_hora=fecha_hora, estado='pendiente', id_empleado=None)
        db.session.add(cita)
        db.session.commit()
        flash("Cita reservada con éxito. Te contactaremos para confirmación.", "success")
    except ValueError as e:
        logger.error(f"Error de formato en fecha_hora: {str(e)}")
        flash("Error: Formato de fecha inválido. Usa YYYY-MM-DD HH:MM.", "danger")
    except Exception as e:
        logger.error(f"Error al reservar cita: {str(e)}")
        flash("Ocurrió un error al reservar la cita. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.citas'))