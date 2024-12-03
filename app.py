from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from sqlalchemy import Table
import random
import string
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:yash152@localhost/book_exchange'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def generate_book_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    books = db.relationship('Book', backref='owner', lazy=True)

class Book(db.Model):
    __tablename__ = 'book'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.String(5), primary_key=True, default=generate_book_id)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    available = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    proposer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.String(5), db.ForeignKey('book.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"Book('{self.id}', '{self.title}', '{self.author}')"

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    submit = SubmitField('Add Book')

class ExchangeForm(FlaskForm):
    book_id = StringField('Book ID', validators=[DataRequired()])
    submit = SubmitField('Propose Exchange')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            return redirect(url_for('home'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required

def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/books', methods=['GET', 'POST'])
@login_required
def books():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(title=form.title.data, author=form.author.data, owner=current_user)
        db.session.add(book)
        db.session.commit()
        flash('Book added!', 'success')
        return redirect(url_for('books'))
    user_books = Book.query.filter_by(user_id=current_user.id).all()
    return render_template('books.html', books=user_books, form=form)

@app.route('/available_books')
def available_books():
    books = Book.query.filter_by(available=True).all()
    return render_template('available_books.html', books=books)

@app.route('/propose_exchange/<int:book_id>', methods=['POST'])
@login_required
def propose_exchange(book_id):
    book = Book.query.get_or_404(book_id)
    if book.available:
        notification = Notification(
            user_id=book.owner.id,
            proposer_id=current_user.id,
            book_id=book.id,
            message=f"{current_user.username} has proposed to exchange {book.title}."
        )
        db.session.add(notification)
        db.session.commit()
        flash('Exchange proposal sent!', 'success')
    else:
        flash('Book not available for exchange.', 'danger')
    return redirect(url_for('available_books'))

@app.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/view_books/<int:notification_id>')
@login_required
def view_books(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    proposer_books = Book.query.filter_by(user_id=notification.proposer_id, available=True).all()
    return render_template('view_books.html', proposer_books=proposer_books, notification=notification)

@app.route('/confirm_exchange/<int:notification_id>/<int:book_id>', methods=['POST'])
@login_required
def confirm_exchange(notification_id, book_id):
    notification = Notification.query.get_or_404(notification_id)
    proposer_book = Book.query.get_or_404(book_id)
    if proposer_book and proposer_book.available:
        proposer_book.available = False
        requested_book = Book.query.get_or_404(notification.book_id)
        requested_book.available = False
        # Notify both users
        confirm_notif = Notification(
            user_id=notification.proposer_id,
            proposer_id=current_user.id,
            book_id=proposer_book.id,
            message=f"{current_user.username} has accepted the exchange of {requested_book.title} for {proposer_book.title}."
        )
        db.session.add(confirm_notif)
        db.session.commit()
        flash('Exchange confirmed!', 'success')
    else:
        flash('Proposed book not available.', 'danger')
    return redirect(url_for('notifications'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
