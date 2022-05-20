import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import jwt
from utils import contiene_caracteres_ilegales, contiene_letras, es_precio

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root@localhost/curso'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

jwt_secret = "basilio"

db = SQLAlchemy(app)
ma = Marshmallow(app)

'''
    Clases y Schemas
'''

class Usuario(db.Model):
    id_usuario = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    nombre = db.Column(db.String(100))
    password = db.Column(db.String(100))
    rol = db.Column(db.String(50))

    def __init__(self,email,nombre,password,rol):
        self.email = email
        self.nombre = nombre
        self.password = password
        self.rol = rol

    def __repr__(self):
        return '<Usuario %u>' % self.nombre

class Habitacion(db.Model):
    id_habitacion = db.Column(db.Integer, primary_key=True)
    nro_habitacion = db.Column(db.Integer, unique=True)
    descripcion = db.Column(db.String(150))
    precio_por_dia = db.Column(db.Float)
    estado = db.Column(db.String(100))

    def __init__(self, nro_habitacion, descripcion, precio_por_dia, estado):
        self.nro_habitacion = nro_habitacion
        self.descripcion = descripcion
        self.precio_por_dia = precio_por_dia
        self.estado = estado

    def __repr__(self):
        return '<Habitacion %h>' % self.nro_habitacion

class Reserva(db.Model):
    id_reserva = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer)
    id_habitacion = db.Column(db.Integer)
    fecha_reserva = db.Column(db.DateTime)

    def __init__(self, id_cliente, id_habitacion, fecha_reserva):
        self.id_cliente = id_cliente
        self.id_habitacion = id_habitacion
        self.fecha_reserva = fecha_reserva

    def __repr__(self):
        return '<Reserva %r' % self.fecha_reserva

db.create_all()

class UsuarioSchema(ma.Schema):
    class Meta:
        fields = ('id','email','nombre','password','rol')

usuario_schema = UsuarioSchema()
usuarios_schema = UsuarioSchema()

'''
    End clases y schemas
'''

def authenticate(ruta):
    def wrapper(*args, **kwargs):
        try:
            token = request.headers['Auth']
            contenido = jwt.decode(token,jwt_secret,algorithms=["HS256"])
            return ruta(*args, **kwargs)
        except jwt.DecodeError:
            return {"error": "Error al decodificar"}
        except jwt.InvalidTokenError:
            return {"error": "Token invalido"}
        except KeyError:
            return {"error": "Parece que está faltando la autenticación..."}

    wrapper.__name__ = ruta.__name__
    return wrapper

def payload_data():
    token = request.headers['Auth']
    contenido = jwt.decode(token,jwt_secret,algorithms=["HS256"])
    rol = contenido['rol']
    nombre = contenido['nombre']
    return {"rol":rol,
            "nombre":nombre}



'''
'' Endpoints ''
''
'''
@app.route("/inicio")
@authenticate
def index():

    datos_usuario = payload_data()
    rol = datos_usuario['rol']

    if rol == 'Empleado':
        return json.dumps({"rol":rol})
    else:
        return json.dumps({"rol":'no empleado'})


@app.route('/api/registro', methods=["POST"])
def registroPost():
    nombre = request.values.get('nombre')
    emailRegistro = request.values.get('email')
    password = request.values.get('pass')
    password2 = request.values.get('pass2')
    rol = request.values.get('rol')

    usuario = Usuario.query.filter_by(email=emailRegistro).first()
    if usuario != None:
        return 'error'

    if password == password2:
        if not contiene_caracteres_ilegales(nombre):
            nuevo_usuario = Usuario(emailRegistro,nombre,password,rol)
            db.session.add(nuevo_usuario)
            db.session.commit()
            return 'exito'
        else:
            return 'error'
    else:
        return 'error'


@app.route('/api/login', methods=['POST'])
def loginPost():
    data = request.json
    emailRegistro = data['email']
    password = data['pass']

    usuario = db.engine.execute(f"select * from usuario where email='{emailRegistro}'")

    if usuario == None:
        return "vacio"

    for fila in usuario:
        emailExistente = fila['email']
        nombre = fila['nombre']
        rol = fila['rol']
        if emailExistente == None:
            return "el usuario no existe"

        passwordExistente = fila['password']

        if password == passwordExistente:

            token = jwt.encode({
                            "nombre": nombre,
                            "rol": rol
                                    }, jwt_secret)

            return {'token': token}
        else:
            return {'error': "datos invalidos"}


@app.route('/api/alta_habitacion', methods=['POST'])
@authenticate
def alta_habitacion():
    error = 'Hubo un error con el ingreso de datos. Por favor, intentelo nuevamente.'

    data = request.json
    nro_habitacion = data['nro_habitacion']
    descripcion = data['descripcion_habitacion']
    precio_por_dia = data['precio_por_dia']
    estado = data['estado']

    habitacion = Habitacion.query.filter_by(nro_habitacion=data['nro_habitacion']).first()
    if habitacion != None:
        return jsonify(error)

    if contiene_letras(nro_habitacion) or contiene_letras(precio_por_dia):
        return jsonify(error)

    if nro_habitacion.replace(" ","") == None or descripcion.replace(" ","") == None or precio_por_dia.replace(" ","") == None or estado.replace(" ","") == None:
        return json.dumps("error", "Debes rellenar todos los campos de texto.")

    if not es_precio(precio_por_dia):
        return jsonify(error)

    if estado != 'activo' and estado != 'inactivo':
        error = 'El estado no puede ser distinto a "activo" o "inactivo"'
        return jsonify(error)

    nueva_habitacion = Habitacion(nro_habitacion,descripcion,precio_por_dia,estado)
    db.session.add(nueva_habitacion)
    db.session.commit()

    return json.dumps({"ok":"Habitación creada con éxito."})

@app.route('/api/empleado/editar', methods=['PUT'])
def editar_habitacion():
    data = request.json
    nro_habitacion = data['nro_habitacion']
    descripcion = data['descripcion_habitacion']
    precio_por_dia = data['precio_por_dia']
    id = data['id_habitacion']

    habitacion = Habitacion.query.filter_by(id_habitacion=id).first()
    if habitacion == None:
        return json.dumps("error", "No se encontró la habitacion que desea editar. Por favor, intentelo nuevamente.")

    if contiene_letras(nro_habitacion) or contiene_letras(precio_por_dia):
        return json.dumps("error", "Los campos de texto numéricos no pueden contener letras.")

    if nro_habitacion.replace(" ","") == None or descripcion.replace(" ","") == None or precio_por_dia.replace(" ","") == None:
        return json.dumps({"error": "Debes rellenar todos los campos de texto."})

    if not es_precio(precio_por_dia):
        return json.dumps("error", "El precio no es válido. Recuerda usar solo números y punto para decimal.")

    habitacion.nro_habitacion = nro_habitacion
    habitacion.descripcion = descripcion
    habitacion.precio_por_dia = precio_por_dia

    db.session.commit()

    return json.dumps({"exito": "Datos cambiados con éxito."})

@app.route('/api/empleado/estado', methods=['PUT'])
def cambiar_estado_habitacion():

    data = request.json
    id = data['id_habitacion']
    habitacion = Habitacion.query.filter_by(id_habitacion=id).first()

    if habitacion.estado == 'activo':
        habitacion.estado = 'inactivo'
    else:
        habitacion.estado = 'activo'

    db.session.commit()
    return json.dumps({"exito":habitacion.estado})

if __name__ == '__main__':
    app.run(debug=True)