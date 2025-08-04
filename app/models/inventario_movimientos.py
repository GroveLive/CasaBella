from sqlalchemy import Enum
from app import db

class InventarioMovimiento(db.Model):
    __tablename__ = 'inventario_movimientos'
    id_movimiento = db.Column(db.Integer, primary_key=True)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    tipo_movimiento = db.Column(Enum('entrada', 'salida', name='tipo_movimiento_enum'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=db.func.current_timestamp())
    motivo = db.Column(db.String(255))