from datetime import datetime, timedelta
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import jwt
from sqlalchemy import exc
import waitress

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root@localhost/hotel_basilio'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
jwt_secret = "basilio"

db = SQLAlchemy(app)
ma = Marshmallow(app)

#Clases y Schemas
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
	id = db.Column(db.Integer, primary_key=True)
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
#FUNCIONES
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
			return {"status":400, "AttributeError":"AttributeError"}
		except exc.IntegrityError:
			return {"status":400, "IntegrityError":"Ocurrió un error con la base de datos"}

	wrapper.__name__ = ruta.__name__
	return wrapper

def payload_data():
	token = request.headers['Auth']
	contenido = jwt.decode(token,jwt_secret,algorithms=["HS256"])
	return {"rol":contenido['rol'], "usuario":contenido['usuario'], "id":contenido['id']}

def esEmpleado(datos):
	if datos['rol'] == 'Empleado':
		return True
	elif datos['rol'] == 'Cliente':
		return False

#ENDPOINTS
#CLIENTES
@app.route('/api/cliente/habitacion/reservar', methods=['POST'])
@authenticate
@error_handler
def reservar_habitacion():
	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	habitacion_nro = int(request.json['nro'])
	fecha_inicio = datetime.strptime(request.json['f_inicio'], '%Y %m %d')

	habitacion = Habitacion.query.filter_by(nro_habitacion=habitacion_nro, estado=True).first()
	if habitacion == None:
		return {"status":400, "message":"La habitacion no existe, o se encuentra inactiva actualmente."}

	lista_fechas_reservadas = [reserva.fecha_reserva for reserva in habitacion.reservas]

	if request.json['f_fin'] != "":
		fecha_fin = datetime.strptime(request.json['f_fin'], '%Y %m %d')
		lista_fechas_ingresadas = [(fecha_inicio + timedelta(days=d)) for d in range((fecha_fin - fecha_inicio).days + 1)]

		for x in range(len(lista_fechas_reservadas)):
			if lista_fechas_reservadas[x] in lista_fechas_ingresadas:
				return {'status':400, 'message':'habitacion no disponible en las fechas deseadas'}

		for fecha in lista_fechas_ingresadas:
			reserva = Reserva(datos_usuario['id'], habitacion.id, fecha)
			db.session.add(reserva)
			db.session.commit()
		return {'status':200, 'message':'habitacion reservada'}

	if fecha_inicio in lista_fechas_reservadas:
		return {'status':400, 'message':'habitacion no disponible en la fecha deseada'}

	reserva = Reserva(datos_usuario['id'], habitacion.id, fecha_inicio)
	db.session.add(reserva)
	db.session.commit()

	return {'status':200, 'message':'habitacion reservada'}

@app.route("/api/cliente/habitacion/fecha/disponibles", methods=['GET'])
@authenticate
@error_handler
def habitaciones_disponibles():
	if esEmpleado(payload_data()):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	fecha_inicio = datetime.strptime(request.json['fecha_inicio'], '%Y %m %d')

	if request.json['fecha_fin'].replace(" ", "") != "":
		fecha_hasta = request.json['fecha_fin']
		fecha_fin = datetime.strptime(fecha_hasta, '%Y %m %d')
		lista_fechas = [(fecha_inicio + timedelta(days=d)).strftime("%Y-%m-%d") for d in range((fecha_fin - fecha_inicio).days + 1)]
		habitaciones = db.engine.execute("SELECT * FROM habitacion WHERE estado='1' AND id NOT IN ( SELECT id_habitacion FROM reserva WHERE fecha_reserva IN ('" + "','".join(map(str, lista_fechas)) + "'))").all()
	else:
		habitaciones = db.engine.execute("SELECT * FROM habitacion WHERE estado='1' AND id NOT IN ( SELECT id_habitacion FROM reserva WHERE fecha_reserva IN ('" + fecha_inicio.strftime("%Y-%m-%d") + "'))").all()

	if len(habitaciones) <= 0:
		return {"status":200, "message":"No hay habitaciones disponibles en la/s fecha/s deseada/s."}
	return HabitacionSchema(many=True, exclude=['reservas', 'id', 'estado']).dumps(habitaciones)

@app.route("/api/cliente/habitacion/precio/all", methods=['GET'])
@error_handler
@authenticate
def habitaciones_disponibles_precio():
	if esEmpleado(payload_data()):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	precio_elegido = float(request.json['precio'])
	if precio_elegido < 0:
		return {"status":400, "message":"Debe ingresar un valor numerico válido."}

	habitaciones = Habitacion.query.filter(Habitacion.precio_por_dia <= precio_elegido, Habitacion.estado == True).all()

	if len(habitaciones)<=0:
		return {"message":"No hay resultados."}
	return HabitacionSchema(many=True, exclude=['reservas', 'estado', 'id']).dumps(habitaciones)

@app.route("/api/cliente/habitacion/fecha/all", methods=['GET'])
@authenticate
@error_handler
def habitaciones_all():
	if esEmpleado(payload_data()):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	fecha_object = datetime.strptime(request.json['fecha'], '%Y %m %d')

	lista_ocupadas = Habitacion.query.filter_by(estado=True).join(Reserva).filter(Reserva.fecha_reserva==fecha_object).all()
	id_ocupadas = [hab.id for hab in lista_ocupadas]
	lista_disponibles = Habitacion.query.filter(Habitacion.id.not_in(id_ocupadas), Habitacion.estado==True).all()

	return {"disponibles:":HabitacionSchema(many=True, exclude=['reservas', 'estado', 'id']).dump(lista_disponibles),
         "ocupadas:":HabitacionSchema(many=True, exclude=['reservas', 'estado', 'id']).dump(lista_ocupadas)}

@app.route('/api/cliente/reservas', methods=['GET'])
@authenticate
@error_handler
def reservas_clientes():
	datos_usuario = payload_data()
	if esEmpleado(datos_usuario):
		return {"error":"Esta área es solo para clientes. Por favor, logueese como cliente."}

	reservas = Reserva.query.filter_by(id_cliente=datos_usuario['id']).all()

	if len(reservas)>0:
		return ReservaSchema(many=True, exclude=['id_cliente']).dumps(reservas)
	else:
		return {"message":"No posee reservas."}

#REGISTRO Y LOGIN
@app.route('/registro', methods=["POST"])
@error_handler
def registroPost():
	usuarioLogin = request.json['nombre']
	password = request.json['pass']
	password2 = request.json['pass2']
	rol = request.json['rol']
	usuario = Usuario.query.filter_by(usuario=usuarioLogin).first()
	if usuario != None:
		return {"status":400,"message":"El usuario ya existe en la base de datos."}
	if password == password2:
		if usuarioLogin.isalnum():
			if rol not in ['Empleado', 'Cliente']:
				return {"status":400,"message":"El rol debe ser Empleado o Cliente"}
			nuevo_usuario = Usuario(usuarioLogin,password,rol)
			db.session.add(nuevo_usuario)
			db.session.commit()
			return {"status":200,'message':'usuario creado'}
		else:
			return {'status':400,"message":"El usuario contiene carácteres inválidos. Ingrese solo letras y/o números."}
	else:
		return {'status':400,"message":"Las contraseñas no coinciden."}

@app.route('/login', methods=['POST'])
@error_handler
def loginPost():
	usuario_login = request.json['usuario']
	password_login = request.json['pass']
	usuario = Usuario.query.filter_by(usuario=usuario_login, password=password_login).first()
	if usuario == None:
		return {'status':400, 'message':'Hubo un error con los datos, intentelo nuevamente.'}
	token = jwt.encode({"usuario": usuario_login, "rol": usuario.rol, "id":usuario.id}, jwt_secret)
	return {'status':200, 'token':token}

#EMPLEADOS
@app.route('/api/empleado/habitacion/alta', methods=['POST'])
@error_handler
@authenticate
def alta_habitacion():
	if not esEmpleado(payload_data()):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}
	numero = int(request.json['nro_habitacion'])
	descrip = request.json['descripcion_habitacion']
	precio = float(request.json['precio_por_dia'])
	estado = request.json['estado']
	if numero <= 0 or precio <= 0:
		return {"status": 400, "message": "Por favor ingrese un valor numérico válido."}
	habitacion = Habitacion.query.filter_by(nro_habitacion=numero).first()
	if habitacion != None:
		return {"status": 400, "message": "La habitación ya existe."}
	if estado.casefold() != 'activo' and estado.casefold() != 'inactivo':
		return {"error":"El estado no puede ser distinto de activo o inactivo"}
	elif estado.casefold() == 'activo':
		estado = True
	else:
		estado = False
	nueva_habitacion = Habitacion(numero,descrip,precio,estado)
	db.session.add(nueva_habitacion)
	db.session.commit()
	return {"status": 200, "message":"Habitación creada con éxito."}

@app.route('/api/empleado/habitacion/listado', methods=['GET'])
@error_handler
@authenticate
def listar_habitaciones():
	if not esEmpleado(payload_data()):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}
	habitaciones = Habitacion.query.all()
	if len(habitaciones) == 0:
		return {"message":"No hay habitaciones."}
	return HabitacionSchema(many=True).dumps(habitaciones)

@app.route('/api/empleado/habitacion/<id>', methods=['GET'])
@error_handler
@authenticate
def get_habitacion(id):
	if not esEmpleado(payload_data()):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}
	habitacion = Habitacion.query.get(id)
	if habitacion == None:
		return {"message":"No hay coincidencias con la búsqueda."}
	habitacion_schema = HabitacionSchema()
	return habitacion_schema.dumps(habitacion)

@app.route('/api/empleado/habitacion/editar', methods=['PUT'])
@error_handler
@authenticate
def editar_habitacion():
	if not esEmpleado(payload_data()):
		return {"status": 400, "message":"Esta área es solo para empleados. Por favor, logueese como empleado."}
	nro_habitacion = int(request.json['nro_habitacion'])
	descripcion = request.json['descripcion_habitacion']
	precio_por_dia = float(request.json['precio_por_dia'])
	id = int(request.json['id_habitacion'])
	if nro_habitacion <= 0 or precio_por_dia <= 0:
		return {"status": 400, "message": "Por favor ingrese un valor numérico válido."}
	habitacion = Habitacion.query.get(id)
	if habitacion == None:
		return {"status": 400, "message": "No se encontró la habitacion que desea editar. Por favor, intentelo nuevamente."}
	habitacion.nro_habitacion = nro_habitacion
	habitacion.descripcion = descripcion
	habitacion.precio_por_dia = precio_por_dia
	db.session.commit()
	return {"status":200, "exito": "Datos cambiados con éxito."}

@app.route('/api/empleado/habitacion/estado', methods=['PUT'])
@error_handler
@authenticate
def cambiar_estado_habitacion():
	if not esEmpleado(payload_data()):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}
	id = int(request.json['id_habitacion'])
	habitacion = Habitacion.query.get(id)
	if habitacion == None:
		return {"status":400, "message":"No se ha encontrado la habitación."}
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
	if not esEmpleado(payload_data()):
		return {"error":"Esta área es solo para empleados. Por favor, logueese como empleado."}
	reservas = Reserva.query.all()
	if len(reservas) > 0:
		return ReservaSchema(many=True).dumps(reservas)
	return {"status":200, "message":"No hay reservas."}

if __name__ == '__main__':
    waitress.serve(app=app, listen='*:5000')