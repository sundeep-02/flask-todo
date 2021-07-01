from flask import Flask, render_template, make_response, redirect, request, session
from flask_restplus import Api, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'verysecret'
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(app, version='1.0', title='TodoMVC API',
    description='A simple TodoMVC API',
)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '7592'
app.config['MYSQL_DB'] = 'flasktodo'

mysql = MySQL(app)

ns = api.namespace('todos', description='TODO operations')

todo = api.model('Todo', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'task': fields.String(required=True, description='The task details'),
    'due_date': fields.Date(required=True, description='The date by which the task must be completed'),
    'task_status': fields.String(required=True, description='The status of the task')
})

class TodoDAO(object):
    def getalltasks(self):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("SELECT * FROM todolist")
                todos = list(cursor.fetchall())
                cursor.close()
                return todos
            except Exception:
                return 'Error: Unable to fetch tasks'

    def get(self, id):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("SELECT * FROM todolist WHERE id=%s", (id, ))
                todo = cursor.fetchone()
                cursor.close()
                return todo
            except Exception:
                return 'Error: Unable to get the task'

    def create(self, data):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("INSERT INTO todolist(task, due_date, task_status) values(%s, %s, %s)", (data['task'], data['due_date'], data['task_status']))
                mysql.connection.commit()
                cursor.close()
            except Exception:
                return 'Error: Unable to add task'

    def update(self, id, updated_status):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("UPDATE todolist SET task_status=%s WHERE id=%s", (updated_status, id))
                mysql.connection.commit()
                cursor.close()
                return 'Updated!'
            except Exception:
                return 'Error: Unable to update the task'

    def delete(self, id):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("DELETE FROM todolist WHERE id=%s", (id, ))
                mysql.connection.commit()
                cursor.close()
            except Exception:
                return 'Error: Unable to delete the task'

    def getDue(self, due_date):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("SELECT * FROM todolist WHERE due_date=%s", (due_date, ))
                todos = list(cursor.fetchall())
                cursor.close()
                return todos
            except Exception:
                return 'Error: Unable to get the task'

    def getOverdue(self):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("SELECT * FROM todolist WHERE due_date < curdate() AND task_status <> 'Finished'")
                todos = list(cursor.fetchall())
                cursor.close()
                return todos
            except Exception:
                return 'Error: Unable to fetch tasks'

    def getFinished(self):
        with app.app_context():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute("SELECT * FROM todolist WHERE task_status = 'Finished'")
                todos = list(cursor.fetchall())
                cursor.close()
                return todos
            except Exception:
                return 'Error: Unable to fetch tasks'

DAO = TodoDAO()
user  = {}

def getUser(username):
    with app.app_context():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM userlist WHERE username = %s", (username, ))
            user = cursor.fetchone()
            cursor.close()
            return user
        except Exception:
            return 'Error: Unable to fetch user details'

@ns.route('/login')
class Login(Resource):
    def get(self):
        return make_response(render_template('login.html'))

    def post(self):
        form_username = request.form['username']
        form_password = request.form['password']
        user = getUser(form_username)
        if user:
            session['username'] = user['username']
            session['access'] = user['access']
            db_password = user['password']
            if form_password == db_password:
                return redirect(api.url_for(TodoList))
            else:
                return make_response(render_template('login.html', error="Incorrect Credentials"))
        else:
            return make_response(render_template('login.html', error="User not found"))


@ns.route('/logout')
class Logout(Resource):
    def get(self):
        session.pop('username', None)
        session.pop('access', None)
        return redirect(api.url_for(Login))

@ns.route('/')
class TodoList(Resource):
    '''Shows a list of all todos, and lets you POST to add new tasks'''
    @ns.doc('list_todos')
    #@ns.marshal_list_with(todo)
    def get(self):
        '''List all tasks'''
        tasks = DAO.getalltasks()
        if 'username' in session:
            user['name'] = session['username']
            user['access'] = session['access']
            return make_response(render_template('todos.html', tasks=tasks, user=user))
        else:
            return redirect(api.url_for(Login))

    @ns.doc('create_todo')
    @ns.expect(todo)
    #@ns.marshal_with(todo, code=201)
    def post(self):
        '''Create a new task'''
        new_task = {}
        new_task['task'] = request.form['new_task']
        new_task['due_date'] = request.form['due_date']
        new_task['task_status'] = "Not Started"
        DAO.create(new_task)
        return redirect(api.url_for(TodoList))

@ns.route('/<int:id>')
@ns.response(404, 'Todo not found')
@ns.param('id', 'The task identifier')
class Todo(Resource):
    '''Show a single todo item and lets you delete them'''
    @ns.doc('get_todo')
    @ns.marshal_with(todo)
    def get(self, id):
        '''Fetch a task given its identifier'''
        return DAO.get(id)

    @ns.doc('delete_todo')
    @ns.response(204, 'Todo deleted')
    def delete(self, id):
        '''Delete a task given its identifier'''
        DAO.delete(id)
        return redirect(api.url_for(TodoList))

    @ns.expect(todo)
    @ns.marshal_with(todo)
    def put(self, id):
        '''Update a task given its identifier'''
        updated_status = request.form['data']
        DAO.update(id, updated_status)
        return redirect(api.url_for(TodoList))

@ns.route('/due/<string:due_date>')
@ns.param('due_date', 'The Due date')
class Due(Resource):
    @ns.doc('get_due')
    #@ns.marshal_with(todo)
    def get(self, due_date):
        '''Fetch tasks that are due by given date'''
        tasks = DAO.getDue(due_date)
        if 'username' in session:
            user['name'] = session['username']
            user['access'] = session['access']
            return make_response(render_template('todos.html', tasks=tasks, user=user))
        else:
            return redirect(api.url_for(Login))

@ns.route('/overdue')
class Overdue(Resource):
    @ns.doc('get_overdue')
    def get(self):
        '''Fetch tasks that are overdue'''
        tasks = DAO.getOverdue()
        if 'username' in session:
            user['name'] = session['username']
            user['access'] = session['access']
            return make_response(render_template('todos.html', tasks=tasks, user=user))
        else:
            return redirect(api.url_for(Login))

@ns.route('/finished')
class Finished(Resource):
    @ns.doc('get_finished')
    def get(self):
        '''Fetch finished tasks'''
        tasks = DAO.getFinished()
        if 'username' in session:
            user['name'] = session['username']
            user['access'] = session['access']
            return make_response(render_template('todos.html', tasks=tasks, user=user))
        else:
            return redirect(api.url_for(Login))

if __name__ == '__main__':
    app.run(debug=True)