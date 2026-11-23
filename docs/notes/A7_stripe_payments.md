# Notes: Phase A7 — Stripe Payments & Zero-Trust Webhooks

## Key Decisions
- **Zero-Trust PaymentIntent Architecture**: Never handle raw card numbers on the backend (avoids PCI-DSS audits). The backend creates a `PaymentIntent` and returns a `client_secret` to the browser.
- **Service Layer Isolation (`app/services/payment.py`)**: Keeps external Stripe SDK interactions cleanly decoupled from FastAPI HTTP route controllers.
- **`await db.flush()` Pattern**: Used when an entity needs its database-generated ID (like `order.id`) before committing, allowing it to be linked to Stripe metadata and the `Payment` table within the same transaction.

## Common Traps & Lessons
- **Floating-Point Currency Representation Bug**:
  Computers cannot represent binary fractions accurately (`0.1 + 0.2 != 0.3`). Stripe accepts integer cents, not floating-point dollars.
  - **Fix**: Convert Decimal directly to integer cents:
    ```python
    amount_cents = int((order.total * 100).to_integral_value())
    ```
- **Webhooks as the Single Source of Truth**:
  Never rely on the customer's browser redirect to confirm payment. Browsers can drop Wi-Fi, run out of battery, or be intercepted by hackers. Only Stripe's server-to-server webhook has authority to mark orders paid.
- **HMAC Signature Verification on Raw Bytes**:
  Stripe hashes the request body with `STRIPE_WEBHOOK_SECRET`.
  - **Trap**: If FastAPI parses the body to JSON first, whitespace or key order changes, invalidating the HMAC.
  - **Fix**: Always verify using raw bytes: `payload = await request.body()`.
- **Webhook Idempotency**:
  Stripe retries webhook delivery if your server's response drops. If an order or payment is already confirmed, **never return 400 or 500**. Log it, skip processing, and return `200 OK` immediately to prevent infinite retry storms.
