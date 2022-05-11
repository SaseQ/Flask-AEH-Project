from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os
import datetime

app = Flask(__name__)
app.secret_key = '233DdsSd341'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///static/database/test.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firstName = db.Column(db.String(24), nullable=False)
    lastName = db.Column(db.String(24), nullable=False)
    email = db.Column(db.String(24), nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(24), nullable=False)

    def __repr__(self):
        return '%s %s: %s' % (self.firstName, self.lastName, self.email)


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    place = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(24), nullable=False)
    file = db.Column(db.String(50), nullable=False, unique=True)
    userId = db.Column(db.Integer, nullable=False)


class Logged(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userId = db.Column(db.Integer, nullable=False)


db.drop_all()
db.create_all()


@app.route('/', methods=['GET'])
def index():
    if 'user' in session:
        user_id = session['user']
        actual_user = User.query.filter_by(id=user_id).first()

        if actual_user is not None:
            user_fullname = '%s %s' % (actual_user.firstName, actual_user.lastName)
            if actual_user.role == 'admin':
                photo_list = Photo.query.all()
                return render_template('index-admin.html', name=user_fullname, photo_list=photo_list)
            else:
                photo_list = Photo.query.filter_by(userId=user_id).all()
                return render_template('index-auth.html', name=user_fullname, photo_list=photo_list)

    logged_users = User.query.join(Logged, User.id == Logged.userId) \
        .add_columns(User.id, User.firstName, User.lastName, User.email) \
        .filter(User.id == Logged.userId) \
        .filter(Logged.userId == User.id) \
        .limit(3) \
        .all()

    return render_template("index.html", lu=logged_users, len=len(logged_users))


# Start Login/Register

@app.route('/signin', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        email = request.form['InputEmail']
        password = request.form['InputPassword']

        actual_user = User.query.filter_by(email=email).first()

        if actual_user and check_password_hash(actual_user.password, password):
            if 'user' not in session:
                session['user'] = ""
            session['user'] = actual_user.id

            try:
                new = Logged(userId=actual_user.id)
                db.session.add(new)
                db.session.commit()
            except ():
                error = 'Current user is logged!'
                db.session.rollback()

            return redirect(url_for('index'))
        else:
            error = 'Incorrect email or password!'

    return render_template("login.html", error=error)


@app.route('/signup', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        first_name = request.form['InputFirstName']
        last_name = request.form['InputLastName']
        email = request.form['InputEmail']
        password = request.form['InputPassword']

        try:
            password_hash = generate_password_hash(password)
            new = User(firstName=first_name, lastName=last_name, email=email, password=password_hash, role='admin')
            db.session.add(new)
            db.session.commit()
            return redirect(url_for('login'))
        except ():
            error = 'Write error has occurred!'
            db.session.rollback()

    return render_template("register.html", error=error)


@app.route('/logout', methods=['GET'])
def logout():
    if 'user' in session:
        Logged.query.filter_by(userId=session['user']).delete()
        db.session.commit()
        session.pop('user', None)

    return redirect(url_for('index'))

# End Login/Register


# Start Profile

@app.route('/profile', methods=['GET'])
def profile():
    if 'user' in session:
        user_id = session['user']
        actual_user = User.query.filter_by(id=user_id).first()

        if actual_user is not None:
            user_fullname = '%s %s' % (actual_user.firstName, actual_user.lastName)
            return render_template('profile.html', name=user_fullname, user=actual_user)

    return redirect(url_for('index'))


@app.route('/editprofile', methods=['POST'])
def editprofile():
    if 'user' in session:
        user_id = session['user']
        actual_user = User.query.filter_by(id=user_id).first()

        first_name = request.form['InputFirstName']
        last_name = request.form['InputLastName']

        if actual_user is not None:
            actual_user.firstName = first_name
            actual_user.lastName = last_name
            db.session.commit()

    return redirect(url_for('profile'))


@app.route('/editpassword', methods=['POST'])
def editpassword():
    if 'user' in session:
        user_id = session['user']
        actual_user = User.query.filter_by(id=user_id).first()

        old_password = request.form['OldPassword']
        new_password = request.form['NewPassword']

        if actual_user and check_password_hash(actual_user.password, old_password):
            password_hash = generate_password_hash(new_password)
            actual_user.password = password_hash
            db.session.commit()

    return redirect(url_for('profile'))

# End Profile


# Start Photo

@app.route('/addphoto', methods=['GET', 'POST'])
def addphoto():
    error = ''
    if request.method == 'POST' and 'user' in session:
        name = request.form['PhotoName']
        place = request.form['PhotoPlace']
        date = request.form['PhotoDate'].split("-")
        favorite = request.form['PhotoFavorite']
        category = request.form['PhotoCategory']
        file = request.files['PhotoFile']

        final_date = datetime.date(int(date[0]), int(date[1]), int(date[2]))
        file_name = save_file(file)
        user_id = int(session['user'])

        try:
            new = Photo(name=name, place=place, date=final_date, type=favorite,
                        category=category, file=file_name, userId=user_id)
            db.session.add(new)
            db.session.commit()
            return redirect(url_for('index'))
        # except Exception as e:
        except ():
            error = 'Write error has occurred!'
            db.session.rollback()
            # print(getattr(e, 'message', repr(e)))

    if 'user' in session:
        return render_template('add-photo.html', error=error)

    return redirect(url_for('index'))


@app.route('/editphoto/<string:photo_id>', methods=['POST'])
def editphoto(photo_id):
    if request.method == 'POST' and 'user' in session:
        actual_photo = Photo.query.filter_by(id=photo_id).first()

        name = request.form['PhotoName']
        place = request.form['PhotoPlace']
        date = request.form['PhotoDate'].split("-")
        favorite = request.form['PhotoFavorite']
        category = request.form['PhotoCategory']
        file = request.files['PhotoFile']

        final_date = datetime.date(int(date[0]), int(date[1]), int(date[2]))
        file_name = save_file(file)

        if actual_photo is not None:
            try:
                if file.filename != '':
                    delete_file(actual_photo.file)
                    actual_photo.file = file_name
                actual_photo.name = name
                actual_photo.place = place
                actual_photo.date = final_date
                actual_photo.type = favorite
                actual_photo.category = category
                db.session.commit()
            except ():
                db.session.rollback()

    return redirect(url_for('index'))


@app.route('/deletephoto/<string:photo_id>', methods=['GET'])
def deletephoto(photo_id):
    if 'user' in session:
        try:
            actual_photo = Photo.query.filter_by(id=photo_id).first()
            delete_file(actual_photo.file)
            db.session.delete(actual_photo)
            db.session.commit()
        except ():
            db.session.rollback()

    return redirect(url_for('index'))

# End Photo


def save_file(file):
    file_name = uuid.uuid1()
    _, extend = os.path.splitext(file.filename)
    file.save('static/saved/%s%s' % (file_name, extend))
    return '%s%s' % (file_name, extend)


def delete_file(file_name):
    path = 'static/saved/%s' % file_name
    os.remove(path)


if __name__ == '__main__':
    app.run()
