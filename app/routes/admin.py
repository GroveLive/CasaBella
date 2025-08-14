from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.users import Usuario
from app.models.productos import Producto
from app.models.categorias import Categoria
from app.models.servicios import Servicio
from app.models.citas import Cita
from flask_login import login_required, current_user
import logging
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    usuarios_count = Usuario.query.count()
    productos_count = Producto.query.count()
    servicios_count = Servicio.query.count()
    citas_pendientes_count = Cita.query.filter_by(estado='pendiente').count()
    return render_template('dashboard_admin.html', usuarios_count=usuarios_count, productos_count=productos_count, servicios_count=servicios_count, citas_pendientes_count=citas_pendientes_count)

@bp.route('/gestion_usuarios')
@login_required
def gestion_usuarios():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    usuarios = Usuario.query.all()
    return render_template('gestion_usuarios.html', usuarios=usuarios)

@bp.route('/agregar_usuario', methods=['GET', 'POST'])
@login_required
def agregar_usuario():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        rol = request.form.get('rol')
        contraseña = request.form.get('contraseña')
        telefono = request.form.get('telefono')
        especialidad = request.form.get('especialidad')
        if not all([nombre, email, rol, contraseña]):
            flash("Los campos obligatorios (nombre, email, rol, contraseña) son requeridos.", "danger")
            return render_template('agregar_usuario.html')
        if rol == 'empleado' and not especialidad:
            flash("La especialidad es obligatoria para empleados.", "danger")
            return render_template('agregar_usuario.html')
        try:
            usuario = Usuario(
                nombre=nombre,
                email=email,
                contraseña=generate_password_hash(contraseña),
                rol=rol,
                telefono=telefono,
                especialidad=especialidad if rol == 'empleado' else None
            )
            db.session.add(usuario)
            db.session.commit()
            flash("Usuario agregado con éxito.", "success")
            return redirect(url_for('admin.gestion_usuarios'))
        except IntegrityError:
            db.session.rollback()
            flash("Error: El email ya está en uso.", "danger")
            return render_template('agregar_usuario.html')
    return render_template('agregar_usuario.html')

@bp.route('/editar_usuario/<int:id_usuario>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id_usuario):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.get_or_404(id_usuario)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        rol = request.form.get('rol')
        contraseña = request.form.get('contraseña')
        telefono = request.form.get('telefono')
        especialidad = request.form.get('especialidad')
        if not all([nombre, email, rol]):
            flash("Los campos obligatorios (nombre, email, rol) son requeridos.", "danger")
            return render_template('editar_usuario.html', usuario=usuario)
        if rol == 'empleado' and not especialidad:
            flash("La especialidad es obligatoria para empleados.", "danger")
            return render_template('editar_usuario.html', usuario=usuario)
        try:
            usuario.nombre = nombre
            usuario.email = email
            usuario.rol = rol
            if contraseña:
                usuario.contraseña = generate_password_hash(contraseña)
            usuario.telefono = telefono
            usuario.especialidad = especialidad if rol == 'empleado' else None
            db.session.commit()
            flash("Usuario actualizado con éxito.", "success")
            return redirect(url_for('admin.gestion_usuarios'))
        except IntegrityError:
            db.session.rollback()
            flash("Error: El email ya está en uso.", "danger")
            return render_template('editar_usuario.html', usuario=usuario)
    return render_template('editar_usuario.html', usuario=usuario)

@bp.route('/eliminar_usuario/<int:id_usuario>', methods=['GET', 'POST'])
@login_required
def eliminar_usuario(id_usuario):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    usuario = Usuario.query.get_or_404(id_usuario)
    if request.method == 'POST':
        try:
            db.session.delete(usuario)
            db.session.commit()
            flash("Usuario eliminado con éxito.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Error: No se pudo eliminar el usuario, puede estar en uso.", "danger")
        return redirect(url_for('admin.gestion_usuarios'))
    return render_template('eliminar_usuario.html', usuario=usuario)

@bp.route('/gestion_productos')
@login_required
def gestion_productos():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    productos = Producto.query.all()
    categorias = Categoria.query.all()
    return render_template('gestion_productos.html', productos=productos, categorias=categorias)

@bp.route('/agregar_producto', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        id_categoria = request.form.get('id_categoria')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        tipo = request.form.get('tipo')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        stock_minimo = request.form.get('stock_minimo')
        estado = request.form.get('estado')
        imagen_url = request.form.get('imagen_url')
        if not all([id_categoria, nombre, tipo, precio, stock]):
            flash("Los campos obligatorios (categoría, nombre, tipo, precio, stock) son requeridos.", "danger")
            return render_template('agregar_producto.html', producto=None, categorias=Categoria.query.all())
        try:
            precio = float(precio)
            stock = int(stock)
            stock_minimo = int(stock_minimo) if stock_minimo else 5
            if precio < 0 or stock < 0 or stock_minimo < 0:
                flash("El precio, stock y stock mínimo no pueden ser negativos.", "danger")
                return render_template('agregar_producto.html', producto=None, categorias=Categoria.query.all())
            producto = Producto(
                id_categoria=id_categoria,
                nombre=nombre,
                descripcion=descripcion,
                tipo=tipo,
                precio=precio,
                stock=stock,
                stock_minimo=stock_minimo,
                estado=estado if estado else 'activo',
                imagen_url=imagen_url
            )
            db.session.add(producto)
            db.session.commit()
            flash("Producto agregado con éxito.", "success")
            return redirect(url_for('admin.gestion_productos'))
        except ValueError:
            flash("El precio debe ser un número decimal y el stock/stock mínimo un número entero.", "danger")
            return render_template('agregar_producto.html', producto=None, categorias=Categoria.query.all())
        except IntegrityError:
            db.session.rollback()
            flash("Error: El producto ya existe o hay un problema de datos.", "danger")
            return render_template('agregar_producto.html', producto=None, categorias=Categoria.query.all())
    return render_template('agregar_producto.html', producto=None, categorias=Categoria.query.all())

@bp.route('/editar_producto/<int:id_producto>', methods=['GET', 'POST'])
@login_required
def editar_producto(id_producto):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    producto = Producto.query.get_or_404(id_producto)
    if request.method == 'POST':
        id_categoria = request.form.get('id_categoria')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        tipo = request.form.get('tipo')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        stock_minimo = request.form.get('stock_minimo')
        estado = request.form.get('estado')
        imagen_url = request.form.get('imagen_url')
        if not all([id_categoria, nombre, tipo, precio, stock]):
            flash("Los campos obligatorios (categoría, nombre, tipo, precio, stock) son requeridos.", "danger")
            return render_template('editar_producto.html', producto=producto, categorias=Categoria.query.all())
        try:
            precio = float(precio)
            stock = int(stock)
            stock_minimo = int(stock_minimo) if stock_minimo else producto.stock_minimo
            if precio < 0 or stock < 0 or stock_minimo < 0:
                flash("El precio, stock y stock mínimo no pueden ser negativos.", "danger")
                return render_template('editar_producto.html', producto=producto, categorias=Categoria.query.all())
            producto.id_categoria = id_categoria
            producto.nombre = nombre
            producto.descripcion = descripcion
            producto.tipo = tipo
            producto.precio = precio
            producto.stock = stock
            producto.stock_minimo = stock_minimo
            producto.estado = estado if estado else producto.estado
            producto.imagen_url = imagen_url
            db.session.commit()
            flash("Producto actualizado con éxito.", "success")
            return redirect(url_for('admin.gestion_productos'))
        except ValueError:
            flash("El precio debe ser un número decimal y el stock/stock mínimo un número entero.", "danger")
            return render_template('editar_producto.html', producto=producto, categorias=Categoria.query.all())
        except IntegrityError:
            db.session.rollback()
            flash("Error: No se pudo actualizar el producto.", "danger")
            return render_template('editar_producto.html', producto=producto, categorias=Categoria.query.all())
    return render_template('editar_producto.html', producto=producto, categorias=Categoria.query.all())

@bp.route('/eliminar_producto/<int:id_producto>', methods=['GET', 'POST'])
@login_required
def eliminar_producto(id_producto):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    producto = Producto.query.get_or_404(id_producto)
    if request.method == 'POST':
        try:
            db.session.delete(producto)
            db.session.commit()
            flash("Producto eliminado con éxito.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Error: No se pudo eliminar el producto, puede estar en uso.", "danger")
        return redirect(url_for('admin.gestion_productos'))
    return render_template('eliminar_producto.html', producto=producto)

@bp.route('/gestion_servicios')
@login_required
def gestion_servicios():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    servicios = Servicio.query.all()
    return render_template('gestion_servicios.html', servicios=servicios)

@bp.route('/agregar_servicio', methods=['GET', 'POST'])
@login_required
def agregar_servicio():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = request.form.get('precio')
        duracion = request.form.get('duracion')
        estado = request.form.get('estado')
        imagen_url = request.form.get('imagen_url')
        if not all([nombre, precio, duracion]):
            flash("Los campos obligatorios (nombre, precio, duración) son requeridos.", "danger")
            return render_template('agregar_servicio.html')
        try:
            precio = float(precio)
            duracion = int(duracion)
            if precio < 0 or duracion <= 0:
                flash("El precio no puede ser negativo y la duración debe ser mayor a 0.", "danger")
                return render_template('agregar_servicio.html')
            servicio = Servicio(
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                duracion=duracion,
                estado=estado if estado else 'activo',
                imagen_url=imagen_url
            )
            db.session.add(servicio)
            db.session.commit()
            flash("Servicio agregado con éxito.", "success")
            return redirect(url_for('admin.gestion_servicios'))
        except ValueError:
            flash("El precio debe ser un número decimal y la duración un número entero.", "danger")
            return render_template('agregar_servicio.html')
        except IntegrityError:
            db.session.rollback()
            flash("Error: Ya existe un servicio con ese nombre.", "danger")
            return render_template('agregar_servicio.html')
    return render_template('agregar_servicio.html')

@bp.route('/editar_servicio/<int:id_servicio>', methods=['GET', 'POST'])
@login_required
def editar_servicio(id_servicio):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    servicio = Servicio.query.get_or_404(id_servicio)
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = request.form.get('precio')
        duracion = request.form.get('duracion')
        estado = request.form.get('estado')
        imagen_url = request.form.get('imagen_url')
        if not all([nombre, precio, duracion]):
            flash("Los campos obligatorios (nombre, precio, duración) son requeridos.", "danger")
            return render_template('editar_servicio.html', servicio=servicio)
        try:
            precio = float(precio)
            duracion = int(duracion)
            if precio < 0 or duracion <= 0:
                flash("El precio no puede ser negativo y la duración debe ser mayor a 0.", "danger")
                return render_template('editar_servicio.html', servicio=servicio)
            servicio.nombre = nombre
            servicio.descripcion = descripcion
            servicio.precio = precio
            servicio.duracion = duracion
            servicio.estado = estado if estado else servicio.estado
            servicio.imagen_url = imagen_url
            db.session.commit()
            flash("Servicio actualizado con éxito.", "success")
            return redirect(url_for('admin.gestion_servicios'))
        except ValueError:
            flash("El precio debe ser un número decimal y la duración un número entero.", "danger")
            return render_template('editar_servicio.html', servicio=servicio)
        except IntegrityError:
            db.session.rollback()
            flash("Error: Ya existe un servicio con ese nombre.", "danger")
            return render_template('editar_servicio.html', servicio=servicio)
    return render_template('editar_servicio.html', servicio=servicio)

@bp.route('/eliminar_servicio/<int:id_servicio>', methods=['GET', 'POST'])
@login_required
def eliminar_servicio(id_servicio):
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
    servicio = Servicio.query.get_or_404(id_servicio)
    if request.method == 'POST':
        try:
            db.session.delete(servicio)
            db.session.commit()
            flash("Servicio eliminado con éxito.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Error: No se pudo eliminar el servicio, puede estar en uso.", "danger")
        return redirect(url_for('admin.gestion_servicios'))
    return render_template('eliminar_servicio.html', servicio=servicio)

@bp.route('/gestion_citas_pendientes')
@login_required
def gestion_citas_pendientes():
    if current_user.rol != 'admin':
        flash("Acceso denegado. Solo para administradores.", "danger")
        return redirect(url_for('auth.login'))
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
    from app.models.asignaciones import Asignacion
    cita = Cita.query.get_or_404(id_cita)
    if cita.estado != 'pendiente' or cita.id_empleado is not None:
        flash("Esta cita no puede ser asignada.", "danger")
        return redirect(url_for('admin.gestion_citas_pendientes'))
    id_empleado = request.form.get('id_empleado')
    notas = request.form.get('notas')
    if not id_empleado:
        flash("Debes seleccionar un empleado.", "danger")
        return redirect(url_for('admin.gestion_citas_pendientes'))
    asignacion = Asignacion(id_cita=id_cita, id_empleado=id_empleado, fecha_asignacion=datetime.now(), notas=notas)
    db.session.add(asignacion)
    cita.id_empleado = id_empleado
    db.session.commit()
    flash("Cita asignada con éxito.", "success")
    return redirect(url_for('admin.gestion_citas_pendientes'))