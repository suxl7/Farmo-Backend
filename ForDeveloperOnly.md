# Other Useful Django Features (Beyond @classmethod & Token Auth)


## 1. Signals
- What it is: Hooks that let you run code automatically when certain events happen (e.g., after saving a model).
- Where to use in Farmo:
- After a farmer registers → automatically create their wallet entry.
- After an order is placed → notify the farmer or update stock.
- After a token expires → mark it as inactive.


## 2. Custom Managers
- What it is: Extend objects with custom querysets.
- Where to use:
- Tokens.objects.active() → fetch only active tokens.
- Products.objects.available() → fetch only products with stock > 0.
- Orders.objects.pending() → fetch orders awaiting delivery.


## 3. Middleware
- What it is: Code that runs on every request/response.
- Where to use:
- Auto‑log user activity (audit trail).
- Enforce token checks globally (extra security).
- Add headers for security (CORS, HTTPS enforcement).


## 4. Model Methods (instance methods)
- What it is: Functions tied to a single object.
- Where to use:
- In Wallet model → wallet.deposit(amount) or wallet.withdraw(amount).
- In Order model → order.mark_delivered() or order.cancel().


## 5. Serializers (DRF)
- What it is: Convert models to JSON and validate input.
- Where to use:
- Farmer profile serializer → validate farm details.
- Product serializer → ensure price and quantity are positive.
- Wallet serializer → ensure withdrawal amount ≤ balance.


## 6. Permissions (DRF)
- What it is: Control access to views.
- Where to use:
- Only farmers can upload products.
- Only consumers can place orders.
- Only admins can deactivate users or tokens.


## 7. Validators
- What it is: Rules to enforce data integrity.
- Where to use:
- Wallet PIN must be 4 digits.
- Product price must be > 0.
- Token expiry must be in the future.


## 8. Caching
- What it is: Store frequently accessed data in memory (Redis/Memcached).
- Where to use:
- Product listings (fast browsing).
- Wallet balance (quick lookup).
- Notifications (reduce DB hits).


## 9. Transactions
- What it is: Ensure multiple DB operations succeed or fail together.
- Where to use:
- When a consumer pays → deduct wallet, create order, update farmer’s wallet.
- If any step fails, rollback everything.


## 10. Admin Customization
- What it is: Extend Django Admin for monitoring.
- Where to use:
- Show farmer verification status.
- Track token activity (active/inactive).
- Generate transaction reports.


### ✅ Summary
- Signals → automate actions (wallet creation, notifications).
- Custom Managers → clean queries (Tokens.active()).
- Middleware → global checks/logging.
- Model Methods → per‑object actions (wallet deposit, order cancel).
- Serializers → validate API input/output.
- Permissions → restrict access by role.
- Validators → enforce rules on fields.
- Caching → speed up product/wallet lookups.
- Transactions → ensure safe money transfers.
- Admin Customization → monitoring and reporting.
