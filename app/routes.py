import os
from flask import render_template, flash, redirect, url_for, request, send_from_directory, jsonify
from flask_login import logout_user, login_user, current_user, login_required
from werkzeug.urls import url_parse
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import ValidationError, DataRequired
import sqlalchemy.sql.expression


from .models import User, paper, paper_parse_queue
from ._init import app, db
from . import controller
from .Form import LoginForm, messageForm #RegistrationForm


# root page
@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('welcome'))
    return render_template('Application.html')

# route for login page
@app.route('/Login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('welcome'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=os.environ['ONLY_USER_NAME']).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('welcome')
        if user.Is_adm ==1:
            next_page = url_for('AdminWelcome')
        return redirect(next_page)
    return render_template('Can_log.html', title='Sign In', form=form)

# route for welcome page
@app.route('/welcome', methods=['GET', 'POST'])
@login_required
def welcome():
    # tmp0 = list(paper.query.limit(10))
    # https://stackoverflow.com/a/60815/7290857
    arxivID_list = db.session.execute(db.select(paper.arxivID).order_by(sqlalchemy.sql.expression.func.random()).limit(10)).all()
    tmp0 = [paper.query.filter_by(arxivID=x[0]).first() for x in arxivID_list]
    return render_template('welcome.html', title='Home', user=current_user, paper_list=tmp0)

# route for welcome page of administrator
@app.route('/AdminWelcome', methods=['GET', 'POST'])
def AdminWelcome():
    return render_template('AdminWelcome.html')

# route for logout, redirect them to root page
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# # route for register
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     form = RegistrationForm()
#     if form.validate_on_submit():
#         user = User(username=form.username.data, email=form.email.data)
#         user.set_password(form.password.data)
#         db.session.add(user)
#         db.session.commit()
#         if current_user.is_authenticated:
#             flash('Add a user')
#         else:
#             flash('Congratulations, you are now a registered user!')
#         return redirect(url_for('login'))
#     return render_template('Register.html', title='Register', form=form)

# route for get paper
@app.route('/paper/<arxivID>', methods=['GET', 'POST'])
@login_required
def get_paper(arxivID):
    tmp0 = paper.query.filter_by(arxivID=arxivID).first()
    return render_template('paper.html', paper=tmp0, title='paper_chat')

@app.route('/search', methods=['POST'])
@login_required
def search_paper():
    arxivID = str(request.form.get('arxivID')).strip()
    tmp0 = paper.query.filter_by(arxivID=arxivID).first()
    if tmp0 is None:
        # TODO: add this arxivID to paper_parse_queue table
        db.session.add(paper_parse_queue(arxivID=arxivID))
        db.session.commit()
        flash("No such paper yet! we will add it soon! please search again 1 minute later (usually).")
        ret = redirect(url_for('welcome'))
    else:
        ret = redirect(url_for('get_paper', arxivID=arxivID))
    return ret

# route for chat response
@app.route('/chat_response', methods=['GET', 'POST'])
@login_required
def chat_response():
    if request.method == 'POST':
        prompt = request.form['prompt']
        res = {}
        res['answer'] = controller.reply_message(current_user.get_id(), request.form['arxivID'], prompt)
    return jsonify(res), 200

# route to remove, add and make other users admin
@app.route('/User_management', methods=['GET', 'POST'])
@login_required
def User_management():
    if current_user.if_adm() != 1:
        return redirect(url_for('welcome'))
    users = User.query.all()

    return render_template('User_management.html', title='User_management', Users_list=users)

# get user id for delete
@app.route('/delete/<user_id>')
@login_required
def delete_user(user_id):
    if current_user.if_adm() != 1:
        return redirect(url_for('welcome'))
    controller.delete_user(user_id)
    flash("User"+str(user_id)+ " has been deleted!")
    return redirect(url_for('User_management'))

# make user an admin
@app.route('/make_admin/<user_id>')
@login_required
def make_admin(user_id):
    if current_user.if_adm() != 1:
        return redirect(url_for('welcome'))
    controller.make_admin(user_id)
    flash("User"+str(user_id)+ " now is admin!")
    return redirect(url_for('User_management'))


