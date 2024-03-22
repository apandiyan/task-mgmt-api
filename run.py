from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(5), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)

    def __repr__(self):
        return '<Group %r>' % self.name
    
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    assignee = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    done = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return '<Task %r>' % self.title
    

def authenticate_user(f):
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return jsonify({'message': 'Authentication required!', 'success': False}), 401
        user = User.query.filter_by(username=auth.username).first()
        if user and user.password == auth.password:
            return f(*args, **kwargs)
        return jsonify({'message': 'Authentication failed!', 'success': False}), 401
    wrapper.__name__ = f.__name__
    return wrapper

def authroize_user(f):
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return jsonify({'message': 'Authentication required!', 'success': False}), 401
        user = User.query.filter_by(username=auth.username).first()
        if user and user.password == auth.password and user.role == 'admin':
            return f(*args, **kwargs)
        return jsonify({'message': 'Authorization failed!', 'success': False}), 401
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == data['password']:
        return jsonify({'name': user.username, 'role': user.role, 'message': 'Login successful!', 'success': True}), 200
    return jsonify({'message': 'Login failed!', 'success': False}), 401

@app.route('/users', methods=['GET'])
@authroize_user
def get_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username, 'role': user.role} for user in users])

@app.route('/users', methods=['POST'])
@authroize_user
def create_user():
    data = request.get_json()
    user = User(username=data['username'], password=data['password'], role=data['role'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created!', 'success': True}), 201

@app.route('/users/<int:id>', methods=['GET'])
@authroize_user
def get_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User not found!', 'success': False}), 404
    return jsonify({'id': user.id, 'username': user.username, 'role': user.role})

@app.route('/users/<int:id>', methods=['PUT'])
@authroize_user
def update_user(id):
    data = request.get_json()
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User not found!', 'success': False}), 404
    user.username = data['username']
    user.password = data['password']
    user.role = data['role']
    db.session.commit()
    return jsonify({'message': 'User updated!', 'success': True}), 200

@app.route('/users/<int:id>', methods=['DELETE'])
@authroize_user
def delete_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User not found!', 'success': False}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted!', 'success': True}), 200

@app.route('/groups', methods=['GET'])
@authroize_user
def get_groups():
    groups = Group.query.all()
    return jsonify([{'id': group.id, 'name': group.name} for group in groups])

@app.route('/groups', methods=['POST'])
@authroize_user
def create_group():
    data = request.get_json()
    group = Group(name=data['name'])
    db.session.add(group)
    db.session.commit()
    return jsonify({'message': 'Group created!', 'success': True, 'name': data['name']}), 201

@app.route('/groups/<int:id>', methods=['GET'])
@authenticate_user
def get_group(id):
    group = Group.query.get(id)
    if not group:
        return jsonify({'message': 'Group not found!', 'success': False}), 404
    return jsonify({'id': group.id, 'name': group.name})

@app.route('/groups/<int:id>', methods=['PUT'])
@authroize_user
def update_group(id):
    data = request.get_json()
    group = Group.query.get(id)
    if not group:
        return jsonify({'message': 'Group not found!', 'success': False}), 404
    group.name = data['name']
    db.session.commit()
    return jsonify({'message': 'Group updated!', 'success': True, 'name': group.name}), 200

@app.route('/groups/<int:id>', methods=['DELETE'])
@authroize_user
def delete_group(id):
    group = Group.query.get(id)
    if not group:
        return jsonify({'message': 'Group not found!', 'success': False}), 404
    db.session.delete(group)
    db.session.commit()
    return jsonify({'message': 'Group deleted!', 'success': True}), 200

@app.route('/tasks', methods=['GET'])
@authenticate_user
def get_tasks():
    user = User.query.filter_by(username=request.authorization.username).first()
    if user.role == 'admin':
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter_by(assignee=user.id).all()
    return jsonify([{'id': task.id, 'title': task.title, 'description': task.description, 'assignee': task.assignee, 'owner': task.owner, 'group': task.group, 'done': task.done} for task in tasks])

@app.route('/tasks', methods=['POST'])
@authroize_user
def create_task():
    data = request.get_json()
    task = Task(title=data['title'], description=data['description'], assignee=data['assignee'], owner=data['owner'], group=data['group'], done=data['done'])
    db.session.add(task)
    db.session.commit()
    return jsonify({'message': 'Task created!', 'success': True}), 201

@app.route('/tasks/<int:id>', methods=['GET'])
@authenticate_user
def get_task(id):
    user = User.query.filter_by(username=request.authorization.username).first()
    if user.role == 'admin':
        task = Task.query.get(id)
        if not task:
            return jsonify({'message': 'Task not found!', 'success': False}), 404
    else:
        task = Task.query.get(id)
        if not task:
            return jsonify({'message': 'Task not found!', 'success': False}), 404
        if task.assignee != user.id:
            return jsonify({'message': 'Authorization failed!', 'success': False}), 401
    return jsonify({'id': task.id, 'title': task.title, 'description': task.description, 'assignee': task.assignee, 'owner': task.owner, 'group': task.group, 'done': task.done})

@app.route('/tasks/<int:id>', methods=['PUT'])
@authenticate_user
def update_task(id):
    data = request.get_json()
    user = User.query.filter_by(username=request.authorization.username).first()
    task = Task.query.get(id)
    if not task:
        return jsonify({'message': 'Task not found!', 'success': False}), 404
    if task.assignee != user.id and user.role != 'admin':
        return jsonify({'message': 'Authorization failed!', 'success': False}), 401
    task.title = data['title']
    task.description = data['description']
    task.assignee = data['assignee']
    task.owner = data['owner']
    task.group = data['group']
    task.done = data['done']
    db.session.commit()
    return jsonify({'message': 'Task updated!', 'success': True}), 200

@app.route('/tasks/<int:id>', methods=['DELETE'])
@authroize_user
def delete_task(id):
    task = Task.query.get(id)
    if not task:
        return jsonify({'message': 'Task not found!', 'success': False}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted!', 'success': True}), 200

with app.app_context():
    db.create_all()
    # create default admin user
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(username='admin', password='admin', role='admin')
        db.session.add(user)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5002)