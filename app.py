from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from models import db, Hotel, Booking, Review
from datetime import datetime
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

@app.route('/')
def index():
    # Handle search, filter, and sorting
    search_query = request.args.get('search', '').strip()
    location_filter = request.args.get('location', '').strip()
    sort_by = request.args.get('sort', '').strip()
    
    # Base query
    query = Hotel.query
    
    # Apply search filter
    if search_query:
        query = query.filter(Hotel.name.ilike(f"%{search_query}%"))
        
    # Apply location filter
    if location_filter:
        query = query.filter(Hotel.location.ilike(f"%{location_filter}%"))
        
    # Apply sorting
    if sort_by == 'price_asc':
        query = query.order_by(Hotel.price_per_night.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Hotel.price_per_night.desc())
    elif sort_by == 'rating_desc':
        query = query.order_by(Hotel.average_rating.desc())
    else:
        query = query.order_by(Hotel.created_at.desc()) # Default: newest
        
    hotels = query.all()
    
    # Get unique locations for the filter dropdown
    locations = [r[0] for r in db.session.query(Hotel.location).distinct().all()]
    # Normalize locations (extract city name before comma)
    cities = sorted(list(set([loc.split(',')[0].strip() for loc in locations if loc])))
    
    return render_template(
        'index.html', 
        hotels=hotels, 
        cities=cities,
        search_query=search_query,
        selected_location=location_filter,
        sort_by=sort_by
    )

@app.route('/hotel/<int:id>')
def hotel_detail(id):
    hotel = db.get_or_404(Hotel, id)
    
    # Sort reviews by newest
    reviews = Review.query.filter_by(hotel_id=id).order_by(Review.created_at.desc()).all()
    # Sort bookings by newest
    bookings = Booking.query.filter_by(hotel_id=id).order_by(Booking.created_at.desc()).all()
    
    # Calculate percentage ratings for progress bars (1 to 5 stars)
    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        if r.rating in star_counts:
            star_counts[r.rating] += 1
            
    total_reviews = len(reviews)
    star_pct = {}
    for star, count in star_counts.items():
        star_pct[star] = int((count / total_reviews) * 100) if total_reviews > 0 else 0
        
    return render_template(
        'hotel_detail.html', 
        hotel=hotel, 
        reviews=reviews, 
        bookings=bookings,
        star_pct=star_pct,
        star_counts=star_counts
    )

@app.route('/hotel/add', methods=['GET', 'POST'])
def add_hotel():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price_per_night', '').strip()
        rooms_str = request.form.get('available_rooms', '').strip()
        image_url = request.form.get('image_url', '').strip()
        
        if not name or not location or not price_str or not rooms_str:
            flash("Будь ласка, заповніть усі обов'язкові поля!", "danger")
            return render_template('add_hotel.html')
            
        try:
            price = float(price_str)
            rooms = int(rooms_str)
            if price <= 0 or rooms < 0:
                raise ValueError()
        except ValueError:
            flash("Некоректне значення для ціни чи кількості номерів!", "danger")
            return render_template('add_hotel.html')
            
        # Default placeholder image if none provided
        if not image_url:
            image_url = "https://images.unsplash.com/photo-1540518614846-7eded433c457?auto=format&fit=crop&w=800&q=80"
            
        try:
            new_hotel = Hotel(
                name=name,
                location=location,
                description=description,
                price_per_night=price,
                available_rooms=rooms,
                image_url=image_url
            )
            db.session.add(new_hotel)
            db.session.commit()
            flash("Готель успішно додано до каталогу!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Помилка збереження: {str(e)}", "danger")
            
    return render_template('add_hotel.html')

@app.route('/hotel/<int:id>/edit', methods=['GET', 'POST'])
def edit_hotel(id):
    hotel = db.get_or_404(Hotel, id)
    
    if request.method == 'POST':
        hotel.name = request.form.get('name', '').strip()
        hotel.location = request.form.get('location', '').strip()
        hotel.description = request.form.get('description', '').strip()
        price_str = request.form.get('price_per_night', '').strip()
        rooms_str = request.form.get('available_rooms', '').strip()
        image_url = request.form.get('image_url', '').strip()
        
        if not hotel.name or not hotel.location or not price_str or not rooms_str:
            flash("Будь ласка, заповніть усі обов'язкові поля!", "danger")
            return render_template('edit_hotel.html', hotel=hotel)
            
        try:
            hotel.price_per_night = float(price_str)
            hotel.available_rooms = int(rooms_str)
            if hotel.price_per_night <= 0 or hotel.available_rooms < 0:
                raise ValueError()
        except ValueError:
            flash("Некоректне значення для ціни чи кількості номерів!", "danger")
            return render_template('edit_hotel.html', hotel=hotel)
            
        if image_url:
            hotel.image_url = image_url
            
        try:
            db.session.commit()
            flash("Дані готелю успішно оновлено!", "success")
            return redirect(url_for('hotel_detail', id=hotel.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Помилка оновлення: {str(e)}", "danger")
            
    return render_template('edit_hotel.html', hotel=hotel)

@app.route('/hotel/<int:id>/delete', methods=['POST'])
def delete_hotel(id):
    hotel = db.get_or_404(Hotel, id)
    try:
        db.session.delete(hotel)
        db.session.commit()
        flash(f"Готель '{hotel.name}' видалено з каталогу разом з усіма бронюваннями та відгуками.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Помилка видалення: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/hotel/<int:id>/book', methods=['POST'])
def book_hotel(id):
    guest_name = request.form.get('guest_name', '').strip()
    check_in_str = request.form.get('check_in_date', '').strip()
    check_out_str = request.form.get('check_out_date', '').strip()
    
    if not guest_name or not check_in_str or not check_out_str:
        flash("Будь ласка, заповніть усі поля для бронювання!", "danger")
        return redirect(url_for('hotel_detail', id=id))
        
    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Некоректний формат дат!", "danger")
        return redirect(url_for('hotel_detail', id=id))
        
    if check_out <= check_in:
        flash("Помилка дат: дата виїзду має бути пізнішою за дату заїзду!", "danger")
        return redirect(url_for('hotel_detail', id=id))
        
    if check_in < datetime.now().date():
        flash("Помилка дат: дата заїзду не може бути в минулому!", "danger")
        return redirect(url_for('hotel_detail', id=id))
        
    # TRANSACTION BLOCK WITH ROW LOCKING
    try:
        # 1. Fetch hotel and lock the row to avoid race condition (double booking)
        hotel = db.session.query(Hotel).filter_by(id=id).with_for_update().first()
        if not hotel:
            flash("Готель не знайдено!", "danger")
            return redirect(url_for('index'))
            
        # 2. Check room availability
        if hotel.available_rooms <= 0:
            raise ValueError("Вибачте, у цьому готелі більше немає вільних номерів!")
            
        # 3. Decrement available rooms
        hotel.available_rooms -= 1
        
        # 4. Calculate total price
        nights = (check_out - check_in).days
        total_price = nights * hotel.price_per_night
        
        # 5. Save the booking
        new_booking = Booking(
            hotel_id=id,
            guest_name=guest_name,
            check_in_date=check_in,
            check_out_date=check_out,
            total_price=total_price
        )
        db.session.add(new_booking)
        
        # 6. Commit transaction
        db.session.commit()
        
        flash(f"Готель успішно заброньовано для {guest_name}! Кількість ночей: {nights}. Сума до сплати: {total_price:.2f} грн.", "success")
    except Exception as e:
        # If anything fails, rollback the transaction (rooms restored, booking canceled)
        db.session.rollback()
        flash(f"Помилка під час транзакції бронювання: {str(e)}", "danger")
        
    return redirect(url_for('hotel_detail', id=id))

@app.route('/booking/<int:id>/delete', methods=['POST'])
def cancel_booking(id):
    # Cancel booking and restore available rooms (Transaction)
    try:
        booking = db.get_or_404(Booking, id)
        hotel_id = booking.hotel_id
        
        # Start transaction with locking
        hotel = db.session.query(Hotel).filter_by(id=hotel_id).with_for_update().first()
        if hotel:
            # Restore the room
            hotel.available_rooms += 1
            
        db.session.delete(booking)
        db.session.commit()
        flash("Бронювання успішно скасовано, номер знову доступний для замовлень!", "success")
        return redirect(url_for('hotel_detail', id=hotel_id))
    except Exception as e:
        db.session.rollback()
        flash(f"Помилка скасування бронювання: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/hotel/<int:id>/review', methods=['POST'])
def add_review(id):
    reviewer_name = request.form.get('reviewer_name', '').strip()
    rating_str = request.form.get('rating', '').strip()
    content = request.form.get('content', '').strip()
    
    if not reviewer_name or not rating_str or not content:
        flash("Будь ласка, заповніть усі поля відгуку!", "danger")
        return redirect(url_for('hotel_detail', id=id))
        
    try:
        rating = int(rating_str)
        if rating < 1 or rating > 5:
            raise ValueError()
    except ValueError:
        flash("Оцінка повинна бути числом від 1 до 5!", "danger")
        return redirect(url_for('hotel_detail', id=id))
        
    try:
        new_review = Review(
            hotel_id=id,
            reviewer_name=reviewer_name,
            rating=rating,
            content=content
        )
        db.session.add(new_review)
        db.session.commit()
        flash("Ваш відгук додано! Рейтинг готелю автоматично перераховано за допомогою тригера PostgreSQL.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Помилка додавання відгуку: {str(e)}", "danger")
        
    return redirect(url_for('hotel_detail', id=id))

if __name__ == '__main__':
    app.run(debug=True)
