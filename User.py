from app import db, ma

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
        
db.create_all()

class UsuarioSchema(ma.Schema):
    class Meta:
        fields = ('id','email','nombre','password','rol')
        
usuario_schema = UsuarioSchema()
usuarios_schema = UsuarioSchema()