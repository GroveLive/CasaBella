from app import db

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)

    # Relaciones usando cadenas
    productos = db.relationship('Producto', backref='categoria', lazy=True)