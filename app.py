from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import jwt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root@localhost/curso'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

db = SQLAlchemy(app)
ma = Marshmallow(app)

'''
    Clases y Schemas
'''

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
        
db.create_all()

class UsuarioSchema(ma.Schema):
    class Meta:
        fields = ('id','email','nombre','password','rol')
        
usuario_schema = UsuarioSchema()
usuarios_schema = UsuarioSchema()

'''
    End clases y schemas
'''

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/registro", methods=['GET'])
def registro():
    return render_template('page-register.html')


@app.route('/api/registro', methods=["POST"])
def registroPost():
    nombre = request.values.get('nombre')
    emailRegistro = request.values.get('email')
    password = request.values.get('pass')
    password2 = request.values.get('pass2')
    rol = 'Empleado'
    
    usuario = Usuario.query.filter_by(email=emailRegistro).first()
    if usuario != None:
        return "error"
    
    if password == password2:
        nuevo_usuario = Usuario(emailRegistro,nombre,password,rol)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return "exito"
    else:
        return 'error'
    
@app.route('/api/login', methods=['POST'])
def loginPost():
    
    emailRegistro = request.values.get('email')
    password = request.values.get('pass')
    '''rol'''
    
    usuario = Usuario.query.filter_by(email=emailRegistro).first()
    if usuario == None:
        return "el usuario no existe"
    
    if password == usuario.password:
        return render_template(index.html)
    else:
        return "datos invalidos"
        
    
    

if __name__ == '__main__':
    app.run(debug=True)