from app import app, db
from models import User

with app.app_context():
    email = 'xalo9016@gmail.com'  # ڕاستەوخۆ دانا
    user = User.query.filter_by(email=email).first()
    if user:
        user.user_type = 'admin'
        db.session.commit()
        print(f'✅ {email} بوو بە ئەدمین')
    else:
        print(f'❌ بەکارهێنەر بە ئیمەیڵی {email} نەدۆزرایەوە')