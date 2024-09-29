from flask import Flask, render_template, request
app= Flask(__name__)


#route 1 (page 1) #Home
@app.route('/')
def home():
    return render_template('home.html')

#route 2 (page 2) #market
@app.route('/market')
def market():   
    contact = request.args.get('market')
    return render_template('market.html', market=market)

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