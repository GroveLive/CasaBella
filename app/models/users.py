from flask_login import UserMixin
from sqlalchemy import Enum
from app import db

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    rol = db.Column(Enum('cliente', 'admin', 'empleado', name='role_enum'), nullable=False, default='cliente')
    telefono = db.Column(db.String(15))
    especialidad = db.Column(db.String(100))  # Para empleados
    fecha_registro = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relaciones usando cadenas
    citas_cliente = db.relationship('Cita', foreign_keys='Cita.id_usuario', backref='cliente', lazy=True)
    citas_empleado = db.relationship('Cita', foreign_keys='Cita.id_empleado', backref='empleado', lazy=True)
    ventas = db.relationship('Venta', backref='usuario', lazy=True)
    notificaciones = db.relationship('Notificacion', backref='usuario', lazy=True)
    reseñas = db.relationship('Reseña', backref='usuario', lazy=True)
    carritos = db.relationship('Carrito', backref='usuario', lazy=True)
    guardados = db.relationship('Guardado', backref='usuario', lazy=True)

    def get_id(self):
        return str(self.id_usuario)
