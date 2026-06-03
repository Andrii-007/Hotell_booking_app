import sys
from flask import Flask
from config import Config
from models import db, Hotel, Review, Booking
from sqlalchemy import text, create_engine
from datetime import datetime, date
from urllib.parse import urlparse, urlunparse

def create_db_if_not_exists():
    url = Config.DATABASE_URL
    if not url:
        return
    
    # Parse URL
    parsed = urlparse(url)
    db_name = parsed.path.lstrip('/')
    if not db_name:
        return
        
    # Create connection string for default 'postgres' database
    postgres_parsed = parsed._replace(path='/postgres')
    postgres_url = urlunparse(postgres_parsed)
    
    print(f"Checking if database '{db_name}' exists on PostgreSQL...")
    try:
        # We need isolation_level="AUTOCOMMIT" to run CREATE DATABASE
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")).fetchone()
            if not result:
                print(f"Database '{db_name}' does not exist. Creating database '{db_name}'...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"Database '{db_name}' created successfully!")
            else:
                print(f"Database '{db_name}' already exists.")
        engine.dispose()
    except Exception as e:
        print(f"Automatic database creation check skipped: {e}")
        print("Continuing with standard database connection...")

def init_database():
    # Attempt to create the database if it doesn't exist
    create_db_if_not_exists()
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    print("Connecting to the database...")
    try:
        with app.app_context():
            # Check database connection
            db.session.execute(text("SELECT 1"))
            print("Successfully connected to PostgreSQL database!")
            
            print("Dropping existing tables...")
            db.drop_all()
            
            print("Creating new tables...")
            db.create_all()
            
            # 1. Create Stored PL/pgSQL Function
            print("Creating PL/pgSQL stored function update_hotel_stats()...")
            function_sql = """
            CREATE OR REPLACE FUNCTION update_hotel_stats()
            RETURNS TRIGGER AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    UPDATE hotels
                    SET average_rating = COALESCE((SELECT AVG(rating) FROM reviews WHERE hotel_id = OLD.hotel_id), 0.00),
                        reviews_count = (SELECT COUNT(*) FROM reviews WHERE hotel_id = OLD.hotel_id)
                    WHERE id = OLD.hotel_id;
                    RETURN OLD;
                ELSE
                    UPDATE hotels
                    SET average_rating = COALESCE((SELECT AVG(rating) FROM reviews WHERE hotel_id = NEW.hotel_id), 0.00),
                        reviews_count = (SELECT COUNT(*) FROM reviews WHERE hotel_id = NEW.hotel_id)
                    WHERE id = NEW.hotel_id;
                    RETURN NEW;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
            """
            db.session.execute(text(function_sql))
            
            # 2. Create PostgreSQL Trigger
            print("Creating trigger trigger_reviews_changed on reviews table...")
            trigger_sql = """
            DROP TRIGGER IF EXISTS trigger_reviews_changed ON reviews;
            CREATE TRIGGER trigger_reviews_changed
            AFTER INSERT OR UPDATE OR DELETE ON reviews
            FOR EACH ROW
            EXECUTE FUNCTION update_hotel_stats();
            """
            db.session.execute(text(trigger_sql))
            
            # Commit the table structures, function, and trigger
            db.session.commit()
            print("Database schema and triggers successfully created!")

            # 3. Seed mock data
            print("Seeding initial hotel data...")
            hotel1 = Hotel(
                name="Grand Royal Resort & Spa",
                location="Київ, Україна",
                description="Розкішний п'ятизірковий готель у самому центрі столиці з панорамним видом на Дніпро. SPA-комплекс світового класу, вишукані ресторани та преміум сервіс для найвибагливіших гостей. Відчуйте справжню розкіш та гостинність.",
                price_per_night=3500.00,
                available_rooms=8,
                image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80"
            )
            
            hotel2 = Hotel(
                name="Carpathian Haven",
                location="Яремче, Україна",
                description="Затишний еко-готель в оточенні віковічних карпатських лісів та величних гір. Дерев'яні котеджі з камінами, карпатські чани під відкритим небом, традиційна гуцульська кухня та безліч мальовничих гірських маршрутів поруч.",
                price_per_night=2200.00,
                available_rooms=4,
                image_url="https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=800&q=80"
            )
            
            hotel3 = Hotel(
                name="Odesa Breeze Hotel",
                location="Одеса, Україна",
                description="Сучасний та стильний готель на першій лінії Чорного моря. Власна упорядкована пляжна зона, великий відкритий басейн із морською водою, панорамні тераси з видом на морський схід сонця та вишуканий ресторан середземноморської кухні.",
                price_per_night=2800.00,
                available_rooms=6,
                image_url="https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800&q=80"
            )
            
            hotel4 = Hotel(
                name="Lviv Vintage Boutique",
                location="Львів, Україна",
                description="Елегантний бутик-готель в ретельно реставрованій історичній будівлі старого Львова. Автентичні інтер'єри 19 століття, вишукана кав'ярня-кондитерська, близькість до Площі Ринок та особлива атмосфера затишку і романтики.",
                price_per_night=1950.00,
                available_rooms=3,
                image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=800&q=80"
            )
            
            db.session.add_all([hotel1, hotel2, hotel3, hotel4])
            db.session.commit()
            print("Hotels added successfully!")

            # 4. Seed initial reviews (these will automatically fire the trigger!)
            print("Seeding reviews to test the database trigger...")
            
            reviews = [
                # Grand Royal Resort & Spa reviews (should average ~4.67)
                Review(hotel_id=hotel1.id, reviewer_name="Олександр", rating=5, content="Неймовірний готель! SPA-зона просто фантастична, а обслуговування на найвищому рівні. Рекомендую всім!"),
                Review(hotel_id=hotel1.id, reviewer_name="Марія", rating=5, content="Прекрасний вид на Дніпро з вікна номера. Дуже смачні сніданки та привітний персонал."),
                Review(hotel_id=hotel1.id, reviewer_name="Ігор", rating=4, content="Чудовий сервіс, але ціна трохи кусається. Проте якість відповідає рівню."),
                
                # Carpathian Haven reviews (should average ~5.00)
                Review(hotel_id=hotel2.id, reviewer_name="Ольга", rating=5, content="Найкраще місце для відпочинку в Карпатах! Карпатські чани під зорями — це щось неймовірне. Обов'язково повернемося!"),
                Review(hotel_id=hotel2.id, reviewer_name="Андрій", rating=5, content="Тиша, спокій і чисте гірське повітря. Затишні будиночки з каміном створюють казкову атмосферу."),
                
                # Odesa Breeze Hotel reviews (should average ~4.00)
                Review(hotel_id=hotel3.id, reviewer_name="Дмитро", rating=4, content="Чудовий готель біля самого моря. Басейн чудовий, але хотілося б трохи швидшого сервісу в ресторані."),
                Review(hotel_id=hotel3.id, reviewer_name="Катерина", rating=4, content="Красиві види та гарний пляж. Загалом задоволені відпочинком."),
                
                # Lviv Vintage Boutique reviews (should average ~4.50)
                Review(hotel_id=hotel4.id, reviewer_name="Юлія", rating=5, content="Дуже атмосферний готель. Буквально за крок від площі Ринок. Кава в кав'ярні готелю неймовірна!"),
                Review(hotel_id=hotel4.id, reviewer_name="Сергій", rating=4, content="Приємний дизайн та зручні ліжка. Будівля стара, тому шумоізоляція не ідеальна, але атмосфера це компенсує.")
            ]
            
            db.session.add_all(reviews)
            db.session.commit()
            print("Reviews added successfully!")
            
            # Let's verify if the trigger worked by reading from the DB!
            db.session.expire_all() # clear SQLAlchemy cache
            h1 = db.session.get(Hotel, hotel1.id)
            h2 = db.session.get(Hotel, hotel2.id)
            
            print("\nDatabase trigger verification:")
            print(f"- {h1.name}: Average Rating = {h1.average_rating} (Reviews: {h1.reviews_count})")
            print(f"- {h2.name}: Average Rating = {h2.average_rating} (Reviews: {h2.reviews_count})")
            print("\nDatabase initialization complete! Trigger is fully operational.")
            
    except Exception as e:
        print(f"\n[ERROR] Database initialization failed: {e}", file=sys.stderr)
        print("\n[TIP] Make sure your PostgreSQL server is running and the database matches your .env configurations.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    init_database()
