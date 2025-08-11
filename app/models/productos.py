from sqlalchemy import Enum
from app import db

class Producto(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.Integer, primary_key=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey('categorias.id_categoria'))
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(Enum('cosmético', 'joya', name='tipo_enum'), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    stock_minimo = db.Column(db.Integer, default=5)
    estado = db.Column(Enum('activo', 'inactivo', 'en_promocion', name='estado_producto_enum'), default='activo')
    imagen_url = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relaciones usando cadenas
    detalle_ventas = db.relationship('DetalleVenta', backref='producto', lazy=True)
    inventario_movimientos = db.relationship('InventarioMovimiento', backref='producto', lazy=True)
    promociones = db.relationship('Promocion', backref='producto', lazy=True)
    reseñas = db.relationship('Reseña', backref='producto', lazy=True)
    detalle_carritos = db.relationship('DetalleCarrito', backref='producto', lazy=True)
    guardados = db.relationship('Guardado', backref='producto', lazy=True)