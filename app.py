from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
from flask_moment import Moment
from flask_session import Session
from flask_mail import Mail, Message
from flask import jsonify
import json
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, vnd, gravatar, cookieCart, CartData, getTotal, getProductImage, getProductName, getCategoryName, getNumberItem, getAllNameProduct
import os
from flask_paginate import Pagination, RECORD_NAME, get_page_parameter
from currency_converter import CurrencyConverter
## & conda install --name py38 pylint -y

app = Flask(__name__)
moment = Moment(app)


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.before_request
def before_request():
  if session.get("user_id"):
      db.execute("UPDATE users SET last_seen=? WHERE id=?", datetime.utcnow(), session["user_id"])

# Custom filter
app.jinja_env.filters["vnd"] = vnd
app.jinja_env.filters["getTotal"] = getTotal
app.jinja_env.filters["getProductImage"] = getProductImage
app.jinja_env.filters["getProductName"] = getProductName
app.jinja_env.filters["getCategoryName"] = getCategoryName



#function 
app.jinja_env.globals.update(gravatar=gravatar)

#function 
app.jinja_env.globals.update(getAllNameProduct=getAllNameProduct)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure email
mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ['EMAIL_USER'],
    "MAIL_PASSWORD": os.environ['EMAIL_PASSWORD']
}

UPLOAD_FOLDER = os.getcwd() + r'\static\product_image'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'jfif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



app.config.update(mail_settings)
mail = Mail(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///ecommerce.db")

@app.route("/")
def index():
    products = {}
    categories = db.execute("SELECT * FROM category")
    for category in categories:
        products[category["name"]] = db.execute("SELECT * FROM products WHERE category_id=? LIMIT 4", category["id"])
    
    # Ensure user confirmed
    if session.get("user_id"):
        rows = db.execute("SELECT * FROM users WHERE id=?", session["user_id"])
        if rows[0]["confirm"] == False:
            return redirect("/unconfirmed")

        return render_template("store.html", products=products, numberCart=getNumberItem(), user=rows[0], categories=categories)
    else:
        cookieData = cookieCart()
        return render_template("store.html",products=products,order_details=cookieData["items"], numberCart=cookieData["numberItem"], total=cookieData["total"], categories=categories)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Register user"""
    if request.method == "GET":
        cartData = CartData()
        return render_template("signup.html", numberCart=cartData["numberItem"])
    else:
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("password_again"):
            return apology("passwords not match", 403)
        elif request.form.get("password") != request.form.get("password_again"):
            return apology("passwords not match", 403)

        rows = db.execute("SELECT * FROM users WHERE email=?", request.form.get("email"))
        user = db.execute("SELECT * FROM users WHERE username=?", request.form.get("username"))

        # Ensure account not exists
        if len(rows) > 0:
            return apology("this email has already existed", 403)
        elif len(user) > 0:
            return apology("this username has already existed", 403)

        db.execute("INSERT INTO users(username, hash, email) VALUES(?, ?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")), request.form.get("email"))
        user_id = db.execute("SELECT * FROM users WHERE username=?", request.form.get("username"))
        db.execute("UPDATE users SET member_since=? WHERE id=?", datetime.utcnow(), user_id[0]["id"])
        msg = Message(subject="Confirm Your Account",
                      sender=app.config.get("MAIL_USERNAME"),
                      recipients=[request.form.get("email")], # replace with your email for testing
                      )
        msg.html=render_template("mail.html", name=request.form.get("username"), id=user_id[0]["id"])
        mail.send(msg)
        flash('Sign up success! A confirmation email has been sent to you by email.', "success")
        return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Log user in 
    session.clear()

    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)
        
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        # Query data for user name
        rows = db.execute("SELECT * FROM Users WHERE email=?", request.form.get("email"))
        
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or email", 403)
        
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        
        # Remember info user logged in 
        session["username"] = rows[0]["username"]
        session["email"] = rows[0]["email"]
        session["image"] = rows[0]["image"]
        session["role"] = rows[0]["role"]

        # Update cookie cart data on browser into user cart when user logged in
        cookieData = cookieCart()
        order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
        items = cookieData["items"]

        if not order:
            db.execute("INSERT INTO orders(user_id) VALUES(?)", session.get("user_id"))
            order_new = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)

            for item in items:
                db.execute("INSERT INTO order_detail VALUES(?, ?, ?, ?)", 
                order_new[0]["id"], item["product_id"], item["quantity"], item["price"]) 
        else:
            order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", order[0]["id"])
            if not order_detail:
                for item in items:
                    db.execute("INSERT INTO order_detail VALUES(?, ?, ?, ?)", 
                    order[0]["id"], item["product_id"], item["quantity"], item["price"]) 
            else:
                for item in items:
                    try:
                        db.execute("INSERT INTO order_detail VALUES(?, ?, ?, ?)", 
                        order[0]["id"], item["product_id"], item["quantity"], item["price"]) 
                    except:
                        db.execute("UPDATE order_detail SET quantity= quantity + ? WHERE order_id=? AND product_id=?",
                        item["quantity"], order[0]["id"], item["product_id"]) 

        # Ensure user confirmed
        if rows[0]["confirm"] == False:
            return redirect("/unconfirmed")

        # Redirect user to home page if user confirmed
        return redirect("/")
    
    # if request is GET
    else:
        cartData = CartData()
        return render_template("login.html", numberCart=cartData["numberItem"])

@app.route("/cart")
def cart():
    if session.get("user_id"):
        try:
            order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
            order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", order[0]['id'])
            numberItem = int(len(order_detail))
            total = db.execute("SELECT SUM(price * quantity) as total FROM order_detail WHERE order_id=?", order[0]['id'])
            total = total[0]["total"]
        except:
            order_detail = None
            numberItem = 0
            total = 0
        products = db.execute("SELECT * FROM products")
        
        return render_template("cart.html", order_details=order_detail, products=products, numberCart=numberItem, total=total)
    else:
        cookieData = cookieCart()
        return render_template("cart.html",order_details=cookieData["items"], numberCart=cookieData["numberItem"], total=cookieData["total"])


@app.route("/product/<string:name>")
def product(name):
    product = db.execute("SELECT * FROM products WHERE name=?", name)
    order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
    cookieData = cookieCart()
    cartData = CartData()
    reviews = db.execute("SELECT * FROM reviews WHERE product_id=?", product[0]['id'])
    images = db.execute("SELECT * FROM product_image WHERE product_id=?", product[0]['id'])
    rating = db.execute("SELECT AVG(rating) as rating, COUNT(*) as total FROM reviews WHERE product_id=?", product[0]['id'])
    return render_template("product.html", product=product[0], numberCart=cartData["numberItem"], reviews=reviews, images=images, rating=rating[0])

@app.route("/admin")
def sell():
    return redirect(url_for('dashboard'))


@app.route("/unconfirmed")
def unconfirmed():
    cartData = CartData()
    rows = db.execute("SELECT * FROM users WHERE id=?", session["user_id"])
    if session.get("user_id") is None or rows[0]["confirm"] == True:
        return redirect("/")
    
    return render_template("unconfirmed.html", numberCart=cartData["numberItem"])
    
    

@app.route('/confirm')
@login_required
def resend_confirmation():

    msg = Message(subject="Confirm Your Account",
                      sender=app.config.get("MAIL_USERNAME"),
                      recipients=[session["email"]], # replace with your email for testing
                      )
    msg.html=render_template("mail.html", name=session["username"], id=session["user_id"])
    mail.send(msg)

    flash('A new confirmation email has been sent to you by email.', "success")
    return redirect(url_for('index'))


@app.route('/confirm/<int:id>')
@login_required
def confirm(id):
    if id != session.get("user_id"):
        return apology('The confirmation link is invalid or has expired.', 403)
    db.execute("UPDATE users SET confirm=? WHERE id=?", 1, session.get("user_id"))
    flash('You have confirmed your account. Thanks!', 'success')
    return redirect("/")


@app.route('/user/<username>')
@login_required
def user(username):
    dataCart = CartData()
    user = db.execute("SELECT * FROM users WHERE username=?", username)
    last_seen = datetime.strptime(user[0]["last_seen"], '%Y-%m-%d %H:%M:%S')
    member_since = datetime.strptime(user[0]["member_since"], '%Y-%m-%d %H:%M:%S')
    return render_template("user.html", user=user[0], last_seen=last_seen, member_since=member_since, numberCart=dataCart["numberItem"])


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == "POST":
        realname = request.form.get("realname")
        location = request.form.get("location")
        aboutme = request.form.get("aboutme")
        
        if realname:
            db.execute("UPDATE users SET realname=? WHERE id=?", realname, session["user_id"])
        if location:
            db.execute("UPDATE users SET location=? WHERE id=?", location, session["user_id"])
        if aboutme:
            db.execute("UPDATE users SET about_me=? WHERE id=?", aboutme, session["user_id"])
        
        flash('Your profile has been updated.', 'success')
        
        return redirect(url_for('user', username=session["username"]))
    
    else:
        dataCart = CartData()
        img = db.execute("SELECT * FROM users WHERE id=?", session.get("user_id"))
        return render_template("edit_profile.html", filename=img[0], numberCart=dataCart["numberItem"])



@app.route('/checkout', methods=["GET", "POST"])
def checkout():
    if request.method == "GET":
        if session.get("user_id"):
            try:
                order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
                order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", order[0]['id'])
                numberItem = int(len(order_detail))
                total = getTotal(order[0]['id'])
            except:
                order_detail = None
                numberItem = 0
                total = 0
            return render_template("checkout.html", numberCart=numberItem, order_details=order_detail, total=total)
        else:
            cookieData = cookieCart()
            return render_template("checkout.html",order_details=cookieData["items"], numberCart=cookieData["numberItem"], total=cookieData["total"])

    else:
        if session.get("user_id"):
            name = request.form.get("name")
            phonenumber = request.form.get("phonenumber")
            email = session.get("email")
            address = request.form.get("address")
            date = datetime.utcnow().strftime('%Y-%m-%d')

            order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
            order_id = order[0]["id"]
            order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", order[0]["id"])
            for item in order_detail:
                db.execute("UPDATE products SET quantity=quantity - ? WHERE id=?", item["quantity"], item["product_id"])

            db.execute('UPDATE orders SET order_name=?, order_phonenumber=?, order_email=?, order_address=?, order_date=?, complete=?', 
            name, phonenumber, email, address, date, 1)
            
            return redirect(url_for('order_success', id=order_id))
        else:
            name = request.form.get("name")
            phonenumber = request.form.get("phonenumber")
            email = request.form.get("email")
            address = request.form.get("address")
            date = datetime.utcnow().strftime('%Y-%m-%d')
            transaction_id = datetime.now().timestamp()
            db.execute("INSERT INTO orders(order_date, order_name, order_phonenumber, order_email, order_address, transaction_id)" 
            "VALUES(?, ?, ?, ?, ?, ?)", date, name, phonenumber, email, address, transaction_id)
            order = db.execute("SELECT * FROM orders WHERE transaction_id=?", transaction_id)
            order_id = order[0]["id"]

            cookieData = cookieCart()
            items = cookieData["items"]

            for item in items:
                db.execute("INSERT INTO order_detail VALUES(?, ?, ?, ?)", 
                order[0]["id"], item["product_id"], item["quantity"], item["price"])
            
            order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", order[0]["id"])
            for item in order_detail:
                db.execute("UPDATE products SET quantity=quantity - ? WHERE id=?", item["quantity"], item["product_id"])
            
            db.execute("UPDATE orders SET complete=? WHERE id=?", 1, order[0]["id"])
            return redirect(url_for('order_success', id=order_id))


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/admin/all-order")
@login_required
def all_order():
   cartData = CartData()
   orders = db.execute("SELECT * FROM orders WHERE complete=? ORDER BY order_date DESC", 1)
   page = request.args.get(get_page_parameter(), type=int, default=1)
   data = []
   for i in range(10 * (page - 1), (page - 1) * 10 + 10):
    try:
        data.append(orders[i])
    except:
        break
   pagination = Pagination(page=page,css_framework='bootstrap4', total=len(orders), RECORD_NAME="orders", per_page=10)
   return render_template("adminpage/all_order.html", orders=data, numberCart=cartData["numberItem"], pagination=pagination)

@app.route("/admin/view-order/<int:id>")
@login_required
def view_order(id):
    cartData = CartData()
    order = db.execute("SELECT * FROM orders WHERE id=?", id)
    order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", id)
    number_item = len(order_detail)
    total = db.execute("SELECT SUM(price * quantity) as sum FROM order_detail WHERE order_id=?", id)
    return render_template("adminpage/view_order.html", order=order[0], order_detail=order_detail, numberCart=cartData["numberItem"], numberItem=number_item, total=total[0])

@app.route("/admin/all-product")
@login_required
def all_product():
    cartData = CartData()
    products = db.execute("SELECT * FROM products")
    page = request.args.get(get_page_parameter(), type=int, default=1)
    data = []
    for i in range(10 * (page - 1), (page - 1) * 10 + 10):
     try:
         data.append(products[i])
     except:
         break
    pagination = Pagination(page=page,css_framework='bootstrap4', total=len(products), RECORD_NAME="products", per_page=10)
    return render_template("adminpage/all_product.html", products=data, numberCart=cartData["numberItem"], pagination=pagination)

@app.route("/admin/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("mytextarea")
        quantity = request.form.get("quantity")
        price = request.form.get("price")
        category = request.form.get("category")
        brand = request.form.get("brand")

        db.execute("INSERT INTO products(name, quantity, price, description, category_id, brand_id) VALUES(?, ?, ?, ?, ?, ?)",
            name, quantity, price, description, category, brand)
        flash("Add product success", "success")
        return redirect(url_for('add_image', name=name))
    else:
        cartData = CartData()
        categories = db.execute("SELECT * FROM category")
        brands = db.execute("SELECT * FROM brand")
        return render_template("adminpage/add_product.html", numberCart=cartData["numberItem"], categories=categories, brands=brands)

@app.route("/admin/add-image/<string:name>", methods=["GET", "POST"])
@login_required
def add_image(name):
    if request.method == "GET":
        cartData = CartData()
        return render_template("adminpage/add_image.html", name=name, numberCart=cartData["numberItem"])


@app.route('/uploads/<string:name>', methods=['GET', 'POST'])
@login_required
def upload(name):
    if request.method == 'POST':     
        files = request.files

        product = db.execute("SELECT * FROM products WHERE name=?", name)

        for i in range(len(files)):
            if files[str(i)] and allowed_file(files[str(i)].filename):
                filename = secure_filename(files[str(i)].filename)
                files[str(i)].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.execute("INSERT INTO product_image(id, product_id, image) VALUES(?, ?, ?)", i + product[0]["id"], product[0]["id"], filename)
                if product[0]["image"] == None:
                    db.execute("UPDATE products SET image=? WHERE id=?", filename, product[0]["id"])  
            else:
                continue
        return redirect(url_for('all_product'))
        


@app.route("/update-item", methods=["GET", "POST"])
def update_item():
    if request.method == "POST":
        data = json.loads(request.data)
        productId = data["productId"]
        quantity = data["quantity"]
        action = data["action"]
        product = db.execute("SELECT * FROM products WHERE id=?", productId)
        order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
        
        if not order:
            db.execute("INSERT INTO orders(user_id) VALUES(?)", session.get("user_id"))
            order_new = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
            
            db.execute("INSERT INTO order_detail(order_id, product_id, quantity, price) VALUES(?, ?, ?, ?)",
                order_new[0]["id"], productId, quantity, product[0]["price"])
        else:
            orderItem = db.execute("SELECT * FROM order_detail WHERE order_id=? AND product_id=?", 
                order[0]["id"], productId)
           
            if not orderItem:
                db.execute("INSERT INTO order_detail(order_id, product_id, quantity, price) VALUES(?, ?, ?, ?)",
                    order[0]["id"], productId, quantity, product[0]["price"])
            
            else:
                if action == "update":
                    db.execute("UPDATE order_detail SET quantity=quantity + ? WHERE order_id=? AND product_id=?",
                    quantity, order[0]["id"], productId)

                if action == "add":
                    db.execute("UPDATE order_detail SET quantity=quantity + ?, price=? WHERE product_id=? AND order_id=?",
                        1,product[0]["price"], productId, orderItem[0]['order_id'])
                elif action == "remove":
                    db.execute("UPDATE order_detail SET quantity=quantity - ?, price=? WHERE product_id=? AND order_id=?",
                        1,product[0]["price"], productId, orderItem[0]['order_id'])
                    item_now = db.execute("SELECT * FROM order_detail WHERE order_id=? AND product_id=?", orderItem[0]['order_id'], productId)
                    if int(item_now[0]["quantity"]) <= 0:
                        db.execute("DELETE FROM order_detail WHERE order_id=? AND product_id=?", orderItem[0]['order_id'], productId)

                elif action == "delete":
                    db.execute("DELETE FROM order_detail WHERE order_id=? AND product_id=?", orderItem[0]['order_id'], productId)
                

        return jsonify("It was added")
    else:
        return "Hello"

@app.route("/delete/<int:id>")
@login_required
def delete_product(id):
    order = db.execute("SELECT * FROM orders WHERE complete=?", 0)
    if order:
        order_detail = db.execute("SELECT * FROM order_detail WHERE product_id=? AND order_id=?", id, order[0]["id"])
        if order_detail:
            db.execute("DELETE FROM order_detail WHERE order_id=?", order[0]["id"])
    db.execute("DELETE FROM reviews WHERE product_id=?", id)
    db.execute("DELETE FROM products WHERE id=?", id)

    path = os.path.join(os.getcwd(), "static\product_image")
    images = db.execute("SELECT * FROM product_image WHERE product_id=?", id)
    for image in images:
        if os.path.exists(os.path.join(path, str(image["image"]))):
            os.remove(os.path.join(path, str(image["image"])))
    db.execute("DELETE FROM product_image WHERE product_id=?", id)
    
    flash("Delete product success", 'success')
    return redirect(url_for('all_product'))


@app.route("/edit-product/<int:id>", methods=["GET", "POST"])
@login_required
def edit_product(id):
    if request.method == "GET":
        cartData = CartData()
        product = db.execute("SELECT * FROM products WHERE id=?", id)
        productImage = db.execute("SELECT * FROM product_image WHERE product_id=?", id)
        categories = db.execute("SELECT * FROM category")
        brands = db.execute("SELECT * FROM brand")
        return render_template("edit_product.html", product=product[0], productImage=productImage, numberCart=cartData["numberItem"], categories=categories, brands=brands)
    else:
        name = request.form.get('name')
        description = request.form.get('mytextarea')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        category = request.form.get("category")
        brand = request.form.get("brand")

        db.execute("UPDATE products SET name=?, description=?, price=?, quantity=?, brand_id=?, category_id=? WHERE id=?",
        name, description, price, quantity,brand, category, id)
        orders = db.execute("SELECT * FROM orders WHERE complete=?",0)
        for order in orders:
            db.execute("UPDATE order_detail SET price=?, quantity=? WHERE order_id=? AND product_id=?"
            , price, quantity, order["id"], id)

        files = request.files
        product = db.execute("SELECT * FROM products WHERE id=?", id)

        for i in range(6):
            if files[str(i)] and allowed_file(files[str(i)].filename):
                filename = secure_filename(files[str(i)].filename)
                files[str(i)].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                try:
                    db.execute("SELECT * FROM WHERE product_image WHERE id=? AND product_id=?", filename, i + id, id)
                    db.execute("UPDATE product_image SET image=? WHERE id=? AND product_id=?", filename, i + id, id)
                except:
                    db.execute("INSERT INTO product_image VALUES(?, ?, ?)", i + id, id, filename)
                if product[0]["image"] == None:
                    db.execute("UPDATE products SET image=? WHERE id=?", filename, id)  
    
        flash('Edit product success', 'success')
        return redirect(url_for('all_product'))

@app.route("/admin/customers/", methods=["GET", "POST"])
@login_required
def customers():
    cartData = CartData()
    customers = db.execute("SELECT * FROM users")
    page = request.args.get(get_page_parameter(), type=int, default=1)
    data = []
    for i in range(10 * (page - 1), (page - 1) * 10 + 10):
        try:
            data.append(customers[i])
        except:
            break
    pagination = Pagination(page=page,css_framework='bootstrap4', total=len(customers), RECORD_NAME="customers", per_page=10)
    return render_template("/adminpage/customers.html", customers=data, numberCart=cartData["numberItem"], pagination=pagination)

@app.route("/admin/upload-user/", methods=["GET", "POST"])
@login_required
def upload_file():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("Not file part", "danger")
            return redirect(url_for('edit_profile'))      
        file = request.files["file"]

        if file.filename == '':
            flash("No select file")
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            db.execute("UPDATE users SET image=? WHERE id=?", filename, session.get("user_id"))
            flash("Upload success", "success")
            return redirect(url_for('edit_profile'))
    

@app.route("/review/<int:id>", methods=["GET", "POST"])
def review(id):
    if request.method == "POST":
        rating = request.form.get("star")
        name = request.form.get("name")
        content = request.form.get("mytextarea")
        db.execute("INSERT INTO reviews(product_id, title, content, rating, submit_date) VALUES(?,?,?,?,?)", 
            id, name, content, rating, datetime.utcnow())
        name = db.execute("SELECT name FROM products WHERE id=?", id)
        flash('Thank you for rating this product', 'success')
        return redirect(url_for('product', name=name[0]['name']))

@app.route("/admin/dashboard")
@login_required
def dashboard():
    cartData = CartData()
    orders = db.execute("SELECT COUNT(*) as total FROM orders")
    orders_top5 = db.execute("SELECT * FROM orders WHERE complete=1 ORDER BY order_date LIMIT 5")
    products = db.execute("SELECT COUNT(*) as total FROM products")
    customers = db.execute("SELECT COUNT(id) as total FROM users")
    return render_template("/adminpage/dashboard.html", orders=orders[0], products=products[0], customers=customers[0], orders_top5=orders_top5, numberCart=cartData["numberItem"])


@app.route("/my-orders")
@login_required
def my_order():
    cartData = CartData()
    orders = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 1)
    return render_template("my_orders.html", orders=orders, numberCart=cartData["numberItem"])

@app.route("/my-orders/<int:id>")
@login_required
def view_my_order(id):
    cartData = CartData()
    order = db.execute("SELECT * FROM orders WHERE id=?", id)
    order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", id)
    return render_template("view_my_order.html", order=order[0], order_detail=order_detail, numberCart=cartData["numberItem"])


@app.route("/order-success/<int:id>")
def order_success(id):
    order = db.execute("SELECT * FROM orders WHERE id=?", id)
    order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", id)
    msg = Message(subject="# " + str(id),
                    sender=app.config.get("MAIL_USERNAME"),
                    recipients=[order[0]["order_email"]], # replace with your email for testing
                    )
    msg.html=render_template("email_order.html", name=order[0]["order_name"], order_detail=order_detail, order=order[0])
    mail.send(msg)

    return render_template("order_success.html", numberCart=0)


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "GET":
        cartData = CartData()
        return render_template("change_password.html", numberCart=cartData["numberItem"])
    else:
        password_old = request.form.get("password_old")
        password_new = request.form.get("password_new")
        password_again = request.form.get("password_again")

        if not password_old or not password_new or not password_again:
            return apology("missing password")
        elif password_new != password_again:
            return apology("password not match")

        rows = db.execute("SELECT * FROM users WHERE id=?", session["user_id"])
        if not check_password_hash(rows[0]["hash"], request.form.get("password_old")):
            return apology("invalid password old", 403)

        db.execute("UPDATE users SET hash=? WHERE "
        "id=?", generate_password_hash(request.form.get("password_new")), session["user_id"])
        flash("Change password success", 'success')
        return redirect("/")

@app.route("/category/<string:category_name>/")
def category(category_name):
    p = request.args.get("p", default="")
    s = request.args.get("s", default="")
    b = request.args.get("b", default="")

    query = ""
    query1 = ""
    query2 = ""
    cookieData = cookieCart()

    if category_name == "phone":
        if p == "duoi-2-trieu":
            query = " AND price < 2000000"
            p = "Dưới 2tr"
        elif p == "tu-2-4-trieu":
            query = " AND price BETWEEN 2000000 AND 4000000"
            p = "Từ 2 - 4tr"
        elif p == "tu-4-7-trieu":
            query = " AND price BETWEEN 4000000 AND 7000000"
            p = "Từ 4 - 7tr"
        elif p == "tu-7-13-trieu":
            query = " AND price BETWEEN 7000000 AND 13000000"
            p = "Từ 7 - 13tr"
        elif p == "tu-13-20-trieu":
            query = " AND price BETWEEN 13000000 AND 20000000"
            p = "Từ 13 - 20tr"
        elif p == "tren-20-trieu":
            query = " AND price > 20000000"
            p = "Trên 20tr"
    elif category_name == "laptop":
        if p == "duoi-10-trieu":
            query = " AND price < 10000000"
            p = "Dưới 10tr"
        elif p == "tu-10-15-trieu":
            query = " AND price BETWEEN 10000000 AND 15000000"
            p = "Từ 10 - 15tr"
        elif p == "tu-15-20-trieu":
            query = " AND price BETWEEN 15000000 AND 20000000"
            p = "Từ 15 - 20tr"
        elif p == "tu-20-25-trieu":
            query = " AND price BETWEEN 20000000 AND 25000000"
            p = "Từ 20 - 25tr"
        elif p == "tren-25-trieu":
            query = " AND price > 25000000"
            p = "Trên 25tr"
    elif category_name == "tablet":
        if p == "duoi-3-trieu":
            query = " AND price < 3000000"
            p = "Dưới 3tr"
        elif p == "tu-3-8-trieu":
            query = " AND price BETWEEN 3000000 AND 8000000"
            p = "Từ 3 - 8tr"
        elif p == "tu-8-15-trieu":
            query = " AND price BETWEEN 8000000 AND 15000000"
            p = "Từ 8 - 15tr"
        elif p == "tren-15-trieu":
            query = " AND price > 15000000"
            p = "Trên 15tr"

        
    if s == "low-to-high-price":
        query1 = " ORDER BY price ASC"
        s = "Low to high price"
    elif s == "high-to-low-price":
        query1 = " ORDER BY price DESC"
        s = "High to low price"



    category = db.execute("SELECT * FROM category WHERE name=?", category_name.capitalize())
    brands = db.execute("SELECT * FROM brand WHERE category_id=?", category[0]["id"])

    if b != "":
        for brand in brands:
            if str(b).lower().strip() ==  str(brand["name"]).lower().strip() and int(category[0]["id"]) == int(brand["category_id"]):
                query2 = " AND brand_id=" + str(brand["id"])
                break

    products = db.execute("SELECT * FROM products WHERE category_id=?" + query + query2 + query1, category[0]["id"])


    page = request.args.get(get_page_parameter(), type=int, default=1)
    data = []
    for i in range(2 * (page - 1), (page - 1) * 2 + 2):
        try:
            data.append(products[i])
        except:
            break
    pagination = Pagination(page=page,css_framework='bootstrap4', total=len(products), RECORD_NAME="products", per_page=2)
    return render_template("category.html",products=data,order_details=cookieData["items"], numberCart=cookieData["numberItem"], 
            total=cookieData["total"],brands=brands , category_name=category_name, p=p, s=s,b=b, pagination=pagination)


@app.route("/search", methods=["GET", "POST"])
def search():
    cartData = CartData()
    search_query = request.form.get("search")
    products = db.execute("SELECT * FROM products WHERE name LIKE ?", "%" + search_query + "%")
    return render_template("search.html", numberCart=cartData["numberItem"], products=products, search_text=search_query)

if __name__ == "__main__":
    app.run(debug=True)