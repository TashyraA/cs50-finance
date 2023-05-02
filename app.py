import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

from datetime import datetime, timezone

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Create new table, and index (for efficient search later on) to keep track of stock orders, by each user
db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER, user_id NUMERIC NOT NULL, symbol TEXT NOT NULL, \
            shares NUMERIC NOT NULL, price NUMERIC NOT NULL, timestamp TEXT, PRIMARY KEY(id), \
            FOREIGN KEY(user_id) REFERENCES users(id))")
db.execute("CREATE INDEX IF NOT EXISTS orders_by_user_id_index ON orders (user_id)")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    owns = own_shares()
    total = 0
    for symbol, shares in owns.items():
        result = lookup(symbol)
        name, price = result["name"], result["price"]
        stock_value = shares * price
        total += stock_value
        owns[symbol] = (name, shares, usd(price), usd(stock_value))
    cash = db.execute("SELECT cash FROM users WHERE id = ? ",
                      session["user_id"])[0]['cash']
    total += cash
    return render_template("index.html", owns=owns, cash=usd(cash), total=usd(total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not (symbol := request.form.get("symbol")):
            return apology("MISSING SYMBOL")

        if not (shares := request.form.get("shares")):
            return apology("MISSING SHARES")

        # Check share is numeric data type
        try:
            shares = int(shares)
        except ValueError:
            return apology("INVALID SHARES")

        # Check shares is positive number
        if not (shares > 0):
            return apology("INVALID SHARES")

        # Ensure symbol is valided
        if not (query := lookup(symbol)):
            return apology("INVALID SYMBOL")

        rows = db.execute("SELECT * FROM users WHERE id = ?;",
                          session["user_id"])

        user_owned_cash = rows[0]["cash"]
        total_prices = query["price"] * shares

        # Ensure user have enough money
        if user_owned_cash < total_prices:
            return apology("CAN'T AFFORD")

        # Execute a transaction
        db.execute("INSERT INTO transactions(user_id, company, symbol, shares, price) VALUES(?, ?, ?, ?, ?);",
                   session["user_id"], query["name"], symbol, shares, query["price"])

        # Update user owned cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?;",
                   (user_owned_cash - total_prices), session["user_id"])

        flash("Bought!")

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute(
        "SELECT symbol, shares, price, timestamp FROM orders WHERE user_id = ?", session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Ensure Symbol is exists
        if not (query := lookup(request.form.get("symbol"))):
            return apology("INVALID SYMBOL")

        return render_template("quote.html", query=query)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    # check username and password
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    if username == "" or len(db.execute('SELECT username FROM users WHERE username = ?', username)) > 0:
        return apology("Invalid Username: Blank, or already exists")
    if password == "" or password != confirmation:
        return apology("Invalid Password: Blank, or does not match")
    # Add new user to users db (includes: username and HASH of password)
    db.execute('INSERT INTO users (username, hash) \
            VALUES(?, ?)', username, generate_password_hash(password))
    # Query database for username
    rows = db.execute("SELECT * FROM users WHERE username = ?", username)
    # Log user in, i.e. Remember that this user has logged in
    session["user_id"] = rows[0]["id"]
    # Redirect user to home page
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""



    if request.method == "POST":



        if not request.form.get("shares"):
            return apology("Please enter share amount")
        elif not request.form.get("symbol"):
            print("hello")
            return apology("Please enter a stock symbol")


        query = lookup(request.form.get("symbol"))

        if not query:
            return apology("Not a valid stock symbol")
        else:

            '''retrieve the amount of cash that the user has'''
            cash = db.execute("SELECT cash FROM users WHERE id = :sessionid", sessionid = session["user_id"])

            '''break that amount of cash out of the value pair'''
            cashVal = cash[0]['cash']

            '''get the number of shares the user wants to sell from the form'''
            amount = int(request.form.get("shares"))
            '''caluclate the total dollar amount of the shares being sold; # of shares * price of share'''
            price = float(query['price']) * int(amount)

            '''calculate the amount of cash we'll be left with'''
            cashVal = cashVal + price


            symbol = query['symbol']
            name = query['name']
            currAmt = db.execute("SELECT stockAmt FROM portfolio WHERE user = :sessionid AND stockSym = :symbol", sessionid = session['user_id'], symbol=symbol)
            currAmt = currAmt[0]['stockAmt']


            boughtOrSold = "Sold"
            stockAmt = int(request.form.get("shares"))
            stockSym = request.form.get("symbol")
            stockPrice = float(query['price'])
            time = strftime("%a, %d %b %Y %H:%M:%S", gmtime())



            duplicate = db.execute("SELECT * FROM portfolio WHERE user = :sessionid AND stockSym = :symbol", sessionid = session['user_id'], symbol=symbol)
            if not duplicate:
                return apology("You don't own any of this stock to sell!")
            elif amount > currAmt:
                return apology("You are trying to sell more shares than you own!")
            elif amount < currAmt:
                newAmt = currAmt - amount
                db.execute("UPDATE portfolio SET stockAmt = (:newAmt) WHERE user = :sessionid AND stockSym = :symbol", newAmt = newAmt, sessionid = session['user_id'], symbol=symbol)
                db.execute("UPDATE users SET cash = (:cashVal) WHERE id = :sessionid", cashVal=cashVal, sessionid = session["user_id"])
                db.execute("INSERT INTO history (user, boughtOrSold, stockSym, stockAmt, stockPrice, dateAndTime) VALUES (:user, :boughtOrSold, :stockSym, :stockAmt, :stockPrice, :dateAndTime)", user=session['user_id'], boughtOrSold=boughtOrSold, stockSym=stockSym, stockAmt=stockAmt, stockPrice=stockPrice, dateAndTime=time)
                return redirect(url_for('index'))
            elif amount == currAmt:
                db.execute("DELETE FROM portfolio WHERE stockSym = :symbol", symbol=symbol)
                db.execute("UPDATE users SET cash = (:cashVal) WHERE id = :sessionid", cashVal=cashVal, sessionid = session["user_id"])
                db.execute("INSERT INTO history (user, boughtOrSold, stockSym, stockAmt, stockPrice, dateAndTime) VALUES (:user, :boughtOrSold, :stockSym, :stockAmt, :stockPrice, :dateAndTime)", user=session['user_id'], boughtOrSold=boughtOrSold, stockSym=stockSym, stockAmt=stockAmt, stockPrice=stockPrice, dateAndTime=time)
                return redirect(url_for('index'))

    else:
        stocks = db.execute("SELECT stockSym FROM portfolio WHERE user = :sessionid", sessionid = session["user_id"])
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


def own_shares():
    """Helper function: Which stocks the user owns, and numbers of shares owned. Return: dictionary {symbol: qty}"""
    user_id = session["user_id"]
    owns = {}
    query = db.execute(
        "SELECT symbol, shares FROM orders WHERE user_id = ?", user_id)
    for q in query:
        symbol, shares = q["symbol"], q["shares"]
        owns[symbol] = owns.setdefault(symbol, 0) + shares
    # filter zero-share stocks
    owns = {k: v for k, v in owns.items() if v != 0}
    return owns


def time_now():
    """HELPER: get current UTC date and time"""
    now_utc = datetime.now(timezone.utc)
    return str(now_utc.date()) + ' @time ' + now_utc.time().strftime("%H:%M:%S")
