# Database sheme

## Users
- id (pk , int)
- email (varchar , unique)
- phone_number (varchar, unique)
- password_hash (varchar)
- created_at (timestamp)

## Categories
- id (pk , int)
- name (varchar, unique)
- created_at (timestamp)

## Product 
- id (pk , int)
- name (varchar, unique)
- category_id (fk -> Categories.id)
- price (decimal)
- stock(int)
- created_at(timestamp)

## Carts 
- id (pk , int)
- user_id(fk -> Users.id ,unique)
- created_at(timestamp)
- updated_at (timestamp) 

## Cart_items
- id (pk , int)
- cart_id (fk , carts.id)
- product_id	(FK -> products)
- quantity (int)
- created_at (timestamp)

## Orders
- id (pk , int)
- user_id ( fk -> users.id)
- total (decimal)
- created_at(timestamp)
- Status (varchar)

## Order_items 
- id (pk , int)
- product_id	(FK -> products)
- Order_id(fk -> orders.id)
- qunatity (int)
- price (decimal) 
- created_at (timestamp)

## Payments
- id (pk , int)
- order_id(fk -> orders.id)
- stripe_payment_intent_id (varchar, unique)
- amount(decimal)
- status(varchar)
- created_at(timestamp)