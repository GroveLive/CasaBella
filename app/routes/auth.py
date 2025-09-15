from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.users import Usuario

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Usuario.query.filter_by(email=email).first()

        if user and check_password_hash(user.contraseña, password):
            login_user(user)
            flash("¡Login exitoso!", "success")

            if user.rol == 'admin':
                return redirect(url_for('auth.admin_dashboard'))
            elif user.rol == 'empleado':
                return redirect(url_for('auth.empleado_dashboard'))
            else:  # cliente
                return redirect(url_for('auth.cliente_dashboard'))
        else:
            flash("Credenciales incorrectas", "danger")

    return render_template("login.html")

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        telefono = request.form['telefono']
        especialidad = request.form.get('especialidad')

        if Usuario.query.filter_by(email=email).first():
            flash("Este correo ya está registrado.", "warning")
            return redirect(url_for('auth.register'))

        is_first_user = Usuario.query.count() == 0
        rol = 'admin' if is_first_user else 'cliente'

        hashed_password = generate_password_hash(password)
        user = Usuario(nombre=nombre, email=email, contraseña=hashed_password, rol=rol, telefono=telefono, especialidad=especialidad if rol == 'empleado' else None)

        try:
            db.session.add(user)
            db.session.commit()
            flash(f"¡Usuario registrado como {rol}!", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash("Error al registrar el usuario.", "danger")

    return render_template("register.html")

@bp.route('/dashboard/cliente')
@login_required
def cliente_dashboard():
    if current_user.rol != 'cliente':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('auth.login'))
    return render_template("dashboard_cliente.html", user=current_user, citas=current_user.citas_cliente, ventas=current_user.ventas, reseñas=current_user.reseñas, notificaciones=current_user.notificaciones)
@bp.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/dashboard/empleado')
@login_required
def empleado_dashboard():
    if current_user.rol != 'empleado':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('auth.login'))
    return render_template("dashboard_empleado.html", user=current_user)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for('auth.login'))