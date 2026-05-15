# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

IRAQ_CITIES = [
    'هەولێر', 'سلێمانی', 'دهۆک', 'کەرکووک', 'هەڵەبجە',
    'بغداد', 'موسڵ', 'بەسرە', 'نەجەف', 'کەربەلا',
    'تکریت', 'کووت', 'دیالە', 'ڕامادی', 'فەلووجە',
    'سامەڕا', 'بابیل', 'دیوانیە', 'عەماره', 'ناسریه'
]

CAR_BRANDS = [
    'Toyota', 'Kia', 'Hyundai', 'BMW', 'Mercedes-Benz',
    'Volkswagen', 'Audi', 'Honda', 'Nissan', 'Chevrolet',
    'Ford', 'Mitsubishi', 'Suzuki', 'Mazda', 'Peugeot',
    'Renault', 'Land Rover', 'Jeep', 'Lexus', 'Isuzu',
    'Opel', 'Dodge', 'Porsche', 'Volvo', 'Subaru',
    'Infiniti', 'Cadillac', 'Chrysler', 'GMC', 'Hummer',
    'BYD', 'Chery', 'Geely', 'MG', 'Haval',
    'JAC', 'Changan', 'BAIC', 'Lifan', 'Brilliance',
    'Daihatsu', 'Fiat', 'Alfa Romeo', 'Ferrari', 'Lamborghini',
    'Maserati', 'Bentley', 'Rolls-Royce', 'Aston Martin', 'McLaren'
]

FUEL_TYPES = ['بەنزین', 'دیزل', 'هایبرید', 'کارەبایی']
TRANSMISSION_TYPES = ['دەستی', 'ئۆتۆماتیک']

# ------------------ مۆدێلەکان ------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), default='')
    whatsapp = db.Column(db.String(20), default='')
    telegram = db.Column(db.String(80), default='')
    city = db.Column(db.String(50), default='')
    profile_image = db.Column(db.String(300), nullable=True)
    plan = db.Column(db.String(10), default='free')
    plan_expires = db.Column(db.DateTime, nullable=True)
    free_img_limit = db.Column(db.Integer, default=3)
    free_vid_limit = db.Column(db.Integer, default=2)
    email_verified = db.Column(db.Boolean, default=False)
    is_active_account = db.Column(db.Boolean, default=True)
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parts = db.relationship('Part', backref='seller', lazy=True)
    vehicles = db.relationship('Vehicle', backref='seller', lazy=True)
    reels = db.relationship('Reel', backref='owner', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    car_model = db.Column(db.String(80))
    car_brand = db.Column(db.String(80), default='')
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(50), default='')
    image_url = db.Column(db.String(300))
    media_type = db.Column(db.String(10), default='image')
    condition = db.Column(db.String(20), default='used')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # پەیوەندی بۆ وێنەکان
    images = db.relationship('PartImage', backref='part', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='part', lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(80))
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    mileage = db.Column(db.Integer, default=0)
    fuel_type = db.Column(db.String(20), default='بەنزین')
    transmission = db.Column(db.String(20), default='دەستی')
    color = db.Column(db.String(30))
    city = db.Column(db.String(50), default='')
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))
    media_type = db.Column(db.String(10), default='image')
    condition = db.Column(db.String(20), default='used')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # پەیوەندی بۆ وێنەکان
    images = db.relationship('VehicleImage', backref='vehicle', lazy=True, cascade="all, delete-orphan")

class VehicleImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

class PartImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)

class Reel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(300), nullable=False)
    thumbnail_url = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ReelLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reel_id = db.Column(db.Integer, db.ForeignKey('reel.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('reel_id', 'ip_address', name='uq_reel_ip'),)

class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    free_image_limit = db.Column(db.Integer, default=3)
    free_video_limit = db.Column(db.Integer, default=2)
    vip_price = db.Column(db.Float, default=25)
    vip_months = db.Column(db.Integer, default=6)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='part_reviews')
    __table_args__ = (db.UniqueConstraint('part_id', 'user_id', name='uq_part_user_review'),)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notif_type = db.Column(db.String(30), default='info')
    link = db.Column(db.String(300), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
