# 🏨 UA-Bookings (Hotel Booking & Reviews App)

Цей проєкт — сучасний вебзастосунок на **Flask** з базою даних **PostgreSQL**, створений для демонстрації роботи з реляційними базами даних та реалізації просунутого функціоналу СУБД.

Нижче наведено детальний опис того, як проєкт відповідає всім вашим вимогам.

---

## 📋 Відповідність вимогам проєкту

### 1. Зв'язані таблиці в БД (Реалізовано 3 таблиці)
В базі даних створено три пов'язані таблиці (опис моделей у файлі `models.py`):
*   **`hotels` (Готелі)**: Основна таблиця. Зберігає інформацію про назву, ціну, локацію, опис та динамічні показники рейтингу.
*   **`bookings` (Бронювання)**: Пов'язана з таблицею `hotels` відношенням **один-до-багатьох** (у одного готелю може бути багато бронювань). При видаленні готелю всі його бронювання видаляються автоматично (Cascade Delete).
*   **`reviews` (Відгуки)**: Також пов'язана з `hotels` відношенням **один-до-багатьох** (один готель має багато відгуків). Також підтримує каскадне видалення.

---

### 2. Вебсторінки та форми (Повний CRUD-цикл)
Інтерфейс містить усі необхідні сторінки для роботи з об'єктами (шаблони в папці `templates/`, обробники в `app.py`):
*   **Список об'єктів (Головна сторінка `index.html`)**: Відображає каталог готелів у вигляді карток із пошуком за назвою, фільтрацією за містом та сортуванням (за ціною чи рейтингом).
*   **Перегляд одного об'єкта (`hotel_detail.html`)**: Детальна сторінка готелю. Показує повний опис, статистику оцінок (діаграми відсотків зірок), список відгуків та форму бронювання.
*   **Створення об'єктів через форми (`add_hotel.html`)**: Зручна форма додавання нового готелю з валідацією полів.
*   **Редагування через форми (`edit_hotel.html`)**: Форма для оновлення полів існуючого готелю.
*   **Видалення записів**: Можливість видалення готелю (кнопка на сторінці деталей) та скасування бронювань.

---

### 3. Акуратний та сучасний інтерфейс
Стилізація виконана у файлі `static/css/style.css` за сучасними стандартами веброзробки:
*   Використано приємну колірну палітру (основа — глибокий синій та білий, акценти — золото/бурштин для зірок рейтингу).
*   Застосовано сучасну типографіку (шрифт **Outfit** від Google Fonts).
*   Елементи містять плавні мікро-анімації при наведенні (hover) та фокусуванні (focus).
*   Адаптивна верстка на основі Flexbox та CSS Grid — сайт однаково гарно виглядає як на моніторах, так і на мобільних телефонах.

---

## 🛠️ Реалізація просунутого функціоналу PostgreSQL

Ми реалізували **всі три** просунуті елементи для роботи з базою даних:

### A. Транзакція з можливістю відкоту (Rollback)
Реалізовано в коді Flask у файлі [app.py](file:///C:/Users/User/.gemini/antigravity/scratch/flask_postgres_app/app.py):
*   **Створення бронювання**: [app.py: рядочки 207–245](file:///C:/Users/User/.gemini/antigravity/scratch/flask_postgres_app/app.py#L207-L245) — виконує блокування рядка через `with_for_update()`, зменшує кількість кімнат та додає запис. У разі будь-якої помилки (відсутність кімнат, помилки дат) виконується `db.session.rollback()`.
*   **Скасування бронювання**: [app.py: рядочки 247–267](file:///C:/Users/User/.gemini/antigravity/scratch/flask_postgres_app/app.py#L247-L267) — скасовує бронювання та повертає вільну кімнату готелю в межах єдиної транзакції з відкотом у разі збою.

---

### B. Збережена процедура/функція (Stored PL/pgSQL Function)
Визначено у файлі ініціалізації бази даних [init_db.py: рядочки 64–84](file:///C:/Users/User/.gemini/antigravity/scratch/flask_postgres_app/init_db.py#L64-L84) мовою PL/pgSQL. 

Код функції:
```sql
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
```
Ця функція автоматично перераховує середній рейтинг та кількість відгуків для певного готелю після кожної зміни.

---

### C. Тригер PostgreSQL (Trigger)
Створюється та реєструється на рівні PostgreSQL у файлі [init_db.py: рядочки 88–95](file:///C:/Users/User/.gemini/antigravity/scratch/flask_postgres_app/init_db.py#L88-L95). 

Код тригера:
```sql
DROP TRIGGER IF EXISTS trigger_reviews_changed ON reviews;
CREATE TRIGGER trigger_reviews_changed
AFTER INSERT OR UPDATE OR DELETE ON reviews
FOR EACH ROW
EXECUTE FUNCTION update_hotel_stats();
```
Тригер автоматично запускає збережену функцію `update_hotel_stats()` після будь-яких маніпуляцій з таблицею `reviews`.
