# ReFind

**Find it again. Give it a new beginning.**

ReFind is a campus-based marketplace for pre-owned goods. It helps students buy,
sell, exchange, donate, and reuse textbooks, academic materials, electronics,
furniture, bicycles, sports equipment, and other university essentials within a
trusted campus community.

Unlike a traditional e-commerce platform, ReFind focuses on student sellers,
local in-person handovers, affordability, and sustainable reuse rather than
commercial delivery and online payments.

## Project Status

The project report defines a Django-based MVP designed for implementation by a
three-member team over one semester. The server-rendered Django MVP described
below is still being developed.

## MVP Features

- Campus-email registration, verification, login, password reset, and profiles
- Student and administrator roles
- Listings with title, description, category, condition, price, and up to three images
- Sell, Exchange, and Donate listing types
- Keyword search, category and condition filters, price ranges, and sorting
- Wishlists for saved listings
- Listing-based buyer and seller message threads with unread indicators
- Buy, exchange, and donation requests with status tracking
- Listing reservation and automatic rejection of competing pending requests
- Seller ratings and reviews after completed requests
- Listing reports and administrator moderation
- An administrator dashboard with platform statistics

Transactions are completed offline between students. ReFind facilitates
discovery and communication but does not process payments or guarantee the
condition or authenticity of products.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Django Templates, Tailwind CSS, HTMX |
| Backend | Python 3, Django 5, Django MVT |
| Database | PostgreSQL |
| Media | Cloudinary in production, local media during development |
| Email | SMTP for verification and password reset |
| Deployment | Render or Railway with environment-based configuration |
| Collaboration | Git, GitHub, and VS Code |

The MVP is intentionally a single Django project with server-rendered pages,
session-based authentication, and no separate API contract. A mobile
application and REST API are future enhancements rather than part of the
current MVP architecture.

## Architecture

ReFind uses a three-tier layered MVT architecture:

1. **Presentation tier** — Django Templates render responsive HTML, Tailwind CSS
   provides styling, and HTMX adds partial updates for interactions such as
   wishlist toggles, filtering, and inbox polling.
2. **Application tier** — Django middleware, URL routing, forms, views, and a
   service layer implement authentication, authorization, validation, and
   marketplace rules.
3. **Data tier** — PostgreSQL stores relational data. Cloudinary or local media
   storage handles images, and SMTP handles account emails.

Important transaction rules are implemented in the service layer. Accepting a
request uses `transaction.atomic()` and `select_for_update()` to lock the
listing, prevent double acceptance, reserve the listing, and reject other
pending requests safely.

## Django Apps

| App | Responsibility |
| --- | --- |
| `accounts` | Registration, campus-email verification, login, profiles, roles, and statistics |
| `listings` | Listing CRUD, images, categories, search, filters, sorting, and wishlists |
| `messaging` | Listing-based conversations, inboxes, and unread counts |
| `transactions` | Buy, exchange, and donation requests, status logic, locking, reviews, and reports |

## Data Model

The compact MVP schema uses five primary models:

- **User** — account, profile, role, verification, and saved listings
- **Listing** — product details, listing type, price, images, and availability
- **Request** — buy, exchange, or donation request, including status and review
- **Message** — listing-based conversation messages
- **Report** — user reports against listings

The database design includes ownership validation, check constraints, indexed
search fields, a conditional unique constraint for duplicate pending requests,
and row-level locking for concurrent request acceptance.

## Repository Structure

```text
ReFind/
├── server/                 # Django MVP implementation (planned/in progress)
├── .gitignore
└── README.md
```

## Local Development

### Django MVP

Once the Django project is added to `server/`, create a virtual environment,
configure the required environment variables, install dependencies, apply
migrations, and start the development server:

```powershell
cd server
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Production configuration should provide PostgreSQL, media storage, SMTP
credentials, the allowed campus email domain, and a secret key through
environment variables. Never commit credentials or `.env` files.

## Scope and Limitations

The initial release:

- Serves one university community
- Requires campus-email verification
- Uses direct, offline student handovers and payments
- Depends on student-created listings for product availability
- Facilitates communication but does not guarantee product quality

## Future Scope

- Real-time chat with Django Channels and Redis
- Multi-university support
- Email and push notification history
- REST API and native mobile clients
- Two-way buyer and seller reviews
- AI price suggestions, image similarity, recommendations, and barter matching
- Optional UPI or payment-gateway integration
- Campus-wide reuse analytics

## Collaboration Principles

- Keep the Django apps modular and responsibilities clearly separated.
- Validate input and enforce ownership and authorization on the server.
- Keep secrets outside version control.
- Preserve listing, request, and availability consistency in database transactions.
- Add tests for marketplace rules, permissions, search, and status transitions.
- Use Git branches and pull requests for collaborative development.

## Links

- [GitHub repository](https://github.com/singhharshitt/ReFind)

## License

This project is under development. Add a project license before public
distribution.
