from sqlalchemy import Enum
from app import db

class Pago(db.Model):
    __tablename__ = 'pagos'
    id_pago = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('ventas.id_venta'))
    metodo_pago = db.Column(Enum('efectivo', 'tarjeta', 'transferencia', name='metodo_pago_enum'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_pago = db.Column(db.DateTime, default=db.func.current_timestamp())
    estado = db.Column(Enum('completado', 'pendiente', name='estado_pago_enum'), default='completado')