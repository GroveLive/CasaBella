
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from werkzeug.security import generate_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.urandom(24)
    app.config.from_object('config.Config')

    try:
        db.init_app(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
    except Exception as e:
        print(f"Error al inicializar extensiones: {e}")
        raise

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.users import Usuario
        return Usuario.query.get(int(user_id))

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

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
        except Exception as e:
            print(f"Error al cargar modelos: {e}")
            raise

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8080)
