from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email

app= Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'


# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/stockwebsite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Creating a Stock
class Stock(db.Model):
    stock_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(80), nullable=False)
    ticker_symbol = db.Column(db.String(4), nullable=False)
    initial_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)


# Flask-WTF form for handling user input
class StockForm(FlaskForm):
    stock_id = StringField('stock_id', validators=[DataRequired()])
    company_name = StringField('Name', validators=[DataRequired()])
    ticker_symbol = StringField('ticker_symbol',validators=[DataRequired()])
    initial_price = StringField('initial_price',validators=[DataRequired()])
    current_price = StringField('current_price',validators=[DataRequired()])
    volume = StringField('volume',validators=[DataRequired()])
    submit = SubmitField('Submit')

#route 1 (page 1) #Home
@app.route('/')
def home():
    return render_template('home.html')

#route 2 (page 2) #market
@app.route('/market')
def market():   
    contact = request.args.get('market')
    db.create_all()
    # Creating a stock in the stock database
    # new_stock = Stock(company_name='NVIDIA Corp', ticker_symbol='NVDA', initial_price=108.10, current_price=108.10, volume=262664898)
    # db.session.add(new_stock)
    # db.session.commit()
    stocks = Stock.query.all()
    return render_template('market.html', stocks=stocks)

#Route for the admin market page
@app.route('/admin_market', methods=["GET", "POST"])
def admin_market():
    form = StockForm()
    if form.validate_on_submit():
        # Create a new Stock object using form data
        new_stock = Stock(
            stock_id=form.stock_id.data,
            company_name=form.company_name.data,
            ticker_symbol=form.ticker_symbol.data,
            initial_price=float(form.initial_price.data),
            current_price=float(form.current_price.data),
            volume=float(form.volume.data)
        )

        # Add new stock to the database
        db.session.add(new_stock)
        db.session.commit()

        flash('Stock added successfully!')
        return redirect(url_for('admin_market'))  # Redirect after success

    return render_template('admin_market.html', form=form)


#route 3 (page 3) #about
@app.route('/portfolio')
def portfolio():
    about = ['Seth Torrey', 'IFT 401 Capstone']
    return render_template('portfolio.html', portfolio=portfolio)

#route 3 (page 3) #account
@app.route('/account')
def account():
    about = ['Seth Torrey', 'IFT 401 Capstone']
    return render_template('account.html', account=account)

#route 3 (page 3) #admin
@app.route('/admin')
def admin():
    about = ['Seth Torrey', 'IFT 401 Capstone']
    return render_template('admin.html', admin=admin)


#route 34 (page 4) #test
@app.route('/test')
def test():
    tests = ['']
    return render_template('test.html', tests=tests)

# route 2: Add User
@app.route("/add-user", methods=["GET", "POST"])
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        new_user = User(name=form.name.data, email=form.email.data)
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully!')
        return redirect(url_for('index'))
    return render_template("admin_market.html", form=form)