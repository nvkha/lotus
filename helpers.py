import os
import requests
import urllib.parse
import hashlib
import json
from cs50 import SQL

from flask import redirect, render_template, request, session
from functools import wraps

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///ecommerce.db")


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def vnd(value):
    if value:
        return f"{value:,.0f}₫"
    else:
        return "0₫"

# Create avatar for user
def gravatar(email, size=100, default='identicon', rating='g'):
    url = 'http://www.gravatar.com/avatar'
    
    hash = hashlib.md5(email.encode('utf-8')).hexdigest()
    
    return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
        url=url, hash=hash, size=size, default=default, rating=rating)

def cookieCart():
        try:
            cart = json.loads(request.cookies.get("cart"))
        except:
            cart = {}
        items = []
        
        total = 0
        for i in cart:
            product = db.execute("SELECT * FROM products WHERE id=?", i) 
            total += cart[i]["quantity"] * product[0]["price"]

            item = {
                'product_id': product[0]["id"],
                'name': product[0]['name'],
                'price': product[0]['price'],
                'image': product[0]['image'],
                'quantity': cart[i]["quantity"],
            }
            items.append(item)
        numberItem = int(len(items))
        return {"items": items, "numberItem": numberItem, "total": total}


def CartData():
    if session.get("user_id"):
        try:
            order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
            order_detail = db.execute("SELECT * FROM order_detail WHERE order_id=?", order[0]['id'])
            numberItem = int(len(order_detail))
            total = db.execute("SELECT SUM(price * quantity) FROM order_detail WHERE order_id=?", order[0]['id'])
        except:
            order_detail = None
            numberItem = 0
            total = 0
        return {"items": order_detail, "numberItem": numberItem, "total": total}
    else:
        cookieData = cookieCart()
        return {"items": cookieData['items'], "numberItem": cookieData['numberItem'], "total": cookieData['total']}

def getTotal(order_id):
    try:
        total = db.execute("SELECT SUM(quantity * price) as total FROM order_detail WHERE order_id=?", order_id)
    except:
        return 0
    return total[0]["total"]

def getProductImage(product_id):
    product = db.execute("SELECT * FROM products WHERE id=?", product_id)
    return product[0]["image"]

def getProductName(product_id):
    product = db.execute("SELECT * FROM products WHERE id=?", product_id)
    return product[0]["name"]

def getCategoryName(category_id):
    category = db.execute("SELECT * FROM category WHERE id=?", category_id)
    return category[0]["name"]

def getNumberItem():
    order = db.execute("SELECT * FROM orders WHERE user_id=? AND complete=?", session.get("user_id"), 0)
    if not order:
        numberItem = 0
    else: 
        numberItem = db.execute("SELECT COUNT(*) as number FROM order_detail WHERE order_id=?", order[0]["id"])
        numberItem = numberItem[0]["number"]
    return numberItem

def getAllNameProduct(): 
    all_products = db.execute("SELECT * FROM products")
    list_product_name = ""
    for product in all_products:
        list_product_name += product["name"] + ","
    return list_product_name
