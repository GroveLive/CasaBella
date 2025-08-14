from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from flask_login import login_required, current_user
import logging
from datetime import datetime

bp = Blueprint('home', __name__, url_prefix='/')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/contacto', methods=['POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form.get('name')
        telefono = request.form.get('phone')
        email = request.form.get('email')
        servicio = request.form.get('service')
        mensaje = request.form.get('message')
        # Aquí puedes guardar en la base de datos o enviar un email
        flash("Solicitud de contacto recibida. Te contactaremos pronto.", "success")
        return redirect(url_for('home.index'))
    return redirect(url_for('home.index'))  # Redirige si no es POST