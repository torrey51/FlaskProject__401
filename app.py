from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Regexp
from werkzeug.security import generate_password_hash 
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import werkzeug
from werkzeug.exceptions import HTTPException


app= Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'

# # Sentry SDK
# sentry_sdk.init('https://4502af8bc3c26c72d3c830cbb2d74ac7@o4508139583700992.ingest.us.sentry.io/4508139586846720', integrations=[FlaskIntegration()])

# class InsufficientEmail(werkzeug.exceptions.HTTPException):
#     code = 1062
#     description = "Email already in use."


# @app.errorhandler(HTTPException)
# def handle_1062(error):
#     flash(error.description, 'error')
#     return render_template('account.html')

# raise InsufficientEmail()


# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/stockwebsite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Creating a Stock table
class Stock(db.Model):
    stock_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(80), nullable=False)
    ticker_symbol = db.Column(db.String(4), nullable=False)
    initial_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)

#Calculates the market capitalization
    @property
    def market_capitalization(self):
        return self.current_price * self.volume

# Flask-WTF form for handling user input for stocks
class StockForm(FlaskForm):
    company_name = StringField('Name', validators=[DataRequired()])
    ticker_symbol = StringField('ticker_symbol',validators=[DataRequired()])
    initial_price = StringField('initial_price',validators=[DataRequired()])
    current_price = StringField('current_price',validators=[DataRequired()])
    volume = StringField('volume',validators=[DataRequired()])
    submit = SubmitField('Submit')


# Creating a market hours table
class Hours(db.Model):
    hour_id = db.Column(db.Integer, primary_key=True)
    open_day = db.Column(db.String(9), nullable=False)
    close_day = db.Column(db.String(9), nullable=False)
    open_hour = db.Column(db.Integer, nullable=False)
    close_hour = db.Column(db.Integer, nullable=False)

# Flask-WTF form for handling user input for changing market hours
class HoursForm(FlaskForm):
    open_day = StringField('open_day', validators=[DataRequired()])
    close_day = StringField('close_day', validators=[DataRequired()])
    open_hour = StringField('open_hour', validators=[DataRequired()])
    close_hour = StringField('close_hour', validators=[DataRequired()])
    submit = SubmitField('submit')


# Creating a User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('customer', 'admin', name='user_type_enum'), nullable=False)

# Flask-WTF form for handling user input for creating a user account
class UserForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    # Email field has a regular expression to validate that the user input is an email
    email = StringField('Email', validators=[DataRequired(), Regexp('^[a-zA-Z0-9_.±]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$', message='Must enter and email address')])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Create')


#route 1 (page 1) #Home
@app.route('/')
def home():
    return render_template('home.html')

#route 2 (page 2) market
@app.route('/market')
def market():   
    db.create_all()
    stocks = Stock.query.all()
    last_hour = Hours.query.order_by(Hours.hour_id.desc()).first()
    return render_template('market.html', stocks=stocks, last_hour=last_hour)

#route 3 (page 3) buying stock
@app.route("/buy-stock/<int:id>", methods=["GET", "POST"])
def buy_stock(id):
    stock = Stock.query.get_or_404(id)
    form = StockForm(obj=stock)
    if form.validate_on_submit():
        stock.company_name = form.company_name.data
        stock.ticker_symbol = form.ticker_symbol.data
        stock.initial_price = float(form.initial_price.data)
        stock.current_price = float(form.current_price.data)
        stock.volume = float(form.volume.data)
        db.session.commit()
        flash('Stock Purchase successfull!')
        return redirect(url_for('market'))
    return render_template("buy_stock.html", form=form, stock=stock)

#Route 4 (page 4) admin market page
@app.route('/admin_market', methods=["GET", "POST"])
def admin_market():
    stocks = Stock.query.all()
    last_hour = Hours.query.order_by(Hours.hour_id.desc()).first()
    return render_template("admin_market.html", stocks=stocks, last_hour=last_hour)

#Route 5 (page 5) adding stock
@app.route("/add-stock", methods=["GET", "POST"])
def add_stock():
    form = StockForm()
    if form.validate_on_submit():
        new_stock = Stock(
            company_name=form.company_name.data,
            ticker_symbol=form.ticker_symbol.data,
            initial_price=float(form.initial_price.data),
            current_price=float(form.current_price.data),
            volume=float(form.volume.data)
        )
        db.session.add(new_stock)
        db.session.commit()
        flash('Stock addes successfully!')
        return redirect(url_for('admin_market'))
    return render_template("add_stock.html", form=form)

#Route 6 deleting stock
@app.route("/delete-stock/<int:id>")
def delete_stock(id):
    stock = Stock.query.get_or_404(id)
    db.session.delete(stock)
    db.session.commit()
    flash('Stock deleted sucessfully!')
    return redirect(url_for('admin_market'))

#Route 7 (page 6) updating stock
@app.route("/update-stock/<int:id>", methods=["GET", "POST"])
def update_stock(id):
    stock = Stock.query.get_or_404(id)
    form = StockForm(obj=stock)
    if form.validate_on_submit():
        stock.company_name = form.company_name.data
        stock.ticker_symbol = form.ticker_symbol.data
        stock.initial_price = float(form.initial_price.data)
        stock.current_price = float(form.current_price.data)
        stock.volume = float(form.volume.data)
        db.session.commit()
        flash('Stock Updated successfully!')
        return redirect(url_for('admin_market'))
    return render_template("update_stock.html", form=form, stock=stock)

#Route 8 (page 7) changing market hours
@app.route("/change-market-hours", methods=["GET", "POST"])
def change_hours():
    form = HoursForm()
    if form.validate_on_submit():
        new_schedule = Hours(
            open_day=form.open_day.data,
            close_day=form.close_day.data,
            open_hour=int(form.open_hour.data),
            close_hour=int(form.close_hour.data)
        )
        db.session.add(new_schedule)
        db.session.commit()
        flash('Market hours added successfully!')
        return redirect(url_for('admin_market'))
    return render_template("change_market_hours.html", form=form)

#route 9 (page 8) portfolio page
@app.route('/portfolio')
def portfolio():
    about = ['Seth Torrey', 'IFT 401 Capstone']
    return render_template('portfolio.html', portfolio=portfolio)

#route 10 (page 9) creating account page
@app.route('/account', methods=["GET", "POST"])
def account():
    form = UserForm()
    if form.validate_on_submit():
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            user_type='customer'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!')
        return redirect(url_for('market'))
    return render_template('account.html', form=form)


#route 11 (page 10) creating admin account
@app.route('/admin_account', methods=["GET", "POST"])
def admin_account():
    form = UserForm()
    if form.validate_on_submit():
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            user_type='admin'
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!')
        return redirect(url_for('admin_market'))
    return render_template('admin_account.html', form=form)
