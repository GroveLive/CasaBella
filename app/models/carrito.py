from sqlalchemy import Enum
from app import db

class Carrito(db.Model):
    __tablename__ = 'carrito'
    id_carrito = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())
    estado = db.Column(Enum('activo', 'completado', 'abandonado', name='estado_carrito_enum'), default='activo')

    # Relaciones usando cadenas
    detalles = db.relationship('DetalleCarrito', backref='carrito', lazy=True)
