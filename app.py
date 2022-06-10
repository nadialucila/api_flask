from datetime import datetime, timedelta
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import jwt
from utils import contiene_caracteres_ilegales, contiene_letras, es_precio
import waitress

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

class ReservaSchema(ma.SQLAlchemySchema):
	class Meta:
		model = Reserva
		include_fk = True
		fields=('id_cliente','fecha_reserva', 'id_habitacion')

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
			return {"DecodeError": "Error al decodificar"}
		except jwt.InvalidTokenError:
			return {"InvalidToken": "Token inválido"}
		except KeyError:
			return {"KeyError": "Ha ocurrido un error, por favor, compruebe haber ingresado los campos correctamente."}

	wrapper.__name__ = ruta.__name__
	return wrapper

def error_handler(ruta):
	def wrapper(*args, **kwargs):
		try:
			return ruta(*args, **kwargs)
		except KeyError:
			return {"status":400, "KeyError":"Oops! falta un campo... intentelo nuevamente."}
		except ValueError:
			return {"status":400, "ValueError":"Los valores ingresados son incorrectos, por favor, compruebe los errores e intentelo nuevamente."}
		except AttributeError:
			return {"status":400, "AttributeError":"No hubo coincidencias con la búsqueda."}

	wrapper.__name__ = ruta.__name__
	return wrapper

def payload_data():
	token = request.headers['Auth']
	contenido = jwt.decode(token,jwt_secret,algorithms=["HS256"])
	print(contenido)
	rol = contenido['rol']
	usuario = contenido['usuario']
	return {"rol":rol,
			"usuario":usuario}

def esEmpleado(datos):
	if datos['rol'] == 'Empleado':
		return True
	elif datos['rol'] == 'Cliente':
		return False

'''
 Endpoints
'''
'''
Clientes
'''
@app.route('/api/cliente/habitacion/reservar', methods=['POST'])
@authenticate
@error_handler
def reservar_habitacion():

	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	data = request.json
	id_habitacion = data['id']
	str_fecha_inicio = data['f_inicio']
	fecha_i_object = datetime.strptime(str_fecha_inicio, '%Y %m %d')

	habitacion = Habitacion.query.get(id_habitacion)
	lista_obj_reservas = habitacion.reservas
	fechas_obj = []
	for reserva in lista_obj_reservas:
		fechas_obj.append(reserva.fecha_reserva)

	if data['f_fin'] != "":
		str_fecha_fin = data['f_fin']
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
				reserva = Reserva(datos_usuario['id'], id_habitacion, fecha)
				db.session.add(reserva)
				db.session.commit()

			return {'status':200, 'message':'habitacion reservada'}

	if fecha_i_object in fechas_obj:
		return {'status':400, 'message':'habitacion no disponible en la fecha deseada'}

	reserva = Reserva(1, id_habitacion, fecha_i_object)
	db.session.add(reserva)
	db.session.commit()
	return {'status':200, 'message':'habitacion reservada'}

@app.route("/api/cliente/habitacion/fecha/disponibles", methods=['GET'])
@authenticate
@error_handler
def habitaciones_disponibles():
	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	fecha_inicio = request.json['fecha_inicio']
	fecha_i_object = datetime.strptime(fecha_inicio, '%Y %m %d')
	if request.json['fecha_fin'] != "":
		fecha_fin = request.json['fecha_fin']
		fecha_f_object = datetime.strptime(fecha_fin, '%Y %m %d')
		lista_fechas = [(fecha_i_object + timedelta(days=d)).strftime("%Y-%m-%d") for d in range((fecha_f_object - fecha_i_object).days + 1)]
		habitaciones = db.engine.execute("SELECT * FROM habitacion WHERE estado='1' AND id NOT IN ( SELECT id_habitacion FROM reserva WHERE fecha_reserva IN ('" + "','".join(map(str, lista_fechas)) + "'))").all()
	else:
		habitaciones = db.engine.execute("SELECT * FROM habitacion WHERE estado='1' AND id NOT IN ( SELECT id_habitacion FROM reserva WHERE fecha_reserva IN ('" + fecha_i_object.strftime("%Y-%m-%d") + "'))").all()

	hSchema = HabitacionSchema(many=True)
	if len(habitaciones) <= 0:
		return {"status":200, "message":"No hay habitaciones disponibles en la/s fecha/s deseada/s."}
	return hSchema.dumps(habitaciones)

@app.route("/api/cliente/habitacion/precio/all", methods=['GET'])
@error_handler
@authenticate
def habitaciones_disponibles_precio():

	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	precio_elegido = request.json['precio']
	if not es_precio(precio_elegido) or contiene_letras(precio_elegido) or precio_elegido == "" or int(precio_elegido) < 0:
		return {"status":400, "message":"Debe ingresar un valor NUMERICO válido."}

	habitaciones = db.engine.execute(f"SELECT * FROM habitacion WHERE precio_por_dia<'{precio_elegido}' AND estado=1").all()

	hSchema = HabitacionSchema(many=True)
	if len(habitaciones)<=0:
		return {"message":"No hay resultados."}
	return hSchema.dumps(habitaciones)

@app.route("/api/cliente/habitacion/fecha/all", methods=['GET'])
@authenticate
@error_handler
def habitaciones_all():
	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

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

	hSchema = HabitacionSchema(many=True)
	return {"disponibles:":hSchema.dump(lista_disponibles),
         	"ocupadas:":hSchema.dump(lista_ocupadas)}

@app.route('/api/cliente/reservas', methods=['GET'])
@authenticate
@error_handler
def reservas_clientes():

	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	reservas = Reserva.query.filter_by(id_cliente=datos_usuario['id'])
	rSchema = ReservaSchema(many=True, exclude=['id_cliente'])

	if len(reservas)>0:
		return rSchema(reservas)
	else:
		return {"message":"No posee reservas."}

'''
Ambos
'''
@app.route('/registro', methods=["POST"])
@error_handler
def registroPost():
	data = request.json
	usuarioLogin = data['nombre']
	password = data['pass']
	password2 = data['pass2']
	rol = data['rol']

	usuario = Usuario.query.filter_by(usuario=usuarioLogin).first()
	if usuario != None:
		return {"status":400,
          		"message":"El usuario ya existe en la base de datos."}

	if password == password2:
		if not contiene_caracteres_ilegales(usuarioLogin):
			nuevo_usuario = Usuario(usuarioLogin,password,rol)
			db.session.add(nuevo_usuario)
			db.session.commit()
			return {"status":200,
           			'message':'usuario creado'}
		else:
			return {'status':400,
           			"message":"El usuario contiene carácteres inválidos."}
	else:
		return {'status':400,
          		"message":"Las contraseñas no coinciden."}

@app.route('/login', methods=['POST'])
@error_handler
def loginPost():
	usuario_login = request.json['usuario']
	password_login = request.json['pass']
 
	hola = "hola"

	usuario = Usuario.query.filter_by(usuario=usuario_login).first()

	if usuario == None:
		return {'status':400,
          		'message':'Hubo un error con los datos, intentelo nuevamente.'}

	passwordExistente = usuario.password

	if password_login == passwordExistente:

		token = jwt.encode({"usuario": usuario_login,
                      		"rol": usuario.rol,
                      		"id":usuario.id}, jwt_secret)

		return {'status':200,
		  		'token':token}
	else:
		return {'status':400,
		  		'message': 'Hubo un error con los datos, intentelo nuevamente.'}
'''
Empleado
'''
@app.route('/api/empleado/habitacion/listado', methods=['GET'])
@error_handler
@authenticate
def listar_habitaciones():
	datos_usuario = payload_data()
	if not esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}

	habitaciones = Habitacion.query.all()
	if len(habitaciones) == 0:
		return {"message":"No hay habitaciones."}
	hSchema = HabitacionSchema(many=True)
	return hSchema.dumps(habitaciones)

@app.route('/api/empleado/habitacion/<id>', methods=['GET'])
@error_handler
@authenticate
def get_habitacion(id):
	datos_usuario = payload_data()
	if not esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}

	habitacion = Habitacion.query.get(id)
	hSchema = HabitacionSchema()
	if habitacion == None:
		return {"message":"No hay coincidencias con la búsqueda."}
	return hSchema.dumps(habitacion)

@app.route('/api/empleado/habitacion/alta', methods=['POST'])
@error_handler
@authenticate
def alta_habitacion():
	datos_usuario = payload_data()
	if not esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}

	error = 'Hubo un error con el ingreso de datos. Por favor, intentelo nuevamente.'

	data = request.json
	nro_habitacion = data['nro_habitacion']
	descripcion = data['descripcion_habitacion']
	precio_por_dia = data['precio_por_dia']
	estado = data['estado']

	habitacion = Habitacion.query.filter_by(nro_habitacion=data['nro_habitacion']).first()

	if habitacion != None:
		return {"error": error}

	if contiene_letras(nro_habitacion) or contiene_letras(precio_por_dia) or contiene_letras(estado):
		return {"error":error}

	if nro_habitacion.replace(" ","") == None or descripcion.replace(" ","") == None or precio_por_dia.replace(" ","") == None or estado.replace(" ","") == None:
		return {"error": "Debes rellenar todos los campos de texto."}

	if not es_precio(precio_por_dia):
		return {"error":error}

	if estado != '1' and estado != '0':
		error = 'El estado no puede ser distinto a "1" o "0"'
		return {"error":error}

	nueva_habitacion = Habitacion(nro_habitacion,descripcion,precio_por_dia,estado)
	db.session.add(nueva_habitacion)
	db.session.commit()

	return {"status": 200, "message":"Habitación creada con éxito."}

@app.route('/api/empleado/habitacion/editar', methods=['PUT'])
@error_handler
@authenticate
def editar_habitacion():

	datos_usuario = payload_data()
	if not esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}

	data = request.json
	nro_habitacion = data['nro_habitacion']
	descripcion = data['descripcion_habitacion']
	precio_por_dia = data['precio_por_dia']
	id = data['id_habitacion']

	habitacion = Habitacion.query.filter_by(id=id).first()
	if habitacion == None:
		return {"error": "No se encontró la habitacion que desea editar. Por favor, intentelo nuevamente."}

	if contiene_letras(nro_habitacion) or contiene_letras(precio_por_dia):
		return {"error": "Los campos de texto numéricos no pueden contener letras."}

	if nro_habitacion.replace(" ","") == None or descripcion.replace(" ","") == None or precio_por_dia.replace(" ","") == None:
		return {"error": "Debes rellenar todos los campos de texto."}

	if not es_precio(precio_por_dia):
		return {"error": "El precio no es válido. Recuerda usar solo números y punto para decimal."}

	habitacion.nro_habitacion = nro_habitacion
	habitacion.descripcion = descripcion
	habitacion.precio_por_dia = precio_por_dia

	db.session.commit()

	return {"status":200, "exito": "Datos cambiados con éxito."}

@app.route('/api/empleado/habitacion/estado', methods=['PUT'])
@error_handler
@authenticate
def cambiar_estado_habitacion():

	datos_usuario = payload_data()
	if not esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}

	data = request.json
	id = data['id_habitacion']
	habitacion = Habitacion.query.filter_by(id_habitacion=id).first()

	if habitacion.estado == 1:
		habitacion.estado = 0
	else:
		habitacion.estado = 1
	db.session.commit()

	return {"status":200}

@app.route('/api/empleado/reservas', methods=['GET'])
@error_handler
@authenticate
def reservas_all():

	datos_usuario = payload_data()
	if not esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}

	reservas = Reserva.query.all()
	rSchema = ReservaSchema(many=True)
	if len(reservas)>0:
		return rSchema.dumps(reservas)
	else:
		return {"message":"No hay reservas."}

if __name__ == '__main__':
    waitress.serve(app=app, listen='*:5000')