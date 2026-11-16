# ReFind

**Find Again. Love Again.**

ReFind is a campus-based peer-to-peer marketplace for students. It helps students buy, sell, and exchange second-hand books, electronics, furniture, cycles, calculators, and other campus essentials within their university community.

## Project Status

The project is currently in the foundation phase:

- React and Vite frontend is available in `client/`.
- Django REST Framework backend dependencies are prepared in `server/`.
- The root `.gitignore` excludes local dependencies, virtual environments, secrets, generated files, and runtime data.
- Marketplace, authentication, messaging, wishlist, reviews, and moderation features are planned for incremental implementation.

## Technology Stack

### Client

- React
- Vite
- JavaScript (ES6+)
- Tailwind CSS v4
- React Router DOM
- Axios
- Lucide React

### Server

- Python
- Django
- Django REST Framework
- Simple JWT
- Django CORS Headers
- Pillow
- Django Channels when real-time messaging infrastructure is enabled

### Database

SQLite is used for initial development. Models and configuration should remain compatible with PostgreSQL for production.

## Repository Structure

```text
ReFind/
├── client/                 # React/Vite frontend
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── server/                 # Django backend
│   ├── accounts/
│   ├── marketplace/
│   ├── messaging/
│   ├── reviews/
│   ├── core/
│   ├── config/
│   └── manage.py
├── .gitignore
└── README.md
```

Backend application directories will be added as their corresponding features are implemented. The frontend and backend remain independently deployable.

## Local Development

### Frontend

From the project root:

```powershell
cd client
npm install
npm run dev
```

Useful frontend commands:

```powershell
npm run build
npm run lint
npm run preview
```

### Backend

Create or activate a Python virtual environment inside `server/`, then install the backend requirements when `server/requirements.txt` is available:

```powershell
cd server
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend should expose its API under `/api/`. Frontend API URLs and secrets must be configured through environment variables; never commit `.env` files.

## Core Product Areas

1. **Authentication** — student registration, JWT login, profiles, and campus email verification.
2. **Marketplace** — product listings, categories, images, conditions, prices, and availability.
3. **Discovery** — search, filtering, sorting, pagination, and related products.
4. **Wishlist** — save and manage products while handling sold or expired listings.
5. **Messaging** — buyer-seller conversations with REST polling initially and WebSocket support later.
6. **Trust and moderation** — seller reviews, listing reports, verification, and administrator controls.
7. **Smart features** — transparent price suggestions, recommendations, listing expiration, and reminders.

## Planned API Areas

```text
/api/accounts/
/api/marketplace/
/api/messaging/
/api/reviews/
/api/core/
```

All API endpoints must validate input on the backend, use appropriate permissions, return consistent errors, and avoid exposing sensitive account data.

## Development Principles

- Inspect existing files before making changes.
- Keep frontend and backend responsibilities separate.
- Validate data on both client and server.
- Enforce authorization in Django, not only in frontend routes.
- Use reusable React components and independent Django apps.
- Keep secrets and uploaded private data out of version control.
- Add loading, empty, success, and error states to user-facing flows.
- Do not mark a feature complete until it has been tested.
- Prefer a working local-development fallback when production infrastructure is unavailable.

## Implementation Roadmap

1. Foundation and API configuration
2. Authentication and student profiles
3. Marketplace listings and image uploads
4. Search, filters, sorting, pagination, and wishlist
5. Buyer-seller messaging and notifications
6. Reviews, reports, and administration
7. Price recommendations, product recommendations, and listing expiration
8. Integration testing, security checks, responsive testing, and deployment documentation

## Team Ownership

### Marketplace

Owns categories, products, images, availability, wishlist, discovery, and recommendation-related marketplace logic.

### Messaging and Search

Owns conversations, messages, unread indicators, notifications, and coordinated search/filter behavior.

### Authentication and Administration

Owns accounts, profiles, JWT authentication, campus verification, permissions, reports, reviews, and moderation.

Teams should agree on API contracts and model relationships before merging dependent work. Migration ownership must be coordinated to avoid conflicting migrations.

## License

This project is currently under development. Add the project license before public distribution.
