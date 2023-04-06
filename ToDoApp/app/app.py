import re  
import os
import uuid
import datetime
from datetime import timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__) 

app.secret_key = 'abcdefgh'
  
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'cs353hw4db'
  
mysql = MySQL(app)  

@app.route('/')

@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s AND password = % s', (username, password, ))
        user = cursor.fetchone()
        if user:              
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return redirect(url_for('tasks'))
        else:
            message = 'Please enter correct email / password !'
    return render_template('login.html', message = message)


@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        unique_id = uuid.uuid4().int & (1<<32)-1
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s', (username, ))
        account = cursor.fetchone()
        if account:
            message = 'Choose a different username!'
  
        elif not username or not password or not email:
            message = 'Please fill out the form!'

        else:
            cursor.execute('INSERT INTO User (id, username, email, password) VALUES (%s, % s, % s, % s)', (unique_id, username, email, password,))
            mysql.connection.commit()
            message = 'User successfully created!'

    elif request.method == 'POST':

        message = 'Please fill all the fields!'
    return render_template('register.html', message = message)

@app.route("/logout", methods=['GET', "POST"])
def logout():
    session['loggedin'] = False
    session['userid'] = ""
    session['username'] = ""
    session['email'] = ""
    return redirect(url_for("login"))

##### TASKS #####
@app.route('/tasks', methods =['GET', 'POST'])
def tasks():
    message = ''
    if(request.args.get("message")):
        message = request.args.get("message")
    userid = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get tasks
    cursor.execute('SELECT * FROM Task WHERE user_id = % s', (userid, ))
    tasks = cursor.fetchall()

    # Change deadline format
    for task in tasks:
        # Format the datetime object to the appropriate format for datetime-local input type
        task['formattedDeadline'] = task['deadline'].strftime("%Y-%m-%dT%H:%M:%S")

    # Classify as completed and todo
    completedTasks = []
    todoTasks = []
    for task in tasks:
        if task['status'] == 'Done':
            completedTasks.append(task)
        else:
            todoTasks.append(task)

    # Sort tasks with deadline and done_time
    completedTasks = sorted(completedTasks, key=lambda task: task['done_time'])
    todoTasks = sorted(todoTasks, key=lambda task: task['deadline'])

    # Get tasktypes
    cursor.execute('SELECT * FROM TaskType', ( ))
    taskTypes = cursor.fetchall()

    # Get task with selected id for edit modal
    if (request.args.get("task_id")):
        selectedTaskId = request.args.get("task_id")
    else:
        selectedTaskId = "0"
    selected = tasks[0]
    for task in tasks:
        if str(task['id']) == str(selectedTaskId):
            selected = task

    openCreate = request.args.get("openCreate")

    return render_template('tasks.html', tasks=tasks, completedTasks=completedTasks, todoTasks=todoTasks, taskTypes=taskTypes, message=message, selectedTaskId=selectedTaskId, selectedTask=selected, openCreate=openCreate)

#### CREATE TASK #####
@app.route("/openCreateModal", methods=["POST", "GET"])
def openCreateModal():
    return redirect(url_for("tasks", openCreate="True"))

@app.route("/closeCreateModal", methods=["POST", "GET"])
def closeCreateModal():
    return redirect(url_for("tasks", openCreate="False"))

@app.route('/createTask', methods =['GET', 'POST'])
def createTask():
    message = ''
    openCreate = "False"

    userid = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST' and 'title' in request.form and 'description' in request.form:
        title = request.form['title']
        description = request.form['description']
        taskType = request.form.get('taskType')
        dueDate = request.form['dueDate']
        unique_id = uuid.uuid4().int & (1<<16)-1

        if not title or not description or not taskType or not dueDate:
            message = 'Fields can not be empty!'
            openCreate = "True"

        else:
            creation_time = datetime.datetime.now()
            creation_time = datetime.datetime.now(tz=timezone.utc)
            gmt3_offset = timedelta(hours=3)
            gmt3_timezone = timezone(gmt3_offset)
            creation_time_gmt3 = creation_time.astimezone(gmt3_timezone)

            cursor.execute('INSERT INTO Task (id, title, description, status, deadline, creation_time, done_time, user_id, task_type) VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s)', (unique_id, title, description, "Todo", dueDate, creation_time_gmt3, userid, taskType))
            mysql.connection.commit()
    elif request.method == 'POST':
        print("here")

        message = 'Please fill all the fields! elif'
    
    return redirect(url_for("tasks", message=message, openCreate=openCreate))

#### Edit Task ####
@app.route("/openEditModal/<int:task_id>", methods=["POST", "GET"])
def openEditModal(task_id):
    return redirect(url_for("tasks", task_id=task_id))

@app.route("/closeEditModal", methods=["POST", "GET"])
def closeEditModal():
    return redirect(url_for("tasks", task_id="0"))

@app.route("/editTask", methods=["POST", "GET"])
def editTask():
    message=''
    selectedTaskId = request.args.get("task_id")
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST' and 'edit-title' in request.form and 'edit-description' in request.form:
        title = request.form['edit-title']
        description = request.form['edit-description']
        taskType = request.form.get('edit-taskType')
        dueDate = request.form['edit-dueDate']

        if not title or not description or not taskType or not dueDate:
            message = 'Fields can not be empty!'
            task_id=selectedTaskId
        else:
            cursor.execute('UPDATE Task SET title = %s, description = %s, task_type = %s, deadline = %s WHERE id = %s', (title, description, taskType, dueDate, selectedTaskId))
            mysql.connection.commit()
            task_id="0"
    elif request.method == 'POST':
        message = 'Please fill all the fields! elif'

    return redirect(url_for("tasks", task_id=task_id, message=message))

#### DELETE Task ####
@app.route("/delete/<int:task_id>")
def delete(task_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM Task WHERE id = %s', (task_id, ))
    mysql.connection.commit()

    return redirect(url_for("tasks"))

#### MARK TASK ####
@app.route("/markDone/<int:task_id>")
def markDone(task_id):
    done_time = datetime.datetime.now(tz=timezone.utc)
    gmt3_offset = timedelta(hours=3)
    gmt3_timezone = timezone(gmt3_offset)
    done_time_gmt3 = done_time.astimezone(gmt3_timezone)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('UPDATE Task SET status = %s, done_time = %s  WHERE id = %s', ('Done', done_time_gmt3, task_id, ))
    mysql.connection.commit()

    return redirect(url_for("tasks"))

@app.route("/markUnDone/<int:task_id>")
def markUnDone(task_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('UPDATE Task SET status = %s, done_time = NULL WHERE id = %s', ('Todo', task_id, ))
    mysql.connection.commit()

    return redirect(url_for("tasks"))

#### ANALYSIS #####
@app.route('/analysis', methods =['GET', 'POST'])
def analysis():
    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # SELECT title, TIMEDIFF(done_time, deadline) as latency, HOUR(TIMEDIFF(done_time, deadline)) DIV 24 as latency_day, HOUR(TIMEDIFF(done_time, deadline)) % 24 as latency_hour, MINUTE(TIMEDIFF(done_time, deadline)) as latency_minute  FROM Task  WHERE user_id=1 AND done_time>deadline;
    cursor.execute('SELECT title, TIMEDIFF(done_time, deadline) as latency, HOUR(TIMEDIFF(done_time, deadline)) DIV 24 as latency_day, HOUR(TIMEDIFF(done_time, deadline)) %% 24 as latency_hour, MINUTE(TIMEDIFF(done_time, deadline)) as latency_minute  FROM Task  WHERE user_id=%s AND done_time>deadline;', (user_id, ))
    task_latencies = cursor.fetchall()
    
    # SELECT HOUR(S.avg_completion_time) DIV 24 as Day, HOUR(S.avg_completion_time) % 24 as Hour, MINUTE(S.avg_completion_time) as Minute FROM (SELECT SEC_TO_TIME(avg(TIME_TO_SEC(TIMEDIFF(done_time,creation_time)))) as avg_completion_time FROM Task WHERE user_id=1) S; 
    cursor.execute('SELECT HOUR(S.avg_completion_time) DIV 24 as Day, HOUR(S.avg_completion_time) %% 24 as Hour, MINUTE(S.avg_completion_time) as Minute FROM (SELECT SEC_TO_TIME(avg(TIME_TO_SEC(TIMEDIFF(done_time,creation_time)))) as avg_completion_time FROM Task WHERE user_id=%s) S; ', (user_id, ))
    avg_completion_time = cursor.fetchall()

    # SELECT task_type, COUNT(*) as count FROM Task WHERE user_id=1 AND status="Done" GROUP BY task_type ORDER BY count DESC;
    cursor.execute('SELECT task_type, COUNT(*) as count FROM Task WHERE user_id=%s AND status="Done" GROUP BY task_type ORDER BY count DESC;', (user_id, ))
    completed_tasks_by_tasktypes = cursor.fetchall()
   
    # SELECT title, deadline FROM Task WHERE user_id=1 AND status="Todo" ORDER BY deadline ASC;
    cursor.execute('SELECT title, deadline FROM Task WHERE user_id=%s AND status="Todo" ORDER BY deadline ASC;', (user_id, ))
    uncompleted_tasks_by_deadline = cursor.fetchall()

    # SELECT * FROM (SELECT title, TIMEDIFF(done_time,creation_time) as completion_time,HOUR(TIMEDIFF(done_time,creation_time)) DIV 24 as Day, HOUR(TIMEDIFF(done_time,creation_time)) % 24 as Hour, MINUTE(TIMEDIFF(done_time,creation_time)) as Minute  FROM Task  WHERE user_id=1 AND status='Done' ORDER BY completion_time DESC LIMIT 2) as S ORDER BY completion_time ASC;
    cursor.execute('SELECT * FROM (SELECT title, TIMEDIFF(done_time,creation_time) as completion_time,HOUR(TIMEDIFF(done_time,creation_time)) DIV 24 as Day, HOUR(TIMEDIFF(done_time,creation_time)) %% 24 as Hour, MINUTE(TIMEDIFF(done_time,creation_time)) as Minute  FROM Task  WHERE user_id=%s AND status=%s ORDER BY completion_time DESC LIMIT 2) as S ORDER BY completion_time ASC;', (user_id, 'Done', ))
    completion_time_tasks = cursor.fetchall()

    return render_template('analysis.html', task_latencies=task_latencies, avg_completion_time=avg_completion_time, completed_tasks_by_tasktypes=completed_tasks_by_tasktypes, uncompleted_tasks_by_deadline=uncompleted_tasks_by_deadline, completion_time_tasks=completion_time_tasks)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)