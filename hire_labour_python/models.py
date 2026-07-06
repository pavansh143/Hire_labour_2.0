from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"admin_{self.admin_id}"

class Labour(db.Model, UserMixin):
    __tablename__ = 'labours'
    labour_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    service_offered = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    profile_image = db.Column(db.String(255))
    id_card_image = db.Column(db.String(255))
    selfie_image = db.Column(db.String(255))
    face_encoding = db.Column(db.Text)
    trust_score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='Pending') # Verified, Suspicious, Fake, Pending
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    feedbacks = db.relationship('Feedback', backref='labour', lazy=True)

    def get_id(self):
        return f"labour_{self.labour_id}"

class Public(db.Model, UserMixin):
    __tablename__ = 'publics'
    public_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    profile_image = db.Column(db.String(255))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    feedbacks = db.relationship('Feedback', backref='public', lazy=True)

    def get_id(self):
        return f"public_{self.public_id}"

class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.Integer, db.ForeignKey('publics.public_id'), nullable=False)
    labour_id = db.Column(db.Integer, db.ForeignKey('labours.labour_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    feedback_date = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True)
    sender_type = db.Column(db.String(10), nullable=False)  # 'public' or 'labour'
    sender_id = db.Column(db.Integer, nullable=False)
    receiver_type = db.Column(db.String(10), nullable=False) # 'public' or 'labour'
    receiver_id = db.Column(db.Integer, nullable=False)
    public_id = db.Column(db.Integer, db.ForeignKey('publics.public_id'), nullable=False)
    labour_id = db.Column(db.Integer, db.ForeignKey('labours.labour_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
class WorkShowcase(db.Model):
    __tablename__ = 'work_showcase'
    id = db.Column(db.Integer, primary_key=True)
    labour_id = db.Column(db.Integer, db.ForeignKey('labours.labour_id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
