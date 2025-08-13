from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.users import Usuario
from app.models.servicios import Servicio
from app.models.productos import Producto
from app.models.citas import Cita
from app.models.asignaciones import Asignacion
from flask_login import login_required, current_user
import logging
from datetime import datetime
from sqlalchemy.exc import IntegrityError

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
    return redirect(url_for('main.productos'))

@bp.route('/carrito')
@login_required
def carrito():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.carrito import Carrito
    from app.models.detalle_carrito import DetalleCarrito
    carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
    if not carrito:
        flash("No tienes un carrito activo.", "info")
    return render_template('carrito.html', carrito=carrito)

@bp.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.users import Usuario
    from app.models.productos import Producto
    from app.models.servicios import Servicio
    from app.models.citas import Cita
    usuarios_count = Usuario.query.count()
    productos_count = Producto.query.count()
    servicios_count = Servicio.query.count()
    citas_pendientes_count = Cita.query.filter_by(estado='pendiente').count()
    return render_template('dashboard_admin.html', usuarios_count=usuarios_count, productos_count=productos_count, servicios_count=servicios_count, citas_pendientes_count=citas_pendientes_count)

@bp.route('/empleado_dashboard')
@login_required
def empleado_dashboard():
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.citas import Cita
    citas_asignadas_count = Cita.query.filter_by(id_empleado=current_user.id_usuario, estado='pendiente').count()
    citas_pendientes_count = Cita.query.filter_by(estado='pendiente').count()
    return render_template('empleado_dashboard.html', citas_asignadas_count=citas_asignadas_count, citas_pendientes_count=citas_pendientes_count)

@bp.route('/gestion_usuarios')
@login_required
def gestion_usuarios():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.users import Usuario
    usuarios = Usuario.query.all()
    return render_template('gestion_usuarios.html', usuarios=usuarios)

@bp.route('/gestion_productos')
@login_required
def gestion_productos():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.productos import Producto
    productos = Producto.query.all()
    return render_template('gestion_productos.html', productos=productos)

@bp.route('/gestion_servicios')
@login_required
def gestion_servicios():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.servicios import Servicio
    servicios = Servicio.query.all()
    return render_template('gestion_servicios.html', servicios=servicios)

@bp.route('/gestion_citas_pendientes')
@login_required
def gestion_citas_pendientes():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.citas import Cita
    from app.models.users import Usuario
    from app.models.asignaciones import Asignacion
    citas_pendientes = Cita.query.filter_by(estado='pendiente').filter_by(id_empleado=None).all()
    empleados = Usuario.query.filter_by(rol='empleado').all()
    return render_template('gestion_citas_pendientes.html', citas_pendientes=citas_pendientes, empleados=empleados)

@bp.route('/asignar_empleado/<int:id_cita>', methods=['POST'])
@login_required
def asignar_empleado(id_cita):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.citas import Cita
    from app.models.asignaciones import Asignacion
    cita = Cita.query.get_or_404(id_cita)
    if cita.estado != 'pendiente' or cita.id_empleado is not None:
        flash("Esta cita no puede ser asignada.", "danger")
        return redirect(url_for('main.gestion_citas_pendientes'))
    id_empleado = request.form.get('id_empleado')
    notas = request.form.get('notas')
    if not id_empleado:
        flash("Debes seleccionar un empleado.", "danger")
        return redirect(url_for('main.gestion_citas_pendientes'))
    asignacion = Asignacion(id_cita=id_cita, id_empleado=id_empleado, fecha_asignacion=datetime.now(), notas=notas)
    db.session.add(asignacion)
    cita.id_empleado = id_empleado
    db.session.commit()
    flash("Cita asignada con éxito.", "success")
    return redirect(url_for('main.gestion_citas_pendientes'))

@bp.route('/trabajar_citas')
@login_required
def trabajar_citas():
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.citas import Cita
    citas = Cita.query.filter_by(id_empleado=current_user.id_usuario).order_by(Cita.fecha_hora).all()
    return render_template('trabajar_citas.html', citas=citas)

@bp.route('/confirmar_cita/<int:id_cita>', methods=['POST'])
@login_required
def confirmar_cita(id_cita):
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.citas import Cita
    cita = Cita.query.get_or_404(id_cita)
    if cita.id_empleado != current_user.id_usuario:
        flash("No tienes permiso para confirmar esta cita.", "danger")
        return redirect(url_for('main.trabajar_citas'))
    if cita.estado != 'pendiente':
        flash("Esta cita no puede ser confirmada.", "danger")
        return redirect(url_for('main.trabajar_citas'))
    cita.estado = 'confirmada'
    db.session.commit()
    flash("Cita confirmada con éxito.", "success")
    return redirect(url_for('main.trabajar_citas'))

@bp.route('/completar_cita/<int:id_cita>', methods=['POST'])
@login_required
def completar_cita(id_cita):
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    from app.models.citas import Cita
    cita = Cita.query.get_or_404(id_cita)
    if cita.id_empleado != current_user.id_usuario:
        flash("No tienes permiso para completar esta cita.", "danger")
        return redirect(url_for('main.trabajar_citas'))
    if cita.estado != 'confirmada':
        flash("Esta cita no puede ser completada. Debe estar confirmada primero.", "danger")
        return redirect(url_for('main.trabajar_citas'))
    cita.estado = 'completada'
    db.session.commit()
    flash("Cita completada con éxito.", "success")
    return redirect(url_for('main.trabajar_citas'))

@bp.route('/agregar_usuario')
@login_required
def agregar_usuario():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de agregar usuario en desarrollo.", "info")
    return redirect(url_for('main.gestion_usuarios'))

@bp.route('/editar_usuario/<int:id_usuario>')
@login_required
def editar_usuario(id_usuario):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de editar usuario en desarrollo.", "info")
    return redirect(url_for('main.gestion_usuarios'))

@bp.route('/eliminar_usuario/<int:id_usuario>')
@login_required
def eliminar_usuario(id_usuario):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de eliminar usuario en desarrollo.", "info")
    return redirect(url_for('main.gestion_usuarios'))

@bp.route('/agregar_producto')
@login_required
def agregar_producto():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de agregar producto en desarrollo.", "info")
    return redirect(url_for('main.gestion_productos'))

@bp.route('/editar_producto/<int:id_producto>')
@login_required
def editar_producto(id_producto):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de editar producto en desarrollo.", "info")
    return redirect(url_for('main.gestion_productos'))

@bp.route('/eliminar_producto/<int:id_producto>')
@login_required
def eliminar_producto(id_producto):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de eliminar producto en desarrollo.", "info")
    return redirect(url_for('main.gestion_productos'))

@bp.route('/agregar_servicio')
@login_required
def agregar_servicio():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de agregar servicio en desarrollo.", "info")
    return redirect(url_for('main.gestion_servicios'))

@bp.route('/editar_servicio/<int:id_servicio>')
@login_required
def editar_servicio(id_servicio):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de editar servicio en desarrollo.", "info")
    return redirect(url_for('main.gestion_servicios'))

@bp.route('/eliminar_servicio/<int:id_servicio>')
@login_required
def eliminar_servicio(id_servicio):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    flash("Función de eliminar servicio en desarrollo.", "info")
    return redirect(url_for('main.gestion_servicios'))

@bp.route('/gestion_citas')
@login_required
def gestion_citas():
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    return redirect(url_for('main.trabajar_citas'))

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
        return redirect(url_for('main.citas'))
    try:
        servicio_id = int(servicio_id)
        servicio = Servicio.query.get(servicio_id)
        if not servicio:
            flash("Servicio no encontrado.", "danger")
            return redirect(url_for('main.citas'))
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