from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Hotel(db.Model):
    __tablename__ = 'hotels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_per_night = db.Column(db.Numeric(10, 2), nullable=False)
    available_rooms = db.Column(db.Integer, default=5, nullable=False)
    
    # These two fields are automatically updated by the PostgreSQL DB trigger
    average_rating = db.Column(db.Numeric(3, 2), default=0.00, nullable=False)
    reviews_count = db.Column(db.Integer, default=0, nullable=False)
    
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with cascade delete
    bookings = db.relationship('Booking', backref='hotel', cascade='all, delete-orphan', lazy=True)
    reviews = db.relationship('Review', backref='hotel', cascade='all, delete-orphan', lazy=True)
    
    def __repr__(self):
        return f"<Hotel {self.name}>"


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def total_nights(self):
        delta = self.check_out_date - self.check_in_date
        return max(delta.days, 1)  # minimum 1 night
        
    def __repr__(self):
        return f"<Booking {self.guest_name} at Hotel ID {self.hotel_id}>"


class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    reviewer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5 stars
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Review from {self.reviewer_name} (Rating: {self.rating})>"
