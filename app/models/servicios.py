from sqlalchemy import Enum
from app import db

class Servicio(db.Model):
    __tablename__ = 'servicios'
    id_servicio = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    duracion = db.Column(db.Integer, nullable=False)  # Duración en minutos

    # Relaciones usando cadenas
    citas = db.relationship('Cita', backref='servicio', lazy=True)
    detalle_ventas = db.relationship('DetalleVenta', backref='servicio', lazy=True)
    promociones = db.relationship('Promocion', backref='servicio', lazy=True)
    reseñas = db.relationship('Reseña', backref='servicio', lazy=True)