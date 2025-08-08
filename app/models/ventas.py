from app import db

class Venta(db.Model):
    __tablename__ = 'ventas'
    id_venta = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    fecha_venta = db.Column(db.DateTime, default=db.func.current_timestamp())
    total = db.Column(db.Numeric(10, 2), nullable=False)

    # Relaciones usando cadenas
    detalle_ventas = db.relationship('DetalleVenta', backref='venta', lazy=True)
    pagos = db.relationship('Pago', backref='venta', lazy=True)
