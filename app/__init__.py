from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from werkzeug.security import generate_password_hash

# Inicialización de extensiones fuera de la función create_app
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    # Creación de la aplicación
    app = Flask(__name__)

    # Configuración de la clave secreta y carga de configuración desde config.py
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config.from_object('config.Config')

    # Inicialización de extensiones con la aplicación
    try:
        db.init_app(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
    except Exception as e:
        print(f"Error al inicializar extensiones: {e}")
        raise

    # Carga del usuario para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.users import Usuario
        return Usuario.query.get(int(user_id))

    # Registro de blueprints
    from app.routes.home import bp as home_bp
    app.register_blueprint(home_bp, url_prefix='/')  # Página principal
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')  # Autenticación
    from app.routes.client import bp as client_bp
    app.register_blueprint(client_bp, url_prefix='/client')  # Cliente
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')  # Admin
    from app.routes.employee import bp as employee_bp
    app.register_blueprint(employee_bp, url_prefix='/employee')  # Empleado

    # Importación de modelos dentro del contexto de la aplicación
    with app.app_context():
        try:
            from app.models.users import Usuario
            from app.models.citas import Cita
            from app.models.servicios import Servicio
            from app.models.productos import Producto
            from app.models.ventas import Venta
            from app.models.detalle_ventas import DetalleVenta
            from app.models.notificaciones import Notificacion
            from app.models.inventario_movimientos import InventarioMovimiento
            from app.models.promociones import Promocion
            from app.models.reseñas import Reseña
            from app.models.pagos import Pago
            from app.models.categorias import Categoria
            from app.models.asignaciones import Asignacion
            from app.models.carrito import Carrito
            from app.models.detalle_carrito import DetalleCarrito
            from app.models.guardados import Guardado
        except Exception as e:
            print(f"Error al cargar modelos: {e}")
            raise

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)