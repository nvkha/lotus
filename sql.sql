CREATE TABLE products(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity INT, price MONEY, description TEXT, product_image_id varchar(255), user_id INTEGER, category_id);
CREATE TABLE products_image(id INTEGER PRIMARY KEY AUTOINCREMENT, image VARCHAR(255));
CREATE TABLE orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date_order DATETIME, payment_id INTEGER, complete BOOLEAN);
CREATE TABLE order_detail(order_id INTEGER, product_id INTEGER, quantity INTEGER, price NUMERIC)