from datetime import datetime, timedelta
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import jwt
from flask_cors import CORS
from utils import contiene_caracteres_ilegales, contiene_letras, es_precio

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root@localhost/curso'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
CORS(app)

jwt_secret = "basilio"

db = SQLAlchemy(app)
ma = Marshmallow(app)
'''
	Clases y Schemas
'''
class Usuario(db.Model):

	id = db.Column(db.Integer, primary_key=True)
	usuario = db.Column(db.String(100), nullable=False, unique=True)
	password = db.Column(db.String(100), nullable=False)
	rol = db.Column(db.String(50), nullable=False)

	reservas = db.relationship('Reserva', backref='usuario', lazy=True)

	def __init__(self,usuario,password,rol):
		self.usuario = usuario
		self.password = password
		self.rol = rol

class Habitacion(db.Model):

	id = db.Column(db.Integer, primary_key=True, nullable=False)
	nro_habitacion = db.Column(db.Integer, unique=True, nullable=False)
	descripcion = db.Column(db.String(150))
	precio_por_dia = db.Column(db.Float, nullable=False)
	estado = db.Column(db.Boolean, nullable=False)

	reservas = db.relationship('Reserva', backref='habitacion', lazy=True)

	def __init__(self, nro_habitacion, descripcion, precio_por_dia, estado):
		self.nro_habitacion = nro_habitacion
		self.descripcion = descripcion
		self.precio_por_dia = precio_por_dia
		self.estado = estado

class Reserva(db.Model):

	id = db.Column(db.Integer, primary_key=True)
	fecha_reserva = db.Column(db.DateTime)

	id_cliente = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
	id_habitacion = db.Column(db.Integer, db.ForeignKey('habitacion.id'), nullable=False)

	def __init__(self, id_cliente, id_habitacion, fecha_reserva):
		self.id_cliente = id_cliente
		self.id_habitacion = id_habitacion
		self.fecha_reserva = fecha_reserva

db.create_all()

class UsuarioSchema(ma.SQLAlchemySchema):
	class Meta:
		model = Usuario

	id = ma.auto_field()
	usuario = ma.auto_field()
	password = ma.auto_field()
	rol = ma.auto_field()

class ReservaSchema(ma.SQLAlchemySchema):
	class Meta:
		model = Reserva
		include_fk = True
		fields=('id_cliente','fecha_reserva')

class HabitacionSchema(ma.SQLAlchemySchema):
	class Meta:
		model = Habitacion
		fields = ('id', 'nro_habitacion', 'descripcion', 'precio_por_dia', 'estado', 'reservas')
	reservas = ma.Nested(ReservaSchema, many=True)
'''
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

@app.route('/api/habitacion/reservar', methods=['POST'])
def reservar_habitacion():
	''' El cliente lo voy a sacar con el usuario del payload
 		mientras tanto hardcodeo
   		tengo q ahorrar un poco mas de lineasss'''
	data = request.json
	id_habitacion = data['id_habitacion']
	str_fecha_inicio = data['fecha_inicio']
	fecha_i_object = datetime.strptime(str_fecha_inicio, '%Y %m %d')

	habitacion = Habitacion.query.get(id_habitacion)
	lista_obj_reservas = habitacion.reservas
	fechas_obj = []
	for reserva in lista_obj_reservas:
		fechas_obj.append(reserva.fecha_reserva)

	if data['fecha_fin'] != "":
		str_fecha_fin = data['fecha_fin']
		fecha_f_object = datetime.strptime(str_fecha_fin, '%Y %m %d')
		lista_fechas = [(fecha_i_object + timedelta(days=d)) for d in range((fecha_f_object - fecha_i_object).days + 1)]
		cantidad = 0
		for fecha in fechas_obj:
			if fecha in lista_fechas:
				cantidad += 1

		if cantidad > 0:
			return {'status':400, 'message':'habitacion no disponible en las fechas deseadas'}
		else:
			for fecha in lista_fechas:
				reserva = Reserva(1, id_habitacion, fecha)
				db.session.add(reserva)
				db.session.commit()

			return {'status':200, 'message':'habitacion reservada'}

	if fecha_i_object in fechas_obj:
		return {'status':400, 'message':'habitacion no disponible en la fecha deseada'}

	reserva = Reserva(1, id_habitacion, fecha_i_object)
	db.session.add(reserva)
	db.session.commit()
	return {'status':200, 'message':'habitacion reservada'}

@app.route('/api/habitacion/listado')
def listar_habitaciones():
    habitaciones = Habitacion.query.all()
    hSchema = HabitacionSchema(many=True)
    return hSchema.dumps(habitaciones)

@app.route("/api/habitacion/disponibles")
def habitaciones_disponibles():
	data = request.json
	fecha_inicio = data['fecha_inicio']
	fecha_i_object = datetime.strptime(fecha_inicio, '%Y %m %d')
	if data['fecha_fin'] != "":
		fecha_fin = data['fecha_fin']
		fecha_f_object = datetime.strptime(fecha_fin, '%Y %m %d')
		lista_fechas = [(fecha_i_object + timedelta(days=d)).strftime("%Y-%m-%d") for d in range((fecha_f_object - fecha_i_object).days + 1)]
		habitaciones = db.engine.execute("SELECT * FROM habitacion WHERE estado='1' AND id NOT IN ( SELECT id_habitacion FROM reserva WHERE fecha_reserva IN ('" + "','".join(map(str, lista_fechas)) + "'))").all()
	else:
		habitaciones = db.engine.execute("SELECT * FROM habitacion WHERE estado='1' AND id NOT IN ( SELECT id_habitacion FROM reserva WHERE fecha_reserva IN ('" + fecha_i_object.strftime("%Y-%m-%d") + "'))").all()


	hSchema = HabitacionSchema(many=True)
	return hSchema.dumps(habitaciones)

@app.route("/api/habitacion/all")
def habitaciones_all():
	hSchema = HabitacionSchema(many=True)

	data = request.json
	fecha = data['fecha']
	fecha_object = datetime.strptime(fecha, '%Y %m %d')

	lista_habitaciones = Habitacion.query.filter_by(estado=True)
	lista_disponibles = []
	lista_ocupadas = []
	fechas = []

	for habitacion in lista_habitaciones:
		if habitacion.reservas == []:
			lista_disponibles.append(habitacion)
		else:
			[fechas.append(reserva.fecha_reserva) for reserva in habitacion.reservas]
			if fecha_object in fechas:
				lista_ocupadas.append(habitacion)
			else:
				lista_disponibles.append(habitacion)

	return {"disponibles:":hSchema.dump(lista_disponibles),
         	"ocupadas:":hSchema.dump(lista_ocupadas)}

@app.route('/registro', methods=["POST"])
def registroPost():
	data = request.json
	usuarioLogin = data['nombre']
	password = data['pass']
	password2 = data['pass2']
	rol = data['rol']

	usuario = Usuario.query.filter_by(usuario=usuarioLogin).first()
	if usuario != None:
		return {'status':400}

	if password == password2:
		if not contiene_caracteres_ilegales(usuarioLogin):
			nuevo_usuario = Usuario(usuarioLogin,password,rol)
			db.session.add(nuevo_usuario)
			db.session.commit()
			return {'status':200, 'message':'usuario creado'}
		else:
			return {'status':400}
	else:
		return {'status':400}

@app.route('/login', methods=['POST'])
def loginPost():
	"""user = db.engine.execute(f"select * from usuario where usuario='usuario'")"""
	data = request.json
	usuario_login = data['usuario']
	password_login = data['pass']

	usuario = Usuario.query.filter_by(usuario=usuario_login).first()

	if usuario == None:
		return {'status':400, 'message':'Hubo un error con los datos, intentelo nuevamente.'}

	passwordExistente = usuario.password

	if password_login == passwordExistente:

		token = jwt.encode({"usuario": usuario_login,"rol": usuario.rol}, jwt_secret)

		return {'status':200,
		  		'token':token}
	else:
		return {'status':400,
		  		'message': 'Hubo un error con los datos, intentelo nuevamente.'}

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

@app.route('/api/editar_habitacion', methods=['PUT'])
@authenticate
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

@app.route('/api/cambiar_estado', methods=['PUT'])
@authenticate
def cambiar_estado_habitacion():

	data = request.json
	id = data['id_habitacion']
	habitacion = Habitacion.query.filter_by(id_habitacion=id).first()

	if habitacion.estado == 1:
		habitacion.estado = 0
	else:
		habitacion.estado = 1
	db.session.commit()

	return {"status":200}

if __name__ == '__main__':
	app.run(debug=True,  port=5000)