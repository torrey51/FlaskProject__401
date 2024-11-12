from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TimeField, IntegerField, DecimalField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Regexp, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
import werkzeug
from werkzeug.exceptions import HTTPException
import random
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
from datetime import datetime, time, date
import holidays
from decimal import Decimal
import os


app= Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'

# Initializing the LoginManager: https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login
login_manager = LoginManager()
login_manager.init_app(app)
# redirects the users to the home login page if they are not signed in
login_manager.login_view = 'home'
login_manager.login_message_category = 'info'

# Sets the timezone to Mountain Standard time
os.environ['TZ'] = 'America/Phoenix'

# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/stockwebsite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Creating a Stock table
class Stock(db.Model):
    __tablename__ = 'stock'
    stock_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(80), nullable=False)
    ticker_symbol = db.Column(db.String(4), nullable=False)
    initial_price = db.Column(db.DECIMAL(13, 2), nullable=False)
    current_price = db.Column(db.DECIMAL(13, 2), nullable=False)
    volume = db.Column(db.DECIMAL(13, 2), nullable=False)
    daily_high = db.Column(db.DECIMAL(13, 2), nullable=True)
    daily_low = db.Column(db.DECIMAL(13, 2), nullable=True)

#Calculates the market capitalization
    @property
    def market_capitalization(self):
        return round(self.current_price * self.volume, 2)
    
#Function for fluctuating the current stock price
def fluctuate_price():
    with app.app_context():
        # Queries all the stocks in the Stock table
        stocks = Stock.query.all()
        # For loop to iterate through the stocks in the Stocks table
        for stock in stocks:
            # fluctuate is set to get a random number between -10 and 10 
            fluctuate = Decimal(random.uniform(-5, 5))
            # The random number is then added to or subtracted from the current price 
            stock.current_price += fluctuate
            # rounds the current price to only use 2 decimal places
            stock.current_price = round(stock.current_price, 2)

            # Sets the daily high to 0 if the value in the database table is null
            if stock.daily_high is None:
                stock.daily_high = 0
            # Sets the daily low to 0 if the value in the database is null
            if stock.daily_low is None:                
                stock.daily_low = stock.current_price

            # If the current price of the stock is higher than the daily_high then that current price becomes the new daily_high
            if stock.current_price > stock.daily_high:
                stock.daily_high = stock.current_price
            # If the current price of the stock is lower than the daily_low then that current price becomes the new daily_low
            if stock.current_price < stock.daily_low:
                stock.daily_low = stock.current_price 
        db.session.commit()

# Function for reseting the daily high and low to the current price of the stock so that the daily values reset everyday 
def reset_daily_price():
    with app.app_context():
        # Queries all of the stocks in the Stock table
        stocks = Stock.query.all()
        # For loop to iterate through all of the stocks in the Stocks table
        for stock in stocks:
            # Resets the daily low and high to the current price of the stock
            stock.daily_high = stock.current_price
            stock.daily_low = stock.current_price
        db.session.commit()

# Creates the scheduler 
sched = BackgroundScheduler(timezone=timezone('America/Phoenix'), daemon=True)
# runs the fluctuate_price function every 5 minutes. Using interval to specify when to fluctuate the prices.
sched.add_job(fluctuate_price, 'interval', minutes=5)
# Runs the reset_daily_price function at midnight everyday. Using cron to specify the certain time of day I want it to run
sched.add_job(reset_daily_price, 'cron', hour=0, minute=0)
# Starts the scheduler
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

    # Checks that the current day is one of the days the market is open. M-F closed on weekends
    if current_day in open_days:
        # Queries the database to get the hours
        market_hours = Hours.query.order_by(Hours.hour_id.desc()).first()
        # return if the current time is between the open and closing hours
        return market_hours.open_hour <= current_time <= market_hours.close_hour
    # else then the market is closed and users should not be able to buy and sell stocks
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
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('customer', 'admin', name='user_type_enum'), nullable=False)

    # Creates a 1 to 1 relationship between the user and the cash account. Each user will only have one cash account associated with their user profile
    cash_account = db.relationship('Cash_Account', backref='user', uselist=False)
    # Creates a 1 to many relationship betweent the user and transactions. Users can have many transactions
    transactions = db.relationship('Transaction', back_populates='user', lazy=True)

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

# Creating cash account table
class Cash_Account(db.Model):
    cashAccount_id = db.Column(db.Integer, primary_key=True)
    # user_id is a foreignKey in the Cash_Account table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    balance = db.Column(db.DECIMAL(13,2), nullable=False)

# Creating form to add funds
class AddFunds(FlaskForm):
    add_balance = DecimalField('Amount', places=2, validators=[DataRequired()])
    add_submit = SubmitField('Add Funds')

# Creating form to withdraw funds
class WithdrawFunds(FlaskForm):
    withdraw_balance = DecimalField('Amount', places=2, validators=[DataRequired()])
    withdraw_submit = SubmitField('Withdraw Funds')

# Creating Funds transaction table
class FundTransaction(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True)
    # User id is a foreign key in the FundTransaction table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.DECIMAL(13,2), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    # Creates a one to many relationship between user and fund transactions. Users can have many fund transactions
    user = db.relationship('User', backref='fund_transactions')


# Creating transaction table
class Transaction(db.Model):
    __tablename__ = 'transaction'
    transaction_id = db.Column(db.Integer, primary_key=True)
    # user_id is a ForeignKey in the Transaction Table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # stock_id is a ForeignKey in the Transaction Table
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.stock_id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    volume = db.Column(db.DECIMAL(13, 2), nullable=False)
    price_at_transaction = db.Column(db.DECIMAL(13, 2), nullable=False)
    funds = db.Column(db.DECIMAL(13, 2), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    # Creates a one to many relationship between the user and transaciton. User can have many transactions 
    user = db.relationship('User', back_populates='transactions')
    # Creates a one to many relationship between stock and transaction. Stock can be associated with multiple transactions
    stock = db.relationship('Stock', backref='transactions')


# Creating a form for handling funds
class FundTransactionFrom(FlaskForm):
    Transaction_type = SelectField('Transaction Type', choices=[('deposit', 'Deposit'), ('withdraw', 'Withdraw')], validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Submit')

# Creating a form for handling stock transactions
class StockTransactionForm(FlaskForm):
    stock_id = SelectField('Stock', coerce=int, validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[('buy', 'Buy'), ('sell', 'Sell')], validators=[DataRequired()])
    volume = DecimalField('Volume', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit')

# Creating a table for the stocks that a user owns
class UserStock(db.Model):
    __tablename__ = 'user_stock'
    id = db.Column(db.Integer, primary_key=True)
    # user_id is a ForeignKey in the UserStock table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # stock_id is a ForeignKey in the UsetStock table
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.stock_id'), nullable=False)
    volume = db.Column(db.DECIMAL(13, 2), nullable=False)

    # Creates a one to many relationship between user and user stocks. Users can have many stocks
    user = db.relationship('User', backref='user_stocks')
    # Creates a one to many relationship between stock and user stocks. Stocks can have many users
    stock = db.relationship('Stock', backref='user_stocks')


#route 1 (page 1) #Home
@app.route('/', methods=["GET", "POST"])
def home():
    login_error = None
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
            return redirect(url_for('market'))
        else:
            login_error = "User name or password is incorrect try again or create a new account if you are a first time user"
    return render_template('home.html', form=form, login_error=login_error)

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

@app.route("/buy-stock/<int:stock_id>", methods=["GET", "POST"])
@login_required
def buy_stock(stock_id):
    # Queries the Stock table and retreives the stock_id
    stock = Stock.query.get(stock_id)
    buy_error = None
    cash_account = Cash_Account.query.filter_by(user_id=current_user.id).first()
    balance = cash_account.balance
    
    # If statement to only run the below code if the form is submitted 
    if request.method == "POST":
        # Retrieves the volume from the form used to buy stock. Form is specefied in the buy_stock.html
        volume = request.form.get('volume', type=int)  

        # If the market is not open then flash message and return to market page
        if not market_open():
            flash("Sorry, market is closed due to either holiday or outside of current market hours. Try again once the market is open.", "danger")
            return redirect(url_for('market'))
        
        # total cost of stock is current price of the stock multiplied by the volume you are buying at 
        total_cost = stock.current_price * Decimal(volume)

        # If the user doesn't have enough available cash redirect to market page and flash insufficient funds message
        if current_user.cash_account.balance < total_cost:
            buy_error = "Sorry, you don't have sufficient funds to purchase stock. Check your current balance and try again:"
            return render_template('buy_stock.html', stock=stock, buy_error=buy_error, balance=balance)
        
        # Get the users cash account balance and subtract the total cost 
        current_user.cash_account.balance -= total_cost
        
        # Quering the database to see if user already has a stock purchased
        user_stock = UserStock.query.filter_by(user_id=current_user.id, stock_id=stock_id).first()
        # If user_stock exists
        if user_stock:
            # Updates the volume of the stock if the stock already exists in the UserStock table
            user_stock.volume += Decimal(volume)
        # If user_stock doesn't exist create a user_stock with current user_id, stock_id, and volume 
        else:
            user_stock = UserStock(user_id=current_user.id, stock_id=stock_id, volume=Decimal(volume))
            # Adding the new user_stock to the session
            db.session.add(user_stock)

        # Set the variable new_transaction with the userid, stocks id, transaction type, the volume, the price at transaction, and the total funds for when a stock is purchased
        new_transaction = Transaction(user_id=current_user.id, stock_id=stock_id, transaction_type='buy', volume=volume, price_at_transaction=stock.current_price, funds=total_cost)
        # Adding the new_transaction to the session
        db.session.add(new_transaction)
        # Add volume to the stock when a stock is purchased
        stock.volume += volume
        # Commits all the changes to the database
        db.session.commit()
        
        # Redirects to the market once a stock is bought
        return redirect(url_for('market')) 
    
    return render_template("buy_stock.html", stock=stock, buy_error=buy_error, balance=balance, current_user=current_user)

@app.route("/sell-stock/<int:stock_id>", methods=["GET", "POST"])
@login_required
def sell_stock(stock_id):
    # Queries the Stock table and retreives the stock_id
    stock = Stock.query.get(stock_id)
    # Sets the sell error to none to initialize 
    sell_error = None
    # Queries the cash account by the current user id
    cash_account = Cash_Account.query.filter_by(user_id=current_user.id).first()
    # Sets the balance variable to the current balance in the user cash account
    balance = cash_account.balance
    
    # Queriers the transaction table to get the most recent transaction for the user and the stock they are selling
    transaction = Transaction.query.filter_by(user_id=current_user.id, stock_id=stock_id).order_by(Transaction.transaction_id.desc()).first()

    # If statement to only run the below code if the form is submitted 
    if request.method == "POST":
        # Retrieves the volume from the form used to sell stock. Form is specefied in the sell_stock.html
        volume_to_sell = request.form.get('volume', type=int)  

        # If market isn't open then redirect back to the portfolio page and then flash error message
        if not market_open():
            flash("Sorry, market is closed due to either holiday or outside of current market hours. Try again once the market is open.", "danger")
            return redirect(url_for('market'))
        
        # Queries the user stock and filters by the user id and stock id 
        user_stock = UserStock.query.filter_by(user_id=current_user.id, stock_id=stock_id).first()

        # If the user is trying to sell more stocks than they currently own then give this error
        if volume_to_sell > user_stock.volume:
            sell_error = "You can't sell more stocks than you currently own"
            return render_template('sell_stock.html', stock=stock, sell_error=sell_error, balance=balance, transaction=transaction)

        # Current price is the stocks current price
        current_price = stock.current_price
        # calculates the sell value based on the stocks current price and the volume the user is selling
        sell_value = current_price * Decimal(volume_to_sell)

        # Update user's cash account balance
        current_user.cash_account.balance += sell_value
        
        # Update or delete user's stock volume
        user_stock.volume -= Decimal(volume_to_sell)
        if user_stock.volume == 0:
            db.session.delete(user_stock)
        
        # Record the transaction in the Transaction database
        new_transaction = Transaction( user_id=current_user.id, stock_id=stock_id, transaction_type='sell', volume=volume_to_sell, price_at_transaction=current_price, funds=sell_value)
        db.session.add(new_transaction)
        # Subtracts volume from the stock 
        stock.volume -= volume_to_sell
        db.session.commit()

        return redirect(url_for('portfolio')) 
    
    return render_template("sell_stock.html", stock=stock, sell_error=sell_error, balance=balance, transaction=transaction)

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
@app.route('/portfolio', methods=["GET", "POST"])
@login_required
def portfolio():
    # prints the user id of the user that is signed in. Used for testing outputs in the terminal
    print("Current User ID:", current_user.id)
    # Queries the Cash_Account table to retrieve the cash account that is associated with the signed in user and assigns it to the cash_account variable. Uses the user_id to filter the table.
    cash_account = Cash_Account.query.filter_by(user_id=current_user.id).first()
    # Initializes the balance variable, if a cash account already exists use the cash account balance, but if no cash account yet set the balance to 0
    balance = cash_account.balance if cash_account else 0

    # Queries the UserStock table to retrieve the stocks that are associated with the signed in user
    user_stocks = UserStock.query.filter_by(user_id=current_user.id).all()

    # Creates and empty list to store the portfolio items
    portfolio_items = []
    # Loops through all the user's stock to retrieve the stock details and the transactions associated with the stock
    for user_stock in user_stocks:
        # Queries the Stock table to get the stocks based on the stock_id
        stock = Stock.query.get(user_stock.stock_id)
        # Queries the Transaction table to find the first buy transaction for the current stock
        transaction = Transaction.query.filter_by(user_id=current_user.id, stock_id=stock.stock_id, transaction_type='buy').first()
        # If the stock already exists in the Transaction table then append a dictionary with the stock and transaction information to the portfolio items list
        if stock and transaction:
            portfolio_items.append({
                'stock': stock, #Stores the stock object
                'volume': user_stock.volume, #Stores the stock volume that is owned by the user
                'total_value': stock.current_price * user_stock.volume, #Calculates the total value of the stock based on the current price and the volume of stock
                'transaction_id': transaction.transaction_id #Stores the transaction id
            })
        # Prints the porfolip_items for testing. Should match up with what is in the active stocks table on the portfolio page
        print(portfolio_items)

    # Creating the instance of the forms used for adding and withdrawing funds
    add_form = AddFunds()
    withdraw_form = WithdrawFunds()

    # If statement to handel the form submission for adding funds to the users cash accoount
    if add_form.validate_on_submit() and add_form.add_submit.data:
        # Prints the cash accout id, user id, and the users current balance for. Used for testing outputs in the terminal
        # print("Cash Account:", cash_account.cashAccount_id, cash_account.user_id, cash_account.balance)

        # If a cash account already exists for a user it will add the cash to their current balance
        if cash_account:
            # adding to the cash accout balance
            cash_account.balance += Decimal(add_form.add_balance.data)
        # If a cash account does not already exists for a user it will create the cash account and add the initial funds
        else:
            cash_account = Cash_Account(user_id=current_user.id, balance=Decimal(add_form.add_balance.data))
            # Adds a new cash account to the database
            db.session.add(cash_account)

        # Creating a fund transaction record for adding funds to acount
        fund_transaction = FundTransaction(user_id=current_user.id, transaction_type='add', amount=Decimal(add_form.add_balance.data))
        # Adds the fund transaction to the database
        db.session.add(fund_transaction)

        # Commits all changes to the database
        db.session.commit()
        # Redirects back to the portfolio page after adding funds
        return redirect(url_for('portfolio'))

    # elif statement for the withdraw form
    elif withdraw_form.validate_on_submit() and withdraw_form.withdraw_submit.data:
        # If the cash account exists and the balance is greater than or eqaul to the amount you want to withdraw then subtract the cash accout balance from the integer
        # that was in the put in the withdraw form
        if cash_account and cash_account.balance >= Decimal(withdraw_form.withdraw_balance.data):
            cash_account.balance -= Decimal(withdraw_form.withdraw_balance.data)

            fund_transaction = FundTransaction(user_id=current_user.id, transaction_type='withdraw', amount=Decimal(withdraw_form.withdraw_balance.data))
            db.session.add(fund_transaction)

            db.session.commit()
        return redirect(url_for('portfolio'))
    
    # Queries the fund transaction table for only the user that is currently signed in by filtering by the user id
    fund_transactions = FundTransaction.query.filter_by(user_id=current_user.id).all()
    # Queries the transaction table for only the user that is currently signed in by filtering by the user id
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    # Creates and empty list to store the transaction data
    transaction_data = []
    # for the transactions in the trasnaction table it will appened the stock name, the transaction type, volume bought or sold, the price at transaction, the total amount spent, and the time the stock was bought or sold
    for transaction in transactions:
        # Queries all of the stocks by their stock_id
        stock = Stock.query.get(transaction.stock_id)
        transaction_data.append({
            'stock_name': stock.company_name,
            'transaction_type': transaction.transaction_type,
            'volume': transaction.volume,
            'price_at_transaction': transaction.price_at_transaction,
            'funds': transaction.funds,
            'timestamp': transaction.timestamp
        })
    
    print("balance", balance)
    return render_template('portfolio.html', balance=balance, current_user=current_user, add_form=add_form, withdraw_form=withdraw_form, transaction_data=transaction_data, portfolio_items=portfolio_items, fund_transactions=fund_transactions)

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
        # Will redirect the user back to the admin_market page after submitting
        return redirect(url_for('admin_market'))
    return render_template('admin_account.html', form=form)

#Route 12 logging out the user
@app.route("/logout")
@login_required
def logout():
    # logs the user out
    logout_user()
    # redirects to the home page if signed out
    return redirect(url_for('home'))