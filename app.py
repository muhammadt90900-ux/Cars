import os, re, secrets, logging, random, string, hashlib, hmac, json
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Part, Vehicle, Reel, ReelLike, SiteSettings, IRAQ_CITIES, CAR_BRANDS, FUEL_TYPES, TRANSMISSION_TYPES, VehicleImage, PartImage
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import magic as magic_module
from flask_talisman import Talisman
from PIL import Image
from flask import request, render_template

# ئەم فەنکشنە لێرە زیاد بکە بۆ بچووککردنەوەی وێنە
def save_optimized_image(file, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = secrets.token_hex(8) + ".webp"
    filepath = os.path.join(folder, filename)
    try:
        img = Image.open(file)
        img = img.convert("RGB")
        if img.width > 1200:
            img.thumbnail((1200, 1200))
        img.save(filepath, "WEBP", quality=75)
        return filename
    except Exception as e:
        print(f"Error: {e}")
        return None


load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

csp = {
    'default-src': ["'self'"],
    'img-src': ["'self'", 'data:', 'https://logo.clearbit.com', '*'],
    'media-src': ["'self'", '*'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net', 'https://fonts.googleapis.com', 'https://cdnjs.cloudflare.com'],
    'font-src': ["'self'", 'https://fonts.gstatic.com', 'https://cdnjs.cloudflare.com'],
    'script-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net', 'https://cdnjs.cloudflare.com'],
}
Talisman(app, content_security_policy=csp, force_https=False)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)

_raw_key = os.environ.get('SECRET_KEY', '')
if not _raw_key or len(_raw_key) < 16:
    _raw_key = secrets.token_hex(32)
    logger.warning("SECRET_KEY not set or too short in .env — generated a random one for this session.")
app.config['SECRET_KEY'] = _raw_key

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kurdauto.db')
app.config['WTF_CSRF_ENABLED'] = True
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

GMAIL_USER = os.environ.get('GMAIL_USER', '')
GMAIL_PASS = os.environ.get('GMAIL_PASS', '')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXT = {'mp4', 'mov', 'webm', 'avi'}
ALLOWED_IMAGE_MIME = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
ALLOWED_VIDEO_MIME = {'video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo'}

TRANSLATIONS = {
    'ku': {
        'site_name': 'کورد ئۆتۆ', 'home': 'سەرەکی', 'login': 'چوونەژوورەوە', 'logout': 'چوونەدەرەوە',
        'register': 'تۆمارکردن', 'dashboard': 'داشبۆرد', 'admin_panel': 'پانێلی ئەدمین',
        'add_part': 'زیادکردنی پارچە', 'edit_profile': 'دەستکاریکردنی پڕۆفایل', 'plans': 'پلانەکان',
        'reels': 'ریلەکان', 'privacy': 'پرایڤەسی', 'terms': 'مەرجەکان', 'footer': '© 2025 کورد ئۆتۆ',
        'search': 'گەڕان', 'search_placeholder': 'گەڕان بکە...', 'all_cities': 'هەموو شارەکان',
        'all_brands': 'هەموو براندەکان', 'min_price': 'کەمترین نرخ', 'max_price': 'زۆرترین نرخ',
        'dinar': 'دینار', 'detail': 'وردەکاری', 'no_parts': 'هیچ پارچەیەک نەدۆزرایەوە',
        'no_vehicles': 'هیچ ئۆتۆمبێلێک نەدۆزرایەوە', 'parts': 'پارچەکان', 'vehicles': 'ئۆتۆمبێلەکان',
        'add_vehicle': 'زیادکردنی ئۆتۆمبێل', 'phone': 'ژمارەی تەلەفۆن', 'email': 'ئیمەیل',
        'password': 'وشەی نهێنی', 'confirm_password': 'دووبارەکردنەوەی وشەی نهێنی',
        'username': 'ناوی بەکارهێنەر', 'seller': 'فرۆشیار', 'buyer': 'کڕیار', 'user_type': 'جۆری هەژمار',
        'city': 'شار', 'price': 'نرخ', 'description': 'وەسف', 'submit': 'ناردن', 'cancel': 'هەڵوەشاندنەوە',
        'edit': 'دەستکاری', 'delete': 'سڕینەوە', 'views': 'بینینەکان', 'likes': 'لایکەکان',
        'vip': 'VIP', 'free': 'خۆڕایی', 'monthly': 'مانگانە', 'verify_email': 'پشتڕاستکردنەوەی ئیمەیل',
        'otp_sent': 'کۆدەکە بۆ ئیمەیلەکەت نێردرا', 'invalid_otp': 'کۆدەکە هەڵەیە یان کاتەکەی تەواو بووە',
        'profile': 'پڕۆفایل', 'notifications': 'ئاگادارکردنەوەکان', 'messages': 'نامەکان',
        'send_message': 'ناردنی نامە', 'no_messages': 'هیچ نامەیەک نییە', 'brand': 'براند',
        'model': 'مۆدێل', 'year': 'ساڵ', 'mileage': 'کیلۆمەتر', 'fuel_type': 'جۆری سووتەمەنی',
        'transmission': 'گێربۆکس', 'color': 'ڕەنگ',
    },
    'ar': {
        'site_name': 'كورد أوتو', 'home': 'الرئيسية', 'login': 'تسجيل الدخول', 'logout': 'تسجيل الخروج',
        'register': 'التسجيل', 'dashboard': 'لوحة التحكم', 'admin_panel': 'لوحة الادمن',
        'add_part': 'إضافة قطعة', 'edit_profile': 'تعديل الملف', 'plans': 'الخطط', 'reels': 'ريلز',
        'privacy': 'الخصوصية', 'terms': 'الشروط', 'footer': '© 2025 كورد أوتو', 'search': 'بحث',
        'search_placeholder': 'ابحث هنا...', 'all_cities': 'كل المدن', 'all_brands': 'كل الماركات',
        'min_price': 'أقل سعر', 'max_price': 'أعلى سعر', 'dinar': 'دينار', 'detail': 'التفاصيل',
        'no_parts': 'لا توجد قطع', 'no_vehicles': 'لا توجد سيارات', 'parts': 'القطع', 'vehicles': 'السيارات',
        'add_vehicle': 'إضافة سيارة', 'phone': 'رقم الهاتف', 'email': 'البريد الإلكتروني',
        'password': 'كلمة المرور', 'confirm_password': 'تأكيد كلمة المرور', 'username': 'اسم المستخدم',
        'seller': 'بائع', 'buyer': 'مشتري', 'user_type': 'نوع الحساب', 'city': 'المدينة', 'price': 'السعر',
        'description': 'الوصف', 'submit': 'إرسال', 'cancel': 'إلغاء', 'edit': 'تعديل', 'delete': 'حذف',
        'views': 'المشاهدات', 'likes': 'الإعجابات', 'vip': 'VIP', 'free': 'مجاني', 'monthly': 'شهري',
        'verify_email': 'تحقق من البريد', 'otp_sent': 'تم إرسال الكود', 'invalid_otp': 'الكود غلط أو منتهي',
        'profile': 'الملف الشخصي', 'notifications': 'الإشعارات', 'messages': 'الرسائل',
        'send_message': 'إرسال رسالة', 'no_messages': 'لا توجد رسائل', 'brand': 'الماركة', 'model': 'الموديل',
        'year': 'السنة', 'mileage': 'المسافة', 'fuel_type': 'نوع الوقود', 'transmission': 'ناقل الحركة',
        'color': 'اللون',
    },
    'en': {
        'site_name': 'Kurd Auto', 'home': 'Home', 'login': 'Login', 'logout': 'Logout', 'register': 'Register',
        'dashboard': 'Dashboard', 'admin_panel': 'Admin Panel', 'add_part': 'Add Part',
        'edit_profile': 'Edit Profile', 'plans': 'Plans', 'reels': 'Reels', 'privacy': 'Privacy',
        'terms': 'Terms', 'footer': '© 2025 Kurd Auto', 'search': 'Search', 'search_placeholder': 'Search here...',
        'all_cities': 'All Cities', 'all_brands': 'All Brands', 'min_price': 'Min Price', 'max_price': 'Max Price',
        'dinar': 'Dinar', 'detail': 'Detail', 'no_parts': 'No parts found', 'no_vehicles': 'No vehicles found',
        'parts': 'Parts', 'vehicles': 'Vehicles', 'add_vehicle': 'Add Vehicle', 'phone': 'Phone Number',
        'email': 'Email', 'password': 'Password', 'confirm_password': 'Confirm Password', 'username': 'Username',
        'seller': 'Seller', 'buyer': 'Buyer', 'user_type': 'Account Type', 'city': 'City', 'price': 'Price',
        'description': 'Description', 'submit': 'Submit', 'cancel': 'Cancel', 'edit': 'Edit', 'delete': 'Delete',
        'views': 'Views', 'likes': 'Likes', 'vip': 'VIP', 'free': 'Free', 'monthly': 'Monthly',
        'verify_email': 'Verify Email', 'otp_sent': 'Code sent to your email',
        'invalid_otp': 'Invalid or expired code', 'profile': 'Profile', 'notifications': 'Notifications',
        'messages': 'Messages', 'send_message': 'Send Message', 'no_messages': 'No messages', 'brand': 'Brand',
        'model': 'Model', 'year': 'Year', 'mileage': 'Mileage', 'fuel_type': 'Fuel Type',
        'transmission': 'Transmission', 'color': 'Color',
    },
}

def get_lang():
    return session.get('lang', 'ku')

def t(key):
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS['ku']).get(key, key)

app.jinja_env.globals['t'] = t
app.jinja_env.globals['get_lang'] = get_lang
app.jinja_env.globals['now'] = datetime.utcnow
app.jinja_env.globals['IRAQ_CITIES'] = IRAQ_CITIES
app.jinja_env.globals['CAR_BRANDS'] = CAR_BRANDS
app.jinja_env.globals['CAR_BRAND_LOGOS'] = CAR_BRAND_LOGOS
app.jinja_env.globals['FUEL_TYPES'] = FUEL_TYPES
app.jinja_env.globals['TRANSMISSION_TYPES'] = TRANSMISSION_TYPES

# ══════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════
def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def allowed_file_magic(file, allowed_mime_set):
    try:
        file.stream.seek(0)
        mime = magic_module.from_buffer(file.stream.read(2048), mime=True)
        file.stream.seek(0)
        return mime in allowed_mime_set
    except Exception:
        return False

def save_file(file, user_id, prefix=''):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"{prefix}{user_id}_{int(datetime.utcnow().timestamp())}.{ext}")
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # بچووککردنەوەی وێنە بۆ پاراستنی باندویدس
    if ext in ALLOWED_IMAGE_EXT:
        try:
            img = Image.open(file.stream)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            max_width = 1200
            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            img.save(path, optimize=True, quality=85)
        except Exception as e:
            logger.error(f"Image compression error: {e}")
            file.save(path)
    else:
        file.save(path)

    return url_for('static', filename=f'uploads/{filename}')

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(to_email, otp_code, lang='ku'):
    if not GMAIL_USER or not GMAIL_PASS:
        logger.warning("Gmail credentials not set. OTP not sent.")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Kurd Auto - کۆدی پشتڕاستکردنەوە'
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        html = f"""
        <div dir="rtl" style="font-family:Tahoma,sans-serif;background:#0a0a0a;color:#fff;padding:40px;border-radius:12px;max-width:400px;margin:auto;">
          <h2 style="color:#f59e0b;">🚗 Kurd Auto</h2>
          <p>کۆدی پشتڕاستکردنەوەی ئیمەیلەکەت:</p>
          <div style="background:#1a1a2e;border:2px solid #f59e0b;border-radius:8px;padding:20px;text-align:center;font-size:36px;letter-spacing:8px;font-weight:bold;color:#f59e0b;">
            {otp_code}
          </div>
          <p style="color:#888;font-size:12px;margin-top:20px;">ئەم کۆدە تەنها 10 خولەک کار دەکات.</p>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return False

def get_settings():
    s = SiteSettings.query.first()
    if not s:
        s = SiteSettings()
        db.session.add(s)
        db.session.commit()
    return s

def count_monthly_uploads(user_id, media_type):
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return Part.query.filter(
        Part.seller_id == user_id,
        Part.media_type == media_type,
        Part.created_at >= start_of_month
    ).count()

def is_vip_active(user):
    return user.plan == 'vip' and user.plan_expires and user.plan_expires > datetime.utcnow()

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'admin':
            flash('ئەم پەرەیە تەنها بۆ ئەدمینە.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def activate_vip_for_user(user):
    s = get_settings()
    user.plan = 'vip'
    user.plan_expires = datetime.utcnow() + timedelta(days=30 * s.vip_months)
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_tables():
    with app.app_context():
        db.create_all()
        if not SiteSettings.query.first():
            db.session.add(SiteSettings())
            db.session.commit()
        logger.info("Tables created/checked.")

# ══════════════════════════════════
# LANGUAGE
# ══════════════════════════════════
@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ('ku', 'ar', 'en'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# ══════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        user_type = request.form.get('user_type', 'buyer')
        city = request.form.get('city', '')

        if not username or not email or not password:
            flash('تکایە هەموو خانەکان پڕ بکەرەوە.', 'danger')
            return redirect(request.url)
        if password != confirm:
            flash('وشەی نهێنیەکان یەک نین.', 'danger')
            return redirect(request.url)
        if User.query.filter_by(email=email).first():
            flash('ئەم ئیمەیلە پێشتر تۆماربووە.', 'danger')
            return redirect(request.url)
        if User.query.filter_by(username=username).first():
            flash('ئەم ناوە پێشتر تۆماربووە.', 'danger')
            return redirect(request.url)

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            phone=phone,
            user_type=user_type,
            city=city,
            email_verified=False,
            plan='free'
        )
        db.session.add(user)
        db.session.commit()

        otp = generate_otp()
        session['otp_code'] = otp
        session['otp_email'] = email
        session['otp_expires'] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        send_otp_email(email, otp)

        flash('تۆمارکردن سەرکەوتوو بوو! تکایە ئیمەیلەکەت پشتڕاست بکەرەوە.', 'success')
        return redirect(url_for('verify_email_page'))

    return render_template('register.html', cities=IRAQ_CITIES)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        # Debug: ببینە ئایا user دەدۆزرێتەوە
        print(f"Login attempt for email: {email}, user exists: {user is not None}")

        if user:
            # Debug: ببینە هاشی وشەی نهێنی هاوشێوەیە
            print(f"Stored hash: {user.password_hash}")
            print(f"Password check result: {check_password_hash(user.password_hash, password)}")

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(t('login_success'), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(t('invalid_credentials'), 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email_page():
    if request.method == 'POST':
        code = request.form.get('otp', '').strip()
        stored = session.get('otp_code')
        expires = session.get('otp_expires')
        email = session.get('otp_email')
        if not stored or not expires or not email:
            flash('تکایە دووبارە تۆمار بکە.', 'danger')
            return redirect(url_for('register'))
        if datetime.utcnow() > datetime.fromisoformat(expires):
            flash('کاتی کۆدەکە تەواو بووە.', 'danger')
            return redirect(url_for('verify_email_page'))
        if code != stored:
            flash('کۆدەکە هەڵەیە.', 'danger')
            return redirect(url_for('verify_email_page'))
        user = User.query.filter_by(email=email).first()
        if user:
            user.email_verified = True
            db.session.commit()
            session.pop('otp_code', None)
            session.pop('otp_email', None)
            session.pop('otp_expires', None)
            login_user(user)
            flash('ئیمەیلەکەت پشتڕاست کرایەوە!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('verify_email.html', email=session.get('otp_email', ''))

@app.route('/resend_otp')
def resend_otp():
    email = session.get('otp_email')
    if not email:
        return redirect(url_for('register'))
    otp = generate_otp()
    session['otp_code'] = otp
    session['otp_expires'] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    send_otp_email(email, otp)
    flash('کۆدی نوێ نێردرا.', 'success')
    return redirect(url_for('verify_email_page'))

# ══════════════════════════════════
# STATIC PAGES
# ══════════════════════════════════
@app.route('/plans')
def plans():
    s = get_settings()
    return render_template('plans.html', settings=s)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/about')
def about():
    return render_template('about.html')

# ══════════════════════════════════
# INDEX (تەنها یەک جار ئەمە هەیە)
# ══════════════════════════════════
@app.route('/')
def index():
    list_type = request.args.get('type', 'part')
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    city_filter = request.args.get('city', '')
    brand_filter = request.args.get('brand', '')
    min_price = request.args.get('min_price', '', type=str).strip()
    max_price = request.args.get('max_price', '', type=str).strip()

    # --- فلتەرە نوێیەکانی ئۆتۆمبێل ---
    year_filter = request.args.get('year', '', type=str).strip()
    fuel_filter = request.args.get('fuel_type', '')
    trans_filter = request.args.get('transmission', '')
    # -----------------------------------------

    per_page = 9

    if list_type == 'vehicle':
        query = Vehicle.query
    else:
        query = Part.query

    if q:
        if list_type == 'vehicle':
            query = query.filter(
                (Vehicle.title.ilike(f'%{q}%')) |
                (Vehicle.description.ilike(f'%{q}%')) |
                (Vehicle.brand.ilike(f'%{q}%')) |
                (Vehicle.model.ilike(f'%{q}%'))
            )
        else:
            query = query.filter(
                (Part.name.ilike(f'%{q}%')) |
                (Part.description.ilike(f'%{q}%')) |
                (Part.car_model.ilike(f'%{q}%')) |
                (Part.car_brand.ilike(f'%{q}%'))
            )
    if city_filter:
        if list_type == 'part':
            query = query.filter(Part.city == city_filter)
        else:
            query = query.filter(Vehicle.city == city_filter)
    if brand_filter:
        if list_type == 'part':
            query = query.filter(Part.car_brand == brand_filter)
        else:
            query = query.filter(Vehicle.brand == brand_filter)

@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        new_vehicle = Vehicle(
            title=request.form.get('title'),
            brand=request.form.get('brand'),
            model=request.form.get('model'),
            year=int(request.form.get('year', 2020)),
            price=float(request.form.get('price', 0)),
            mileage=int(request.form.get('mileage', 0)),
            fuel_type=request.form.get('fuel_type'),
            transmission=request.form.get('transmission'),
            color=request.form.get('color'),
            city=request.form.get('city'),
            description=request.form.get('description'),
            seller_id=current_user.id
        )
        db.session.add(new_vehicle)
        db.session.flush()

        # بەشی وەرگرتنی چەند وێنەیەک
        files = request.files.getlist('image_files')
        for file in files:
            if file and file.filename != '':
                filename = save_optimized_image(file, app.config['UPLOAD_FOLDER'])
                if filename:
                    img_entry = VehicleImage(image_url=filename, vehicle_id=new_vehicle.id)
                    db.session.add(img_entry)
                    if not new_vehicle.image_url:
                        new_vehicle.image_url = filename

        db.session.commit()
        flash('ئۆتۆمبێلەکە بە سەرکەوتوویی زیادکرا', 'success')
        return redirect(url_for('index'))

    return render_template('add_vehicle (1).html', cities=IRAQ_CITIES, brands=CAR_BRANDS)

    # --- بەشی فلتەری نوێ ---
    if year_filter and list_type == 'vehicle':
        try:
            query = query.filter(Vehicle.year == int(year_filter))
        except ValueError:
            pass
    if fuel_filter and list_type == 'vehicle':
        query = query.filter(Vehicle.fuel_type == fuel_filter)
    if trans_filter and list_type == 'vehicle':
        query = query.filter(Vehicle.transmission == trans_filter)
    # -----------------------

    if min_price:
        try:
            price_field = Part.price if list_type == 'part' else Vehicle.price
            query = query.filter(price_field >= float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            price_field = Part.price if list_type == 'part' else Vehicle.price
            query = query.filter(price_field <= float(max_price))
        except ValueError:
            pass

    if list_type == 'vehicle':
        items = query.order_by(Vehicle.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        items = query.order_by(Part.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('index.html',
        list_type=list_type,
        parts=items.items if list_type == 'part' else [],
        vehicles=items.items if list_type == 'vehicle' else [],
        pagination=items,
        search_query=q,
        city_filter=city_filter,
        brand_filter=brand_filter,
        min_price=min_price,
        max_price=max_price,
        year_filter=year_filter,
        fuel_filter=fuel_filter,
        trans_filter=trans_filter
    )

# ══════════════════════════════════
# PARTS
# ══════════════════════════════════
@app.route('/part/<int:part_id>')
def part_detail(part_id):
    part = db.session.get(Part, part_id)
    if not part:
        return render_template('404.html'), 404
    part.views = (part.views or 0) + 1
    db.session.commit()
    return render_template('part_detail.html', part=part)

@app.route('/add_part', methods=['GET', 'POST'])
@login_required
def add_part():
    if request.method == 'POST':
        new_part = Part(
            name=request.form.get('name'),
            car_brand=request.form.get('car_brand'),
            car_model=request.form.get('car_model'),
            city=request.form.get('city'),
            description=request.form.get('description'),
            price=float(request.form.get('price', 0)),
            condition=request.form.get('condition', 'used'),
            seller_id=current_user.id
        )
        db.session.add(new_part)
        db.session.flush()

        files = request.files.getlist('part_images')
        for file in files:
            if file and file.filename != '':
                filename = save_optimized_image(file, app.config['UPLOAD_FOLDER'])
                if filename:
                    img_entry = PartImage(image_url=filename, part_id=new_part.id)
                    db.session.add(img_entry)
                    if not new_part.image_url:
                        new_part.image_url = filename

        db.session.commit()
        flash('پارچەکە زیادکرا', 'success')
        return redirect(url_for('index'))

    return render_template('add_part (1).html', cities=IRAQ_CITIES, brands=CAR_BRANDS)


@app.route('/edit_part/<int:part_id>', methods=['GET', 'POST'])
@login_required
def edit_part(part_id):
    part = db.session.get(Part, part_id)
    if not part or part.seller_id != current_user.id:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        part.name = request.form.get('name', part.name).strip()
        part.description = request.form.get('description', part.description).strip()
        part.car_brand = request.form.get('car_brand', part.car_brand)
        part.car_model = request.form.get('car_model', part.car_model).strip()
        part.city = request.form.get('city', part.city)
        try:
            part.price = float(request.form.get('price', part.price))
        except ValueError:
            pass
        if 'image_file' in request.files and request.files['image_file'].filename:
            f = request.files['image_file']
            if allowed_file_magic(f, ALLOWED_IMAGE_MIME):
                part.image_url = save_file(f, current_user.id)
                part.media_type = 'image'
        db.session.commit()
        flash('پارچەکە نوێ کرایەوە!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_part.html', part=part, cities=IRAQ_CITIES, brands=CAR_BRANDS)

@app.route('/delete_part/<int:part_id>', methods=['POST'])
@login_required
def delete_part(part_id):
    part = db.session.get(Part, part_id)
    if part and (part.seller_id == current_user.id or current_user.user_type == 'admin'):
        db.session.delete(part)
        db.session.commit()
        flash('پارچەکە سڕایەوە.', 'success')
    return redirect(url_for('dashboard'))

# ══════════════════════════════════
# VEHICLES
# ══════════════════════════════════
@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if current_user.user_type != 'seller':
        return redirect(url_for('index'))
    if not current_user.email_verified:
        flash('تکایە ئیمەیلەکەت پشتڕاست بکەرەوە.', 'warning')
        return redirect(url_for('verify_email_page'))
    if request.method == 'POST':
        title = request.form['title']
        brand = request.form['brand']
        model = request.form['model']
        year = int(request.form['year'])
        try:
            price = float(request.form['price'])
            if price < 0: raise ValueError
        except ValueError:
            flash('نرخێکی دروست بنووسە!', 'danger')
            return redirect(request.url)
        mileage = int(request.form.get('mileage', 0))
        fuel_type = request.form.get('fuel_type', 'بەنزین')
        transmission = request.form.get('transmission', 'دەستی')
        color = request.form.get('color', '')
        city = request.form.get('city', '')
        description = request.form.get('description', '')

        image_url = None
        media_type = 'image'
        if 'image_file' in request.files and request.files['image_file'].filename:
            f = request.files['image_file']
            if allowed_file_magic(f, ALLOWED_IMAGE_MIME):
                image_url = save_file(f, current_user.id)
                media_type = 'image'
            else:
                flash('جۆری وێنە ڕێگەپێدراو نییە.', 'danger')
                return redirect(request.url)
        elif 'video_file' in request.files and request.files['video_file'].filename:
            f = request.files['video_file']
            if allowed_file_magic(f, ALLOWED_VIDEO_MIME):
                image_url = save_file(f, current_user.id, 'vid_')
                media_type = 'video'
            else:
                flash('جۆری ڤیدیۆ ڕێگەپێدراو نییە.', 'danger')
                return redirect(request.url)
        elif request.form.get('image_url'):
            raw = request.form['image_url']
            if not re.match(r'^https?://', raw, re.I):
                flash('ئادرەسی وێنەکە دروست نییە.', 'danger')
                return redirect(request.url)
            image_url = raw

        vehicle = Vehicle(title=title, brand=brand, model=model, year=year, price=price,
                          mileage=mileage, fuel_type=fuel_type, transmission=transmission,
                          color=color, city=city, description=description,
                          image_url=image_url, media_type=media_type,
                          seller_id=current_user.id)
        db.session.add(vehicle)
        db.session.commit()
        flash('ئۆتۆمبێلەکەت زیاد کرا!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_vehicle.html', cities=IRAQ_CITIES, brands=CAR_BRANDS,
                           fuel_types=FUEL_TYPES, transmission_types=TRANSMISSION_TYPES)

@app.route('/vehicle/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        return render_template('404.html'), 404
    vehicle.views = (vehicle.views or 0) + 1
    db.session.commit()
    return render_template('vehicle_detail.html', vehicle=vehicle)

@app.route('/edit_vehicle/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.seller_id != current_user.id:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        vehicle.title = request.form.get('title', vehicle.title).strip()
        vehicle.brand = request.form.get('brand', vehicle.brand)
        vehicle.model = request.form.get('model', vehicle.model).strip()
        vehicle.year = int(request.form.get('year', vehicle.year))
        vehicle.city = request.form.get('city', vehicle.city)
        vehicle.fuel_type = request.form.get('fuel_type', vehicle.fuel_type)
        vehicle.transmission = request.form.get('transmission', vehicle.transmission)
        vehicle.color = request.form.get('color', vehicle.color)
        vehicle.description = request.form.get('description', vehicle.description)

        try:
            vehicle.price = float(request.form.get('price', vehicle.price))
            vehicle.mileage = int(request.form.get('mileage', vehicle.mileage))
        except ValueError:
            pass

        if 'image_file' in request.files and request.files['image_file'].filename:
            f = request.files['image_file']
            if allowed_file_magic(f, ALLOWED_IMAGE_MIME):
                vehicle.image_url = save_file(f, current_user.id)
                vehicle.media_type = 'image'

        db.session.commit()
        flash('ئۆتۆمبێلەکەت نوێ کرایەوە!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_vehicle.html', vehicle=vehicle, cities=IRAQ_CITIES,
                           brands=CAR_BRANDS, fuel_types=FUEL_TYPES, transmission_types=TRANSMISSION_TYPES)

@app.route('/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if vehicle and (vehicle.seller_id == current_user.id or current_user.user_type == 'admin'):
        db.session.delete(vehicle)
        db.session.commit()
        flash('ئۆتۆمبێلەکە سڕایەوە.', 'success')
    return redirect(url_for('dashboard'))

# ══════════════════════════════════
# REELS
# ══════════════════════════════════
@app.route('/reels')
def reels():
    reels_list = Reel.query.order_by(Reel.created_at.desc()).all()
    return render_template('reels.html', reels=reels_list)

@app.route('/reels/add', methods=['GET', 'POST'])
@login_required
def add_reel():
    if not current_user.email_verified:
        flash('تکایە ئیمەیلەکەت پشتڕاست بکەرەوە.', 'warning')
        return redirect(url_for('verify_email_page'))
    if request.method == 'POST':
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        video_url = None
        thumbnail_url = None
        if 'video_file' in request.files and request.files['video_file'].filename:
            f = request.files['video_file']
            if allowed_file_magic(f, ALLOWED_VIDEO_MIME):
                video_url = save_file(f, current_user.id, 'reel_')
            else:
                flash('جۆری ڤیدۆ ڕێگەپێدراو نییە.', 'danger')
                return redirect(request.url)
        if 'thumb_file' in request.files and request.files['thumb_file'].filename:
            tf = request.files['thumb_file']
            if allowed_file_magic(tf, ALLOWED_IMAGE_MIME):
                thumbnail_url = save_file(tf, current_user.id, 'thumb_')
        if not video_url:
            flash('تکایە ڤیدۆیەک بارکە.', 'danger')
            return redirect(request.url)
        reel = Reel(title=title, description=description, video_url=video_url,
                    thumbnail_url=thumbnail_url, owner_id=current_user.id)
        db.session.add(reel)
        db.session.commit()
        flash('ریلەکەت بە سەرکەوتوویی زیاد کرا!', 'success')
        return redirect(url_for('reels'))
    return render_template('add_reel.html')
@csrf.exempt
@app.route('/reel/<int:reel_id>/like', methods=['POST'])
@limiter.limit("10 per minute")
def like_reel(reel_id):
    reel = db.session.get(Reel, reel_id)
    if not reel:
        return jsonify({'error': 'not found'}), 404
    ip = get_client_ip()
    existing = ReelLike.query.filter_by(reel_id=reel_id, ip_address=ip).first()
    if existing:
        return jsonify({'likes': reel.likes, 'already_liked': True})
    try:
        like = ReelLike(reel_id=reel_id, ip_address=ip)
        db.session.add(like)
        reel.likes += 1
        db.session.commit()
        return jsonify({'likes': reel.likes, 'already_liked': False})
    except Exception:
        db.session.rollback()
        return jsonify({'likes': reel.likes, 'already_liked': True})
@csrf.exempt
@app.route('/reel/<int:reel_id>/view', methods=['POST'])
def view_reel(reel_id):
    reel = db.session.get(Reel, reel_id)
    if reel:
        reel.views += 1
        db.session.commit()
        return jsonify({'views': reel.views})
    return jsonify({'error': 'not found'}), 404

# ══════════════════════════════════
# DASHBOARD
# ══════════════════════════════════
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'admin':
        return redirect(url_for('admin_panel'))
    if current_user.user_type not in ('seller', 'buyer'):
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    parts_paginated = Part.query.filter_by(seller_id=current_user.id)\
        .order_by(Part.created_at.desc()).paginate(page=page, per_page=4, error_out=False)
    vehicles = Vehicle.query.filter_by(seller_id=current_user.id)\
        .order_by(Vehicle.created_at.desc()).all()
    img_count = count_monthly_uploads(current_user.id, 'image')
    vid_count = count_monthly_uploads(current_user.id, 'video')
    vip = is_vip_active(current_user)
    return render_template('dashboard.html',
        parts=parts_paginated.items, pagination=parts_paginated,
        vehicles=vehicles,
        img_count=img_count, vid_count=vid_count, vip=vip)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username', current_user.username).strip()
        current_user.phone = request.form.get('phone', current_user.phone).strip()
        current_user.city = request.form.get('city', current_user.city)
        new_pass = request.form.get('new_password', '')
        if new_pass:
            current_user.password_hash = generate_password_hash(new_pass)
        db.session.commit()
        flash('پڕۆفایلەکەت نوێ کرایەوە!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_profile.html', cities=IRAQ_CITIES)

# ══════════════════════════════════
# ADMIN
# ══════════════════════════════════
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = User.query.order_by(User.created_at.desc()).all()
    parts = Part.query.order_by(Part.created_at.desc()).all()
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).all()
    reels_list = Reel.query.order_by(Reel.created_at.desc()).all()
    s = get_settings()
    return render_template('admin.html', users=users, parts=parts,
                           vehicles=vehicles, reels=reels_list, settings=s)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = db.session.get(User, user_id)
    if user and user.user_type != 'admin':
        db.session.delete(user)
        db.session.commit()
        flash('بەکارهێنەرەکە سڕایەوە.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/activate_vip/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_activate_vip(user_id):
    user = db.session.get(User, user_id)
    if user:
        activate_vip_for_user(user)
        flash(f'{user.username} VIP کرایەوە.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/settings', methods=['POST'])
@login_required
@admin_required
def admin_settings():
    s = get_settings()
    try:
        s.vip_price = float(request.form.get('vip_price', s.vip_price))
        s.vip_months = int(request.form.get('vip_months', s.vip_months))
        s.free_image_limit = int(request.form.get('free_image_limit', s.free_image_limit))
        s.free_video_limit = int(request.form.get('free_video_limit', s.free_video_limit))
        db.session.commit()
        flash('ڕێکخستنەکان پاشەکەوت کران.', 'success')
    except Exception as e:
        flash(f'هەڵە: {e}', 'danger')
    return redirect(url_for('admin_panel'))

# ══════════════════════════════════
# ERROR HANDLERS
# ══════════════════════════════════
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
@app.route('/search')
def search():
    query = request.args.get('q', '')
    category = request.args.get('category', 'all')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    vehicles = []
    parts = []

    # گەڕان بۆ ئۆتۆمبێل
    if category in ('all', 'vehicle'):
        vehicle_query = Vehicle.query
        if query:
            vehicle_query = vehicle_query.filter(
                (Vehicle.brand.ilike(f'%{query}%')) |
                (Vehicle.model.ilike(f'%{query}%')) |
                (Vehicle.description.ilike(f'%{query}%'))
            )
        if min_price:
            vehicle_query = vehicle_query.filter(Vehicle.price >= float(min_price))
        if max_price:
            vehicle_query = vehicle_query.filter(Vehicle.price <= float(max_price))
        vehicles = vehicle_query.all()

    # گەڕان بۆ پارچە
    if category in ('all', 'part'):
        part_query = Part.query
        if query:
            part_query = part_query.filter(
                (Part.name.ilike(f'%{query}%')) |
                (Part.description.ilike(f'%{query}%'))
            )
        if min_price:
            part_query = part_query.filter(Part.price >= float(min_price))
        if max_price:
            part_query = part_query.filter(Part.price <= float(max_price))
        parts = part_query.all()

    return render_template('search_results.html',
                           vehicles=vehicles,
                           parts=parts,
                           query=query,
                           category=category)
# ══════════════════════════════════
# MAIN
# ══════════════════════════════════
if __name__ == '__main__':
    create_tables()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
