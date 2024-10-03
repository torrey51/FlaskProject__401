from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app= Flask(__name__)

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