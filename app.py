from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Regexp
from werkzeug.security import generate_password_hash, check_password_hash
import werkzeug
from werkzeug.exceptions import HTTPException
import random
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, date
import holidays


app= Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'

# Initializing the LoginManager: https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login
login_manager = LoginManager()
login_manager.init_app(app)
# redirects the users to the home login page if they are not signed in
login_manager.login_view = 'home'
login_manager.login_message_category = 'info'

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
    
#Function for fluctuating the current stock price
def fluctuate_price():
    with app.app_context():
        stocks = Stock.query.all()
        for stock in stocks:
            # fluctuate is set to get a random number between -10 and 10 
            fluctuate = random.uniform(-10, 10)
            # The random number is then added to or subtracted from the current price 
            stock.current_price += fluctuate
            # rounds the current price to only use 2 decimal places
            stock.current_price = round(stock.current_price, 2)
        db.session.commit()

sched = BackgroundScheduler(daemon=True)
sched.add_job(fluctuate_price, 'interval', minutes=5)
sched.start()

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
    open_hour = db.Column(db.Time, nullable=False)
    close_hour = db.Column(db.Time, nullable=False)

def market_open():
    # Gets the current date and time
    time_now = datetime.now()
    # Gets the current day of the week 
    current_day = time_now.strftime("%A")
    # Gets the current time 
    current_time = time_now.time()
    # Getting the current year
    current_year = datetime.now().year
    # Get the current date
    current_date = time_now.date()

    # Creates a variable holiday_dates to store the us calendar holidays for the whatever the current year it is 
    # Using a set to store all of the holidays in one variable, and using the .keys() to only get the dates and not include the holiday names
    holiday_dates = set(holidays.US(years=current_year).keys())

    # Specifies the days when the market is allowed to be open no weekends
    open_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Prints the current day, current time, the holiday dates, and the current date for testing purposes
    print("current day:", current_day)
    print("current time:", current_time)
    print(holiday_dates)
    print("Current date", current_date)

    # If the current_date is in the holiday dates then the market is closed
    if current_date in holiday_dates:
        return False

    # Checks that the current day is one of the days the market is open. M-W closed on weekends
    if current_day in open_days:

        # Queries the database to get the hours
        market_hours = Hours.query.order_by(Hours.hour_id.desc()).first()

        # If a weekday check to see if its within the market hours
        return market_hours.open_hour <= current_time <= market_hours.close_hour
    # else then false and the market is closed and users should not be able to buy and sell stocks
    else:
        return False

# Flask-WTF form for handling user input for changing market hours
class HoursForm(FlaskForm):
    open_day = StringField('Open Day', validators=[DataRequired()])
    close_day = StringField('Close Day', validators=[DataRequired()])
    open_hour = TimeField('Open Hour', format='%H:%M', validators=[DataRequired()])
    close_hour = TimeField('Close Hour', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('submit')

# Creating a User model
class User(db.Model, UserMixin):
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

# Form for logging in
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# User loader function that will retreive the user by their ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#route 1 (page 1) #Home
@app.route('/', methods=["GET", "POST"])
def home():
    # If the user is already signed in when visiting the website they will be redirected to the portfolio page instead of being shown the home page
    if current_user.is_authenticated:
        return redirect(url_for('portfolio'))
    # Form for loggin in as a user, will be redirected to the market page once logged in, and flashses a success message on the market page
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # Checks to see if the hashed passwords match each other, if they do user will be logged in
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('market'))
        else:
            flash('Login failed. Check your email and password', 'danger')
    return render_template('home.html', form=form)

#route 2 (page 2) market
@app.route('/market')
@login_required
def market():   
    # Creates the tables in the database 
    db.create_all()
    # queries all the stocks from the stock table 
    stocks = Stock.query.all()
    # queries the Hours table to take the most recent update to the stock market hours 
    last_hour = Hours.query.order_by(Hours.hour_id.desc()).first()
    return render_template('market.html', stocks=stocks, last_hour=last_hour)

#route 3 (page 3) buying stock
@app.route("/buy-stock/<int:id>", methods=["GET", "POST"])
def buy_stock(id):
    if not market_open():
        flash("Market is closed", "danger")
        return redirect(url_for('market'))
    stock = Stock.query.get_or_404(id)
    # Form for buying the stocks (not completed need to figure out how to buy stocks)
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
@login_required
def admin_market():
    # Checks if the current user is an admin or not. Will only let admins view the admin market pages. redirects the users to the market if not an admin
    if current_user.user_type != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('market'))
    
    stocks = Stock.query.all()
    last_hour = Hours.query.order_by(Hours.hour_id.desc()).first()
    return render_template("admin_market.html", stocks=stocks, last_hour=last_hour)

#Route 5 (page 5) adding stock
@app.route("/add-stock", methods=["GET", "POST"])
def add_stock():
    # Form for creating a new stock to add to the database
    form = StockForm()
    if form.validate_on_submit():
        new_stock = Stock(
            company_name=form.company_name.data,
            ticker_symbol=form.ticker_symbol.data,
            initial_price=float(form.initial_price.data),
            current_price=float(form.current_price.data),
            volume=float(form.volume.data)
        )
        # Adds the new stock to the database once the form is submitted
        db.session.add(new_stock)
        db.session.commit()
        flash('Stock addes successfully!')
        return redirect(url_for('admin_market'))
    return render_template("add_stock.html", form=form)

#Route 6 deleting stock
@app.route("/delete-stock/<int:id>")
def delete_stock(id):
    stock = Stock.query.get_or_404(id)
    # Deletes the stock from the database and commits 
    db.session.delete(stock)
    db.session.commit()
    flash('Stock deleted sucessfully!')
    return redirect(url_for('admin_market'))

#Route 7 (page 6) updating stock
@app.route("/update-stock/<int:id>", methods=["GET", "POST"])
def update_stock(id):
    stock = Stock.query.get_or_404(id)
    # populates the stockfrom with the stocks data that was selected
    form = StockForm(obj=stock)
    # Form for updating the stock information
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
    # form for changing the market hours
    form = HoursForm()
    if form.validate_on_submit():
        new_schedule = Hours(
            open_day=form.open_day.data,
            close_day=form.close_day.data,
            open_hour=form.open_hour.data,
            close_hour=form.close_hour.data
        )
        # adds the new market hours to the database and commits
        db.session.add(new_schedule)
        db.session.commit()
        flash('Market hours added successfully!')
        return redirect(url_for('admin_market'))
    return render_template("change_market_hours.html", form=form)

#route 9 (page 8) portfolio page
@app.route('/portfolio')
@login_required
def portfolio():
    return render_template('portfolio.html', portfolio=portfolio, current_user=current_user)

#route 10 (page 9) creating account page
@app.route('/account', methods=["GET", "POST"])
def account():
    # Form for creating a new user, will set the account as customer since it was created on the customer account page
    form = UserForm()
    if form.validate_on_submit():
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            # Hashes the users password when the accout is created
            password=generate_password_hash(form.password.data),
            # Sets the user type to customer
            user_type='customer'
        )
        # Adds the user to the database and commits
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!')
        return redirect(url_for('home'))
    return render_template('account.html', form=form)


#route 11 (page 10) creating admin account
@app.route('/admin_account', methods=["GET", "POST"])
def admin_account():
    # for for creating a admin account, will set the account as admin since it was created on the admin accout page
    form = UserForm()
    if form.validate_on_submit():
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            # Hashes the password when the accout is created
            password=generate_password_hash(form.password.data),
            # Sets the user type to admin
            user_type='admin'
        )
        # Adds the user to the datbase and commits
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!')
        # Will redirect the user back to the admin_market page after submitting
        return redirect(url_for('admin_market'))
    return render_template('admin_account.html', form=form)

#Route 12 logging out the user
@app.route("/logout")
@login_required
def logout():
    # logs the user out
    logout_user()
    flash('You have been logged out.', 'info')
    # redirects to the home page if signed out
    return redirect(url_for('home'))