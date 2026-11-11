
-- Add nullable user ownership to existing orders.
ALTER TABLE orders
ADD COLUMN user_id INTEGER NULL;

-- Link each assigned order to a registered user.
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user_id
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE SET NULL;

-- Speed up queries that retrieve a user's orders.
CREATE INDEX ix_orders_user_id
ON orders(user_id);
