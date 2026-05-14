# Specifiche Tecniche — SoftwareSales
**Piattaforma Ecommerce per la Vendita di Licenze Software**

Versione: 1.0  
Data: 2026-05-08  
Autore: Praxyon AI System

---

## 1. Visione e Obiettivi

SoftwareSales è una piattaforma B2C/B2B per la vendita e gestione di licenze software digitali. Consente a venditori (ISV — Independent Software Vendors) di pubblicare i propri prodotti e a clienti di acquistare, scaricare e gestire le proprie licenze.

### Obiettivi primari
- Vendita self-service di licenze software con checkout immediato
- Generazione e consegna automatica delle chiavi di licenza via email
- Gestione abbonamenti (SaaS) con rinnovo automatico
- Portale clienti per visualizzare e scaricare le proprie licenze
- Dashboard venditori per monitorare vendite e gestire prodotti
- Integrazione pagamenti (Stripe) con supporto IVA europea

---

## 2. Architettura di Sistema

### Stack tecnologico

| Layer | Tecnologia |
|-------|-----------|
| Backend API | Python 3.12 + FastAPI |
| Database relazionale | PostgreSQL 15 |
| Cache / sessioni | Redis 7 |
| Pagamenti | Stripe (Checkout + Webhooks) |
| Email transazionali | SendGrid / SMTP |
| Storage file (installer) | S3-compatible (Cloudflare R2 o MinIO) |
| Frontend | React 18 + Vite (gestito da Codex) |
| Autenticazione | JWT + OAuth2 Google |
| Deploy | Docker Compose → VPS Hetzner |
| CI/CD | GitHub Actions |

### Schema architetturale

```
Cliente Browser
      │
      ▼
  Frontend (React)
      │ REST/JSON
      ▼
  FastAPI Backend
   ├── Auth Service (JWT + Google OAuth)
   ├── Product Service (catalogo, versioni)
   ├── Order Service (checkout, pagamento)
   ├── License Service (generazione chiavi)
   ├── Subscription Service (abbonamenti SaaS)
   ├── Download Service (link firmati S3)
   └── Notification Service (email, webhook)
      │
      ├── PostgreSQL (dati persistenti)
      ├── Redis (sessioni, task queue)
      └── Stripe (pagamenti)
```

---

## 3. Modello Dati

### 3.1 Entità principali

#### `users`
```sql
id              UUID PRIMARY KEY
email           VARCHAR(255) UNIQUE NOT NULL
name            VARCHAR(255)
role            ENUM('customer', 'vendor', 'admin')
google_id       VARCHAR(255)
created_at      TIMESTAMP WITH TIME ZONE
last_login_at   TIMESTAMP WITH TIME ZONE
is_active       BOOLEAN DEFAULT TRUE
```

#### `products`
```sql
id              UUID PRIMARY KEY
vendor_id       UUID REFERENCES users(id)
name            VARCHAR(255) NOT NULL
slug            VARCHAR(255) UNIQUE NOT NULL
description     TEXT
short_desc      VARCHAR(500)
category        VARCHAR(100)
tags            JSONB
is_published    BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP WITH TIME ZONE
updated_at      TIMESTAMP WITH TIME ZONE
```

#### `product_variants`
```sql
id              UUID PRIMARY KEY
product_id      UUID REFERENCES products(id)
name            VARCHAR(255)           -- es. "Pro", "Enterprise", "Monthly"
license_type    ENUM('perpetual', 'subscription', 'trial')
price_cents     INTEGER NOT NULL       -- prezzo in centesimi (EUR)
currency        VARCHAR(3) DEFAULT 'EUR'
billing_period  ENUM('once', 'monthly', 'yearly') DEFAULT 'once'
max_activations INTEGER DEFAULT 1
stripe_price_id VARCHAR(255)
is_active       BOOLEAN DEFAULT TRUE
```

#### `orders`
```sql
id              UUID PRIMARY KEY
user_id         UUID REFERENCES users(id)
status          ENUM('pending', 'paid', 'cancelled', 'refunded')
total_cents     INTEGER NOT NULL
currency        VARCHAR(3) DEFAULT 'EUR'
stripe_session_id VARCHAR(255)
stripe_payment_intent VARCHAR(255)
invoice_number  VARCHAR(50) UNIQUE
vat_number      VARCHAR(50)           -- per fatturazione B2B
country_code    VARCHAR(2)
vat_rate        NUMERIC(5,2)
created_at      TIMESTAMP WITH TIME ZONE
paid_at         TIMESTAMP WITH TIME ZONE
```

#### `order_items`
```sql
id              UUID PRIMARY KEY
order_id        UUID REFERENCES orders(id)
variant_id      UUID REFERENCES product_variants(id)
quantity        INTEGER DEFAULT 1
unit_price_cents INTEGER NOT NULL
```

#### `licenses`
```sql
id              UUID PRIMARY KEY
order_item_id   UUID REFERENCES order_items(id)
user_id         UUID REFERENCES users(id)
product_id      UUID REFERENCES products(id)
variant_id      UUID REFERENCES product_variants(id)
license_key     VARCHAR(255) UNIQUE NOT NULL
status          ENUM('active', 'expired', 'revoked', 'suspended')
activations_used INTEGER DEFAULT 0
max_activations INTEGER
issued_at       TIMESTAMP WITH TIME ZONE
expires_at      TIMESTAMP WITH TIME ZONE   -- NULL = perpetua
last_checked_at TIMESTAMP WITH TIME ZONE
```

#### `subscriptions`
```sql
id                  UUID PRIMARY KEY
user_id             UUID REFERENCES users(id)
variant_id          UUID REFERENCES product_variants(id)
license_id          UUID REFERENCES licenses(id)
stripe_subscription_id VARCHAR(255)
status              ENUM('active', 'past_due', 'cancelled', 'trialing')
current_period_start TIMESTAMP WITH TIME ZONE
current_period_end   TIMESTAMP WITH TIME ZONE
cancel_at_period_end BOOLEAN DEFAULT FALSE
```

#### `downloads`
```sql
id              UUID PRIMARY KEY
product_id      UUID REFERENCES products(id)
version         VARCHAR(50)
platform        ENUM('windows', 'mac', 'linux', 'universal')
filename        VARCHAR(255)
s3_key          VARCHAR(500)
file_size_bytes BIGINT
checksum_sha256 VARCHAR(64)
release_notes   TEXT
is_latest       BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP WITH TIME ZONE
```

#### `license_activations`
```sql
id              UUID PRIMARY KEY
license_id      UUID REFERENCES licenses(id)
machine_id      VARCHAR(255)
machine_name    VARCHAR(255)
ip_address      INET
activated_at    TIMESTAMP WITH TIME ZONE
last_seen_at    TIMESTAMP WITH TIME ZONE
is_active       BOOLEAN DEFAULT TRUE
```

---

## 4. API Endpoints

### Autenticazione (`/api/auth`)
```
POST   /api/auth/login              # Login con Google OAuth
GET    /api/auth/callback           # OAuth callback
GET    /api/auth/me                 # Profilo utente corrente
POST   /api/auth/logout             # Logout
POST   /api/auth/register           # Registrazione email/password (futuro)
```

### Catalogo Prodotti (`/api/products`)
```
GET    /api/products                # Lista prodotti pubblicati (paginata)
GET    /api/products/{slug}         # Dettaglio prodotto
GET    /api/products/{slug}/variants # Varianti con prezzi
GET    /api/categories              # Lista categorie
```

### Ordini e Checkout (`/api/orders`)
```
POST   /api/checkout                # Crea sessione Stripe Checkout
GET    /api/checkout/{session_id}/status  # Verifica stato pagamento
GET    /api/orders                  # Lista ordini dell'utente
GET    /api/orders/{id}             # Dettaglio ordine
GET    /api/orders/{id}/invoice     # Scarica fattura PDF
```

### Licenze (`/api/licenses`)
```
GET    /api/licenses                # Lista licenze dell'utente
GET    /api/licenses/{id}           # Dettaglio licenza + chiave
POST   /api/licenses/{id}/activate  # Registra nuova attivazione macchina
DELETE /api/licenses/{id}/activations/{machine_id}  # Rimuovi attivazione
POST   /api/licenses/verify         # API pubblica: verifica chiave licenza
```

### Download (`/api/downloads`)
```
GET    /api/downloads/{license_id}       # Lista versioni scaricabili
POST   /api/downloads/{download_id}/link # Genera link firmato S3 (10 min)
```

### Abbonamenti (`/api/subscriptions`)
```
GET    /api/subscriptions           # Abbonamenti attivi
POST   /api/subscriptions/{id}/cancel  # Cancella a fine periodo
POST   /api/subscriptions/{id}/resume  # Riattiva abbonamento
```

### Vendor Dashboard (`/api/vendor`) — solo ruolo vendor
```
GET    /api/vendor/products         # I miei prodotti
POST   /api/vendor/products         # Crea prodotto
PUT    /api/vendor/products/{id}    # Aggiorna prodotto
POST   /api/vendor/products/{id}/publish   # Pubblica
GET    /api/vendor/orders           # Ordini ricevuti
GET    /api/vendor/stats            # Revenue, MAU, churn
POST   /api/vendor/downloads        # Upload nuovo installer
```

### Webhooks Stripe (`/webhooks`)
```
POST   /webhooks/stripe             # Riceve eventi Stripe (checkout.session.completed, invoice.paid, etc.)
```

---

## 5. Servizi Core

### 5.1 License Key Generator
- Formato: `XXXX-XXXX-XXXX-XXXX` (base36, crittograficamente sicuro)
- Alternativa per prodotti enterprise: RSA-signed JWT
- Verifica offline possibile con chiave pubblica embedded nel client
- API pubblica `/api/licenses/verify` per validazione online

### 5.2 Stripe Integration
- Checkout Session per pagamento one-shot (perpetual)
- Subscription per SaaS (monthly/yearly)
- Webhook handler per conferma pagamento → attivazione licenza automatica
- Customer Portal Stripe per gestione metodo pagamento
- Calcolo IVA automatico via Stripe Tax (EU VAT rules)

### 5.3 Download Service
- File installer su S3/R2 (non su VPS — storage scalabile)
- Link firmati con scadenza 10 minuti (no hotlinking)
- Verifica licenza attiva prima di generare link
- Tracking download per analytics venditori

### 5.4 Notification Service
- Email transazionale: conferma ordine, consegna licenza, rinnovo, scadenza imminente
- Template HTML responsive (conferma ordine con riepilogo + chiave licenza)
- Webhook opzionale per venditori (event push su ordini/rinnovi)

---

## 6. Sicurezza

- **Autenticazione**: JWT httponly secure cookie + Google OAuth2
- **Autorizzazione**: RBAC (customer / vendor / admin)
- **Rate limiting**: SlowAPI su endpoint pubblici (es. `/api/licenses/verify` max 10 req/min per IP)
- **License key**: entropy 128 bit, one-way hash in DB (solo hash, non chiave in chiaro)
- **Download links**: HMAC-SHA256 firmati con scadenza
- **Webhook Stripe**: verifica `stripe-signature` header
- **Input validation**: Pydantic v2 su tutti gli endpoint
- **SQL injection**: solo ORM (SQLAlchemy 2.0), nessuna query raw
- **HTTPS**: obbligatorio in produzione, HSTS header

---

## 7. Piano di Sviluppo

### Fase 1 — Foundation (Sprint 1-2)
**Obiettivo**: scheletro del backend funzionante, DB schema, auth

| Task | Agente | Priorità |
|------|--------|----------|
| Setup FastAPI + PostgreSQL + migrations Alembic | DEV | P0 |
| Modelli SQLAlchemy (users, products, variants) | DEV | P0 |
| Auth service (JWT + Google OAuth) | DEV | P0 |
| CRUD prodotti + varianti (vendor) | DEV | P1 |
| Pydantic schemas per tutti i modelli | DEV | P1 |
| Test unitari modelli + auth | TESTER | P1 |

### Fase 2 — Commerce Core (Sprint 3-4)
**Obiettivo**: checkout end-to-end funzionante

| Task | Agente | Priorità |
|------|--------|----------|
| Integrazione Stripe Checkout | DEV | P0 |
| Webhook Stripe → attivazione licenza | DEV | P0 |
| License key generator + store | DEV | P0 |
| Order management service | DEV | P0 |
| Email conferma ordine + consegna licenza | DEV | P1 |
| Test integrazione checkout | TESTER | P1 |

### Fase 3 — Subscriptions & Downloads (Sprint 5-6)
**Obiettivo**: SaaS subscription + download sicuri

| Task | Agente | Priorità |
|------|--------|----------|
| Stripe Subscription (create, renew, cancel) | DEV | P0 |
| License activation + machine tracking | DEV | P0 |
| Download service (S3 signed URLs) | DEV | P0 |
| License verify API (online check) | DEV | P1 |
| Email rinnovo e scadenza imminente | DEV | P1 |
| Test subscriptions + downloads | TESTER | P1 |

### Fase 4 — Vendor Dashboard & Polish (Sprint 7-8)
**Obiettivo**: vendor self-service, analytics, produzione-ready

| Task | Agente | Priorità |
|------|--------|----------|
| Vendor stats API (revenue, ordini) | DEV | P0 |
| Upload installer + versioning | DEV | P0 |
| Admin panel (gestione utenti, licenze) | DEV | P1 |
| Generazione fattura PDF | DEV | P1 |
| Rate limiting + security hardening | DEV | P1 |
| Review architettura finale | REVIEWER | P1 |
| Documentazione API (OpenAPI) | ANALYST | P2 |

---

## 8. Struttura Repository

```
softwaresales/
├── src/
│   ├── api/
│   │   ├── app.py              # FastAPI app factory
│   │   ├── auth/               # JWT, OAuth, middleware
│   │   ├── routes/             # Endpoint per dominio
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   ├── licenses.py
│   │   │   ├── downloads.py
│   │   │   ├── subscriptions.py
│   │   │   └── vendor.py
│   │   └── webhooks/
│   │       └── stripe.py
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── license.py
│   │   ├── subscription.py
│   │   └── download.py
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic
│   │   ├── license_service.py
│   │   ├── stripe_service.py
│   │   ├── download_service.py
│   │   └── notification_service.py
│   ├── db/
│   │   ├── base.py             # SQLAlchemy engine + session
│   │   └── migrations/        # Alembic migrations
│   └── core/
│       ├── config.py           # Settings da .env
│       └── security.py        # JWT, HMAC utils
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── TECHNICAL_SPEC.md
```

---

## 9. Variabili d'Ambiente

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/softwaresales

# Auth
SECRET_KEY=<random 256-bit>
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
ALLOWED_DOMAINS=sposito.eu  # opzionale: restringi login

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLIC_KEY=pk_live_...

# Storage
S3_ENDPOINT_URL=https://...r2.cloudflarestorage.com
S3_BUCKET=softwaresales-installers
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG....
EMAIL_FROM=noreply@softwaresales.com

# App
FRONTEND_URL=https://softwaresales.com
ENVIRONMENT=production
```

---

## 10. Metriche e KPI

| Metrica | Target |
|---------|--------|
| Latenza API p95 | < 200ms |
| Uptime | 99.9% |
| Tempo consegna licenza post-pagamento | < 30 secondi |
| Tasso successo webhook Stripe | > 99.5% |
| Tempo generazione link download | < 500ms |
