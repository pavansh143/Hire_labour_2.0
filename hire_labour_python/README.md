# Hire Labour - Python Conversion

This project is a modern Python/Flask conversion of the original PHP Hire Labour system.

## Features
- **Backend**: Flask with SQLAlchemy (SQLite).
- **Frontend**: Premium Vanilla HTML5 and CSS3 (Glassmorphism design).
- **AI Recommendation**: Smart system that recommends top-rated professionals based on community feedback.
- **Language Support**: Seamless toggle between English and Kannada (extensible).
- **Secure Auth**: Role-based access for Admin, Labour, and Public users.

## How to Run

1. **Install Dependencies**:
   ```bash
   pip install flask flask_sqlalchemy flask_login
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the App**:
   Open `http://127.0.0.1:5000` in your browser.

## Sample Accounts (Seeded automatically)
- **Public**: Username: `raj`, Password: `password`
- **Labour**: Username: `pavan`, Password: `password`
- **Admin**: Username: `admin`, Password: `admin123`
