from flask import Flask, render_template, url_for, redirect, request, session, flash, send_from_directory, abort, send_file, Response
from pytube import YouTube
from forms import RegistrationForm, LoginForm
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user
from io import BytesIO
from werkzeug.wsgi import FileWrapper

from datetime import datetime

app = Flask(__name__)
app.secret_key = "hello"
app.config["CLIENT_VIDEOS"] = "/home/jckpokimon/static/client/mp4"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///sitebase.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique = False, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(20), unique = False, nullable=False)
    dateCreated = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"User('{self.username}', '{self.email})"

class FileContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100))
    name = db.Column(db.String(200)) 
    data = db.Column(db.LargeBinary)
    fileType = db.Column(db.String(200))

    def __repr__(self):
        return f"{self.name}"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/youtube", methods=['GET', 'POST'])
def youtube():
    if request.method == 'POST':
        link = request.form['link']
        if(link):
            try:
                yt = YouTube(link)
                session["link"] = link
                return redirect(url_for("download"))
            except Exception:
                flash("Invalid link! Please check URL of YouTube video", "danger")
                return redirect(request.url)
        else:
            flash("HEY HEY! Enter a Link!", "warning")
            return redirect(request.url)
    return render_template('youtube.html')

@app.route("/download", methods=['GET', 'POST'])
def download():
    if session["link"]:
        link = session["link"]
        yt = YouTube(link)
        videos = yt.streams.filter(progressive=True)[0]
        test = videos.title
    if request.method == 'POST':
        if request.form['submit_button'] == 'Download':
            fileName = request.form['fileName']
            fileQuality = request.form['qualitySelector']
            name = str(fileName) + ".mp4"
            link = session["link"]
            yt = YouTube(link)

            if str(fileQuality) == "1":
                videos = yt.streams.filter(progressive=True)[0]
            elif str(fileQuality) == "2":
                videos = yt.streams.filter(progressive=True)[1]
            
            videos.download(output_path=app.config["CLIENT_VIDEOS"], filename=str(fileName))
            try:
                return send_from_directory(app.config["CLIENT_VIDEOS"], filename=name, as_attachment=True)
            except FileNotFoundError:
                abort(404)

    return render_template('download.html', name=test)
    

@app.route("/ty")
def ty():
    return render_template('ty.html')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if form.validate_on_submit():
        find = User.query.filter_by(email=form.email.data).first()
        if find:
            flash('You already have an account', 'danger')
        else:
            user = User(username=form.username.data, email=form.email.data, password=form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for("home"))

    return render_template('signup.html', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        find = User.query.filter_by(email=form.email.data).first()
        if find:
            if form.password.data == find.password:
                flash('Login Successful', 'success')
                login_user(find)
                return render_template('home.html', user=find.username)
            else:
                flash('Wrong Password', 'danger')
        else:
            flash('No accounts found with this email', 'danger')
    
    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    if current_user.is_active:
        fileList = FileContent.query.filter_by(email=current_user.email).all()
        length = len(fileList)
        for i in range(length):
            db.session.delete(fileList[i])
        db.session.commit()
        logout_user()
        return redirect(url_for("home"))
    else:
        return redirect(url_for("login"))

@app.route("/cloud/<int:para>", methods=['GET', 'POST'])
def cloud(para):
    
    fileList = FileContent.query.filter_by(email=current_user.email).all()
    length = len(fileList)
    if para < 100000:
        download_file = fileList[para]
        b = BytesIO(download_file.data)
        w = FileWrapper(b)
        headers = {
            'Content-Disposition': 'attachement; filename="{}"'.format(download_file.name)
        }
        response = Response(w,
                        mimetype=download_file.fileType,
                        direct_passthrough=False,
                        headers=headers)
        response.headers['Content-Type'] = download_file.fileType               
        return response
    return render_template('cloud.html', fileList=fileList, length=length)

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['inputFile']
        newFile = FileContent(email = current_user.email, name = file.filename, data=file.read(), fileType=file.content_type)
        db.session.add(newFile)
        db.session.commit()
        return redirect(url_for("ty"))
    return render_template('upload.html')

if __name__ == "__main__":
    app.run(debug=True)