cat > README.md << 'EOF'
# KUKUNET - Poultry Farm Management Platform

![KUKUNET Banner](https://via.placeholder.com/1200x400/2E7D32/white?text=KUKUNET+Poultry+Platform)

A multi-tenant poultry farm management, marketplace, and learning platform designed for farmers in Uganda and across Africa.

## 🚀 Features

### Farm Management
- Flock tracking and management
- Daily records (mortality, feed, water)
- Vaccination scheduling
- Expense tracking
- Production analytics

### Marketplace
- Buy/sell farm inputs and produce
- Product categories
- Shopping cart and orders
- Seller dashboard

### Learning Academy
- Video courses
- Quizzes and certificates
- Progress tracking
- Offline-friendly content

### Multi-tenant SaaS
- Tenant isolation
- Role-based access (Farmer, Supplier, Trainer, Admin)
- Subscription plans

## 🛠️ Tech Stack

- **Backend**: Django 4.x, Django REST Framework
- **Database**: MySQL
- **Frontend**: Tailwind CSS, jQuery
- **Task Queue**: Celery + Redis
- **Authentication**: Phone number + 4-digit PIN
- **Deployment**: Gunicorn + Nginx

## 📋 Prerequisites

- Python 3.10+
- MySQL 8.0+
- Redis (for Celery)
- Virtual environment (recommended)

## 🔧 Installation

### 1. Clone the repository
```bash
git clone https://github.com/simeonbayo/kukunet.git
cd kukunet