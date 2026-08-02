import time
import mysql.connector
MAX_SUBSTITUTIONS_PER_DAY = 4



def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="alpha_admin",
        password="alpha@123",
        database="alpha_substitution",
        autocommit=False,
        connection_timeout=30
    )

def create_database():

    conn = mysql.connector.connect(
        host="localhost",
        user="alpha_admin",
        password="alpha@123"
    )

    c = conn.cursor()

    c.execute(
        """
        CREATE DATABASE IF NOT EXISTS alpha_substitution
        """
    )

    conn.commit()
    conn.close()

def initialize_database(): 
    conn = mysql.connector.connect( host="localhost", user="alpha_admin", password="alpha@123", database="alpha_substitution" ) 
    c = conn.cursor() 
    # Teachers table 
    c.execute( """ CREATE TABLE IF NOT EXISTS teachers ( id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL, subject VARCHAR(100), contact VARCHAR(20) ) """ ) 
    # Timetable table 
    c.execute( """ CREATE TABLE IF NOT EXISTS timetable ( id INT AUTO_INCREMENT PRIMARY KEY, teacher_id INT, day VARCHAR(20), period1 VARCHAR(100), period2 VARCHAR(100), period3 VARCHAR(100), period4 VARCHAR(100), period5 VARCHAR(100), period6 VARCHAR(100), period7 VARCHAR(100), period8 VARCHAR(100), period9 VARCHAR(100), FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE ) """ ) 
    # Absences table 
    c.execute( """ CREATE TABLE IF NOT EXISTS absences ( id INT AUTO_INCREMENT PRIMARY KEY, teacher_id INT, date DATE, day VARCHAR(20), FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE ) """ ) 
    # Substitutions table 
    c.execute( """ CREATE TABLE IF NOT EXISTS substitutions ( id INT AUTO_INCREMENT PRIMARY KEY, absence_id INT, substitute_teacher_id INT NULL, period INT, class_name VARCHAR(100), FOREIGN KEY (absence_id) REFERENCES absences(id) ON DELETE CASCADE, FOREIGN KEY (substitute_teacher_id) REFERENCES teachers(id) ON DELETE CASCADE ) """ ) 
    c.execute( """ CREATE TABLE IF NOT EXISTS teacher_classes ( id INT AUTO_INCREMENT PRIMARY KEY, teacher_id INT NOT NULL, class_name VARCHAR(50) NOT NULL, FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE ) """ )
    c.execute( """ CREATE TABLE IF NOT EXISTS classes (id INT AUTO_INCREMENT PRIMARY KEY,class_name VARCHAR(50) UNIQUE NOT NULL)""");
    #users table
    c.execute(
    """
    CREATE TABLE IF NOT EXISTS users(

        id INT AUTO_INCREMENT PRIMARY KEY,

        username VARCHAR(100) UNIQUE,

        password VARCHAR(100),

        role VARCHAR(20),

        teacher_id INT NULL,

        FOREIGN KEY (teacher_id)
        REFERENCES teachers(id)
        ON DELETE CASCADE

    )
    """
)      
    #admin user
    c.execute(
    """
    SELECT *

    FROM users

    WHERE username='admin'
    """
)

    admin = c.fetchone()

    if admin is None:

        c.execute(
        """
        INSERT INTO users(

            username,
            password,
            role

        )

        VALUES(

            %s,
            %s,
            %s

        )
        """,

        (
            "admin",
            "admin@123",
            "admin"
        )
    )
    # Settings table 
    c.execute( """ CREATE TABLE IF NOT EXISTS settings( id INT PRIMARY KEY, staff_password VARCHAR(100) ) """ ) 
    # Insert default staff password 
    c.execute( """ SELECT * FROM settings WHERE id=1 """ ) 
    setting = c.fetchone() 
    if setting is None: 
        c.execute( """ INSERT INTO settings( id, staff_password ) VALUES( 1, %s ) """, ( "staff@123", ) )
    conn.commit() 
    conn.close()

def load_substitution_cache(absence_date, day):

    conn = connect_db()
    c = conn.cursor()

    cache = {}

    # -----------------------------
    # All Teacher IDs
    # -----------------------------
    c.execute("""
        SELECT id,name,subject
        FROM teachers
    """)

    teacher_rows=c.fetchall()

    cache["teacher_ids"] = [row[0]for row in teacher_rows]

    cache["teacher_names"]={row[0]:row[1] for row in teacher_rows}

    cache["teacher_subjects"]={row[0]:row[2] for row in teacher_rows}

    # -----------------------------
    # Timetables
    # -----------------------------
    c.execute("""
        SELECT
            teacher_id,
            period1,
            period2,
            period3,
            period4,
            period5,
            period6,
            period7,
            period8,
            period9

        FROM timetable

        WHERE day=%s
    """, (day,))

    cache["timetables"] = {}

    cache["free_periods"] = {}

    cache["working_periods"] = {}

    for row in c.fetchall():

        teacher_id = row[0]

        periods = list(row[1:])

        cache["timetables"][teacher_id] = periods

        cache["free_periods"][teacher_id] = periods.count("Free")

        working = []
        for p in periods:

            if p == "Free":
                working.append(False)
            else:
                working.append(True)

        cache["working_periods"][teacher_id] = working

    # -----------------------------
    # Teacher Classes
    # -----------------------------
    c.execute("""
        SELECT
            teacher_id,
            class_name

        FROM teacher_classes
    """)

    cache["teacher_classes"] = {}

    for teacher_id, class_name in c.fetchall():

        cache["teacher_classes"].setdefault(
            teacher_id,
            set()
        ).add(class_name)

    # -----------------------------
    # Today's Absent Teachers
    # -----------------------------
    c.execute("""
        SELECT teacher_id

        FROM absences

        WHERE date=%s
    """, (absence_date,))

    cache["absent_teachers"] = {

        row[0]

        for row in c.fetchall()

    }

    # -----------------------------
    # Today's Substitutions
    # -----------------------------
    c.execute("""
        SELECT

            s.substitute_teacher_id,

            s.period

        FROM substitutions s

        JOIN absences a

        ON s.absence_id=a.id

        WHERE a.date=%s

        AND s.substitute_teacher_id IS NOT NULL
    """, (absence_date,))

    cache["assigned_periods"] = {}

    cache["substitution_count"] = {}

    for teacher_id, period in c.fetchall():

        cache["assigned_periods"].setdefault(
            teacher_id,
            set()
        ).add(period)

        cache["substitution_count"][teacher_id] = (

            cache["substitution_count"].get(
                teacher_id,
                0
            ) + 1

        )

    conn.close()

    return cache

def is_teacher_unavailable_on_day(
        teacher_name,
        day):

    if (
        teacher_name.strip().casefold()
        == "mr. gowtham"
        and
        day.strip().casefold()
        == "tuesday"
    ):
        return True

    return False

def update_teacher_full(
        teacher_id,
        name,
        subject,
        contact,
        classes,
        timetable):

    conn = connect_db()
    c = conn.cursor()

    try:

        # Update teacher information
        c.execute(
            """
            UPDATE teachers

            SET
                name=%s,
                subject=%s,
                contact=%s

            WHERE id=%s
            """,

            (
                name,
                subject,
                contact,
                teacher_id
            )
        )


        # Delete old capable classes
        c.execute(
            """
            DELETE FROM teacher_classes

            WHERE teacher_id=%s
            """,

            (teacher_id,)
        )


        # Insert new capable classes
        if classes:

            class_values = [

                (
                    teacher_id,
                    class_name
                )

                for class_name in classes
            ]

            c.executemany(
                """
                INSERT INTO teacher_classes(
                    teacher_id,
                    class_name
                )

                VALUES(%s, %s)
                """,

                class_values
            )


        # Update timetable
        timetable_values = []

        for row in timetable:

            day = row[0]

            periods = row[1:]

            timetable_values.append(
                (
                    periods[0],
                    periods[1],
                    periods[2],
                    periods[3],
                    periods[4],
                    periods[5],
                    periods[6],
                    periods[7],
                    periods[8],
                    teacher_id,
                    day
                )
            )


        c.executemany(
            """
            UPDATE timetable

            SET
                period1=%s,
                period2=%s,
                period3=%s,
                period4=%s,
                period5=%s,
                period6=%s,
                period7=%s,
                period8=%s,
                period9=%s

            WHERE teacher_id=%s

            AND day=%s
            """,

            timetable_values
        )


        # Save everything together
        conn.commit()


    except Exception:

        conn.rollback()

        raise


    finally:

        c.close()
        conn.close()

def has_three_consecutive_periods_cached(
        cache,
        teacher_id,
        period):

    working = cache["working_periods"][teacher_id][:]

    for assigned in cache["assigned_periods"].get(
            teacher_id,
            set()):

        working[assigned-1] = True

    working[period-1] = True

    count = 0

    for status in working:

        if status:

            count += 1

            if count > 3:

                return True

        else:

            count = 0

    return False

def can_teacher_handle_class(
        teacher_id,
        class_name):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT *

        FROM teacher_classes

        WHERE

        teacher_id = %s

        AND

        class_name = %s
        """,

        (
            teacher_id,
            class_name
        )
    )

    result = c.fetchone()

    conn.close()

    return result is not None

def update_teacher_classes(
        teacher_id,
        classes):

    conn = connect_db()
    c = conn.cursor()

    c.execute(

        """
        DELETE FROM teacher_classes
        WHERE teacher_id=%s
        """,

        (teacher_id,)
    )

    for class_name in classes:

        c.execute(

            """
            INSERT INTO teacher_classes(

            teacher_id,
            class_name

            )

            VALUES(%s,%s)
            """,

            (

                teacher_id,

                class_name

            )
        )

    conn.commit()

    conn.close()

def get_teacher_classes(
        teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT class_name
        FROM teacher_classes
        WHERE teacher_id=%s
        """,

        (teacher_id,)
    )

    classes = [

        row[0]

        for row in c.fetchall()

    ]

    conn.close()

    return classes

def get_all_classes():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT class_name
        FROM classes
        ORDER BY class_name
        """
    )

    classes = c.fetchall()

    conn.close()

    return classes

def update_user_password(
        user_id,
        new_password):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        UPDATE users

        SET password=%s

        WHERE id=%s
        """,

        (
            new_password,
            user_id
        )
    )

    conn.commit()

    conn.close()

def add_teacher_classes(
        teacher_id,
        classes):

    conn = connect_db()
    c = conn.cursor()

    for class_name in classes:

        c.execute(
            """
            INSERT INTO teacher_classes(
                teacher_id,
                class_name
            )

            VALUES(
                %s,
                %s
            )
            """,

            (
                teacher_id,
                class_name
            )
        )

    conn.commit()
    conn.close()

def get_absences_by_date(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
        a.id,
        t.name,
        a.date,
        a.day

        FROM absences a

        JOIN teachers t

        ON a.teacher_id = t.id

        WHERE a.date=%s

        ORDER BY t.name
        """,

        (date,)
    )

    absences = c.fetchall()

    conn.close()

    return absences

def get_all_substitutions_report():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        a.date,
        s.period,
        s.class_name,
        t.name

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        LEFT JOIN teachers t

        ON s.substitute_teacher_id = t.id

        ORDER BY a.date DESC, s.period
        """
    )

    records = c.fetchall()

    conn.close()

    return records

def get_all_absences_report():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        t.name,
        a.date,
        a.day

        FROM absences a

        JOIN teachers t

        ON a.teacher_id = t.id

        ORDER BY a.date DESC
        """
    )

    records = c.fetchall()

    conn.close()

    return records

def update_admin_password(new_password):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        UPDATE users

        SET password=%s

        WHERE username='admin'
        """,

        (
            new_password,
        )
    )

    conn.commit()

    conn.close()

def update_staff_password(new_password):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        UPDATE settings

        SET staff_password=%s

        WHERE id=1
        """,

        (
            new_password,
        )
    )

    conn.commit()

    conn.close()

def get_staff_password():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT staff_password

        FROM settings

        WHERE id=1
        """
    )

    password = c.fetchone()[0]

    conn.close()

    return password


def login_user(
        username,
        password):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        id,
        username,
        role,
        teacher_id

        FROM users

        WHERE

        username=%s

        AND

        password=%s
        """,

        (
            username,
            password
        )
    )

    user = c.fetchone()

    conn.close()

    return user

def get_teacher_details(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
        name,
        subject

        FROM teachers

        WHERE id=%s
        """,

        (teacher_id,)
    )

    teacher = c.fetchone()

    conn.close()

    return teacher

def count_absent_teachers(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)
        FROM absences
        WHERE date=%s
        """,

        (date,)
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def search_absences(name="", date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
    SELECT

    a.id,
    t.name,
    a.date,
    a.day

    FROM absences a

    JOIN teachers t

    ON a.teacher_id = t.id

    WHERE 1=1
    """

    values = []

    if name:

        query += """
        AND t.name LIKE %s
        """

        values.append(
            "%" + name.lower() + "%"
        )

    if date:

        query += """
        AND a.date = %s
        """

        values.append(
            date
        )

    query += """
    ORDER BY a.date DESC
    """

    c.execute(
        query,
        tuple(values)
    )

    absences = c.fetchall()

    conn.close()

    return absences

def count_substitutions(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)

        FROM substitutions s

        JOIN absences a

        ON s.absence_id=a.id

        WHERE a.date=%s
        """,

        (date,)
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def count_absences_today(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)

        FROM absences

        WHERE date=%s
        """,

        (date,)
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def count_substitutions_today_dashboard(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)

        FROM substitutions s

        JOIN absences a

        ON s.absence_id=a.id

        WHERE a.date=%s
        """,

        (date,)
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def fetch_only_today_substitutions(today_date):

    conn = connect_db()

    c = conn.cursor()

    c.execute(
        """
        SELECT
            s.period,
            absent_teacher.name,
            s.class_name,
            substitute_teacher.name,
            s.manual_substitute_name

        FROM substitutions s

        JOIN absences a
        ON s.absence_id = a.id

        JOIN teachers absent_teacher
        ON a.teacher_id = absent_teacher.id

        LEFT JOIN teachers substitute_teacher
        ON s.substitute_teacher_id = substitute_teacher.id

        WHERE a.date = %s

        ORDER BY s.period
        """,

        (today_date,)
    )

    records = c.fetchall()

    c.close()

    conn.close()

    return records

def count_unavailable_substitutions(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)

        FROM substitutions s

        JOIN absences a

        ON s.absence_id=a.id

        WHERE

        a.date=%s

        AND

        s.substitute_teacher_id IS NULL
        AND (s.manual_substitute_name IS NULL OR TRIM(s.manual_substitute_name) = '')
        """,

        (date,)
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def get_dashboard_stats(date):

    conn = connect_db()
    c = conn.cursor()

    try:

        # Total teachers
        c.execute(
            """
            SELECT COUNT(*)
            FROM teachers
            """
        )

        total_teachers = c.fetchone()[0]


        # Today's absences
        c.execute(
            """
            SELECT COUNT(*)
            FROM absences
            WHERE date=%s
            """,
            (date,)
        )

        absences_today = c.fetchone()[0]


        # Today's substitutions
        c.execute(
            """
            SELECT COUNT(*)
            FROM substitutions s

            JOIN absences a
            ON s.absence_id = a.id

            WHERE a.date=%s
            """,
            (date,)
        )

        substitutions_today = c.fetchone()[0]


        # Today's unavailable substitutions
        c.execute(
            """
            SELECT COUNT(*)
            FROM substitutions s

            JOIN absences a
            ON s.absence_id = a.id

            WHERE
                a.date=%s

                AND

                s.substitute_teacher_id IS NULL

                AND (s.manual_substitute_name IS NULL OR TRIM(s.manual_substitute_name) = '')
            """,
            (date,)
        )

        unavailable_today = c.fetchone()[0]


        return {
            "total_teachers": total_teachers,
            "absences_today": absences_today,
            "substitutions_today": substitutions_today,
            "unavailable_today": unavailable_today
        }


    finally:

        c.close()
        conn.close()

def search_teachers(name):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT *

        FROM teachers

        WHERE name LIKE %s
        """,

        (
            "%" + name + "%",
        )
    )

    teachers = c.fetchall()

    conn.close()

    return teachers

def fetch_substitutions_by_date(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        a.date,
        a.day,
        s.period,
        s.class_name,
        t.name

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        LEFT JOIN teachers t

        ON s.substitute_teacher_id = t.id

        WHERE a.date=%s

        ORDER BY
        s.period
        """,

        (date,)
    )

    substitutions = c.fetchall()

    conn.close()

    return substitutions

def count_teachers():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)
        FROM teachers
        """
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def get_today_substitutions(date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        s.period,
        s.class_name,
        t.name

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        LEFT JOIN teachers t

        ON s.substitute_teacher_id = t.id

        WHERE a.date=%s

        ORDER BY s.period
        """,

        (date,)
    )

    substitutions = c.fetchall()

    conn.close()

    return substitutions

def get_my_absences(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        date,
        day

        FROM absences

        WHERE teacher_id=%s

        ORDER BY date DESC
        """,

        (teacher_id,)
    )

    absences = c.fetchall()

    conn.close()

    return absences

def get_my_substitutions(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        a.date,
        a.day,
        s.period,
        s.class_name

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        WHERE s.substitute_teacher_id = %s

        ORDER BY
        a.date DESC,
        s.period
        """,

        (teacher_id,)
    )

    substitutions = c.fetchall()

    conn.close()

    return substitutions

def get_teacher_full_timetable(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT

        day,
        period1,
        period2,
        period3,
        period4,
        period5,
        period6,
        period7,
        period8,
        period9

        FROM timetable

        WHERE teacher_id=%s
        """,

        (teacher_id,)
    )

    timetable = c.fetchall()

    conn.close()

    return timetable

def count_free_periods(
        teacher_id,
        day):

    timetable = get_teacher_timetable_for_day(
        teacher_id,
        day
    )

    count = 0

    for period in timetable:

        if period == "Free":

            count += 1

    return count


def has_three_consecutive_periods(
        teacher_id,
        day,
        period,
        date):

    # Get the timetable
    timetable = get_teacher_timetable_for_day(
        teacher_id,
        day
    )

    # Convert to working/free periods
    working = []

    for i in range(1, 10):

        if timetable[i - 1] == "Free":

            working.append(False)

        else:

            working.append(True)

    # Mark already assigned substitutions
    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT period

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        WHERE

        s.substitute_teacher_id = %s

        AND

        a.date = %s
        """,

        (
            teacher_id,
            date
        )
    )

    assigned_periods = c.fetchall()

    conn.close()

    for p in assigned_periods:

        working[p[0] - 1] = True

    # Simulate assigning this substitution
    working[period - 1] = True

    # Check for more than 3 consecutive periods
    count = 0

    for status in working:

        if status:

            count += 1

            if count > 3:

                return True

        else:

            count = 0

    return False

def count_substitutions_today(
        teacher_id,
        absence_date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT COUNT(*)

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        WHERE

        s.substitute_teacher_id = %s

        AND

        a.date = %s
        """,

        (
            teacher_id,
            absence_date
        )
    )

    count = c.fetchone()[0]

    conn.close()

    return count

def is_teacher_absent(
        teacher_id,
        absence_date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT id

        FROM absences

        WHERE
        teacher_id=%s
        AND
        date=%s
        """,

        (
            teacher_id,
            absence_date
        )
    )

    absence = c.fetchone()

    conn.close()

    return absence is not None

def get_teacher_timetable_for_day(
        teacher_id,
        day):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
        period1,
        period2,
        period3,
        period4,
        period5,
        period6,
        period7,
        period8,
        period9

        FROM timetable

        WHERE teacher_id=%s
        AND day=%s
        """,

        (
            teacher_id,
            day
        )
    )

    timetable = c.fetchone()

    conn.close()

    return timetable

def insert_substitutions_batch(substitutions):

    conn = connect_db()
    c = conn.cursor()

    try:

        query = """
            INSERT INTO substitutions(
                absence_id,
                substitute_teacher_id,
                period,
                class_name,
                manual_substitute_name
            )

            VALUES(%s, %s, %s, %s, %s)
        """

        values = []

        for item in substitutions:

            values.append(
                (
                    item["absence_id"],
                    item["teacher_id"],
                    item["period"],
                    item["class_name"],
                    item["manual_substitute_name"]
                )
            )

        c.executemany(
            query,
            values
        )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        c.close()
        conn.close()

def insert_substitution(
        absence_id,
        substitute_teacher_id,
        period,
        class_name,
        manual_substitute_name=None):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO substitutions(

        absence_id,

        substitute_teacher_id,

        period,

        class_name,

        manual_substitute_name

        )

        VALUES(%s,%s,%s,%s,%s)
        """,

        (
            absence_id,
            substitute_teacher_id,
            period,
            class_name,
            manual_substitute_name
        )
    )

    conn.commit()
    conn.close()

def is_teacher_already_assigned(
        teacher_id,
        absence_date,
        period):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT s.id

        FROM substitutions s

        JOIN absences a

        ON s.absence_id = a.id

        WHERE
        s.substitute_teacher_id = %s
        AND
        a.date = %s
        AND
        s.period = %s
        """,

        (
            teacher_id,
            absence_date,
            period
        )
    )

    assigned = c.fetchone()

    conn.close()

    return assigned is not None

def is_teacher_free(
        teacher_id,
        day,
        period):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        f"""
        SELECT period{period}
        FROM timetable

        WHERE teacher_id=%s
        AND day=%s
        """,

        (
            teacher_id,
            day
        )
    )

    value = c.fetchone()

    conn.close()

    return (
        value is not None
        and
        value[0] == "Free"
    )

def absence_exists(
        teacher_id,
        date):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT id

        FROM absences

        WHERE teacher_id=%s
        AND date=%s
        """,

        (
            teacher_id,
            date
        )
    )

    absence = c.fetchone()

    conn.close()

    return absence is not None

def search_today_substitutions_with_absent_teacher(
        teacher_name="",
        date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
    SELECT

        a.date,

        a.day,

        absent_teacher.name AS absent_teacher_name,

        s.period,

        s.class_name,

        CASE

            WHEN s.manual_substitute_name IS NOT NULL
            THEN s.manual_substitute_name

            WHEN substitute_teacher.name IS NOT NULL
            THEN substitute_teacher.name

            ELSE 'Substitute Not Available'

        END AS substitute_name

    FROM substitutions s

    JOIN absences a
    ON s.absence_id = a.id

    JOIN teachers absent_teacher
    ON a.teacher_id = absent_teacher.id

    LEFT JOIN teachers AS substitute_teacher
    ON s.substitute_teacher_id = substitute_teacher.id

    WHERE 1=1
    """

    values = []

    if teacher_name:

        query += """
        AND LOWER(

            COALESCE(
                s.manual_substitute_name,
                substitute_teacher.name,
                ''
            )

        ) LIKE %s
        """

        values.append(
            "%" + teacher_name.lower() + "%"
        )

    if date:

        query += """
        AND a.date = %s
        """

        values.append(date)

    query += """
    ORDER BY

        a.date DESC,

        s.period ASC,

        absent_teacher.name ASC
    """

    c.execute(
        query,
        tuple(values)
    )

    substitutions = c.fetchall()

    c.close()
    conn.close()

    return substitutions

def get_teacher_id(name):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT id
        FROM teachers
        WHERE name=%s
        """,

        (name,)
    )

    teacher = c.fetchone()

    c.close()
    conn.close()

    if teacher is None:

        return None

    return teacher[0]

def delete_absence(absence_id):

    conn = connect_db()
    c = conn.cursor()

    # Delete substitutions generated from this absence
    c.execute(
        """
        DELETE FROM substitutions
        WHERE absence_id=%s
        """,

        (absence_id,)
    )

    # Delete the absence itself
    c.execute(
        """
        DELETE FROM absences
        WHERE id=%s
        """,

        (absence_id,)
    )

    conn.commit()
    conn.close()

def search_upcoming_absences(name="", date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
        SELECT
            a.id,
            t.name,
            a.date,
            a.day

        FROM absences a

        JOIN teachers t
        ON a.teacher_id = t.id

        WHERE a.date > CURDATE()
    """

    values = []

    if name:

        query += """
            AND LOWER(t.name) LIKE %s
        """

        values.append(
            "%" + name.lower() + "%"
        )

    if date:

        query += """
            AND a.date = %s
        """

        values.append(date)

    query += """
        ORDER BY
            a.date ASC,
            t.name ASC
    """

    c.execute(
        query,
        tuple(values)
    )

    absences = c.fetchall()

    c.close()
    conn.close()

    return absences

def fetch_upcoming_absences():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
            a.id,
            t.name,
            a.date,
            a.day

        FROM absences a

        JOIN teachers t
        ON a.teacher_id = t.id

        WHERE a.date > CURDATE()

        ORDER BY
            a.date ASC,
            t.name ASC
        """
    )

    absences = c.fetchall()

    c.close()
    conn.close()

    return absences

def search_previous_absences(
        name="",
        date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
        SELECT
            a.id,
            t.name,
            a.date,
            a.day

        FROM absences a

        JOIN teachers t
        ON a.teacher_id = t.id

        WHERE a.date < CURDATE()
    """

    values = []

    if name:

        query += """
            AND LOWER(t.name) LIKE %s
        """

        values.append(
            "%" + name.lower() + "%"
        )

    if date:

        query += """
            AND a.date = %s
        """

        values.append(date)

    query += """
        ORDER BY a.date DESC
    """

    c.execute(
        query,
        tuple(values)
    )

    absences = c.fetchall()

    c.close()
    conn.close()

    return absences

def fetch_absences():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
        a.id,
        t.name,
        a.date,
        a.day

        FROM absences a

        JOIN teachers t

        ON a.teacher_id=t.id

        WHERE a.date < CURDATE()

        ORDER BY a.date DESC
        """
    )

    absences = c.fetchall()

    conn.close()

    return absences


def update_timetable(
        teacher_id,
        timetable):

    conn = connect_db()
    c = conn.cursor()

    for row in timetable:

        day = row[0]
        periods = row[1:]

        c.execute(
            """
            UPDATE timetable
            SET
            period1=%s,
            period2=%s,
            period3=%s,
            period4=%s,
            period5=%s,
            period6=%s,
            period7=%s,
            period8=%s,
            period9=%s
            WHERE teacher_id=%s
            AND day=%s
            """,

            (
                periods[0],
                periods[1],
                periods[2],
                periods[3],
                periods[4],
                periods[5],
                periods[6],
                periods[7],
                periods[8],
                teacher_id,
                day
            )
        )

    conn.commit()
    conn.close()

def update_teacher(teacher_id, name, subject, contact):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        UPDATE teachers
        SET name=%s,
            subject=%s,
            contact=%s
        WHERE id=%s
        """,

        (name, subject, contact, teacher_id)
    )

    conn.commit()
    conn.close()

def get_teacher(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT id,name,subject,contact
        FROM teachers
        WHERE id=%s
        """,

        (teacher_id,)
    )

    teacher = c.fetchone()

    conn.close()

    return teacher

def update_timetable_day(
        teacher_id,
        day,
        periods):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        UPDATE timetable
        SET
        period1=%s,
        period2=%s,
        period3=%s,
        period4=%s,
        period5=%s,
        period6=%s,
        period7=%s,
        period8=%s,
        period9=%s
        WHERE teacher_id=%s
        AND day=%s
        """,

        (
            periods[0],
            periods[1],
            periods[2],
            periods[3],
            periods[4],
            periods[5],
            periods[6],
            periods[7],
            periods[8],
            teacher_id,
            day
        )
    )

    conn.commit()
    conn.close()

def get_full_timetable(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
        day,
        period1,
        period2,
        period3,
        period4,
        period5,
        period6,
        period7,
        period8,
        period9

        FROM timetable

        WHERE teacher_id=%s

        ORDER BY FIELD(
        day,
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday')
        """,

        (teacher_id,)
    )

    timetable = c.fetchall()

    conn.close()

    return timetable

def get_teacher_timetable(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        SELECT
        day,
        period1,
        period2,
        period3,
        period4,
        period5,
        period6,
        period7,
        period8,
        period9
        FROM timetable
        WHERE teacher_id=%s
    """,(teacher_id,))

    timetable = c.fetchall()

    conn.close()

    return timetable

def delete_teacher(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    # Delete dependent records first
    c.execute(
        "DELETE FROM timetable WHERE teacher_id=%s",
        (teacher_id,)
    )

    c.execute(
        "DELETE FROM absences WHERE teacher_id=%s",
        (teacher_id,)
    )

    c.execute(
        "DELETE FROM substitutions WHERE substitute_teacher_id=%s",
        (teacher_id,)
    )

    # Finally delete teacher
    c.execute(
        "DELETE FROM teachers WHERE id=%s",
        (teacher_id,)
    )

    conn.commit()
    conn.close()

def fetch_all_teachers():
    conn = connect_db()
    c = conn.cursor()

    c.execute("""
        SELECT id, name, subject, contact
        FROM teachers
    """)

    rows = c.fetchall()

    conn.close()

    return rows

def get_teacher_names():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT name
        FROM teachers
        ORDER BY name
        """
    )

    teachers = c.fetchall()

    conn.close()

    return teachers

def get_all_teacher_ids():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT id
        FROM teachers
        """
    )

    teachers = c.fetchall()

    conn.close()

    return [
        teacher[0]
        for teacher in teachers
    ]

def search_substitutions(
        teacher_name="",
        date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
    SELECT

    a.date,

    a.day,

    s.period,

    s.class_name,

    CASE

        WHEN s.manual_substitute_name IS NOT NULL
        THEN s.manual_substitute_name

        WHEN t.name IS NOT NULL
        THEN t.name

        ELSE 'Substitute Not Available'

    END AS substitute_name

    FROM substitutions s

    JOIN absences a

    ON s.absence_id = a.id

    LEFT JOIN teachers t

    ON s.substitute_teacher_id = t.id

    WHERE 1=1
    """

    values = []

    if teacher_name:

        query += """
        AND LOWER(

            COALESCE(
                s.manual_substitute_name,
                t.name,
                ''
            )

        ) LIKE %s
        """

        values.append(
            "%" + teacher_name.lower() + "%"
        )

    if date:

        query += """
        AND a.date=%s
        """

        values.append(
            date
        )

    query += """
    ORDER BY

    a.date DESC,

    s.period
    """

    c.execute(
        query,
        tuple(values)
    )

    substitutions = c.fetchall()

    conn.close()

    return substitutions

def record_absence(
        teacher_id,
        date,
        day):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO absences(
        teacher_id,
        date,
        day)

        VALUES(%s,%s,%s)
        """,

        (
            teacher_id,
            date,
            day
        )
    )

    absence_id = c.lastrowid

    conn.commit()

    conn.close()

    return absence_id

def get_teacher_name(teacher_id):

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT name

        FROM teachers

        WHERE id=%s
        """,

        (teacher_id,)
    )

    result = c.fetchone()

    conn.close()

    if result:

        return result[0]

    return None

def search_upcoming_substitutions(
        teacher_name="",
        date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
        SELECT
            a.date,
            a.day,
            s.period,
            s.class_name,

            CASE

                WHEN s.manual_substitute_name IS NOT NULL
                THEN s.manual_substitute_name

                WHEN t.name IS NOT NULL
                THEN t.name

                ELSE 'Substitute Not Available'

            END AS substitute_name

        FROM substitutions s

        JOIN absences a
        ON s.absence_id = a.id

        LEFT JOIN teachers t
        ON s.substitute_teacher_id = t.id

        WHERE a.date > CURDATE()
    """

    values = []

    if teacher_name:

        query += """
            AND LOWER(
                COALESCE(
                    s.manual_substitute_name,
                    t.name,
                    ''
                )
            ) LIKE %s
        """

        values.append(
            "%" + teacher_name.lower() + "%"
        )

    if date:

        query += """
            AND a.date = %s
        """

        values.append(date)

    query += """
        ORDER BY
            a.date ASC,
            s.period
    """

    c.execute(
        query,
        tuple(values)
    )

    substitutions = c.fetchall()

    c.close()
    conn.close()

    return substitutions

def fetch_upcoming_substitutions():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
            a.date,
            a.day,
            s.period,
            s.class_name,

            CASE

                WHEN s.manual_substitute_name IS NOT NULL
                THEN s.manual_substitute_name

                WHEN t.name IS NOT NULL
                THEN t.name

                ELSE 'Substitute Not Available'

            END AS substitute_name

        FROM substitutions s

        JOIN absences a
        ON s.absence_id = a.id

        LEFT JOIN teachers t
        ON s.substitute_teacher_id = t.id

        WHERE a.date > CURDATE()

        ORDER BY
            a.date ASC,
            s.period
        """
    )

    substitutions = c.fetchall()

    c.close()
    conn.close()

    return substitutions

def search_previous_substitutions(
        teacher_name="",
        date=""):

    conn = connect_db()
    c = conn.cursor()

    query = """
        SELECT
            a.date,
            a.day,
            s.period,
            s.class_name,

            CASE

                WHEN s.manual_substitute_name IS NOT NULL
                THEN s.manual_substitute_name

                WHEN t.name IS NOT NULL
                THEN t.name

                ELSE 'Substitute Not Available'

            END AS substitute_name

        FROM substitutions s

        JOIN absences a
        ON s.absence_id = a.id

        LEFT JOIN teachers t
        ON s.substitute_teacher_id = t.id

        WHERE a.date < CURDATE()
    """

    values = []

    if teacher_name:

        query += """
            AND LOWER(
                COALESCE(
                    s.manual_substitute_name,
                    t.name,
                    ''
                )
            ) LIKE %s
        """

        values.append(
            "%" + teacher_name.lower() + "%"
        )

    if date:

        query += """
            AND a.date = %s
        """

        values.append(date)

    query += """
        ORDER BY
            a.date DESC,
            s.period
    """

    c.execute(
        query,
        tuple(values)
    )

    substitutions = c.fetchall()

    c.close()
    conn.close()

    return substitutions

def fetch_substitutions():

    conn = connect_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
            a.date,
            a.day,
            s.period,
            s.class_name,

            CASE

                WHEN s.manual_substitute_name IS NOT NULL
                THEN s.manual_substitute_name

                WHEN t.name IS NOT NULL
                THEN t.name

                ELSE 'Substitute Not Available'

            END AS substitute_name

        FROM substitutions s

        JOIN absences a
        ON s.absence_id = a.id

        LEFT JOIN teachers t
        ON s.substitute_teacher_id = t.id

        WHERE a.date < CURDATE()

        ORDER BY
            a.date DESC,
            s.period
        """
    )

    substitutions = c.fetchall()

    c.close()
    conn.close()

    return substitutions

def add_teacher(
        name,
        subject,
        contact,
        timetable,
        classes):

    conn = connect_db()
    c = conn.cursor()

    try:

        # Check for existing teacher
        c.execute(
            """
            SELECT id
            FROM teachers
            WHERE LOWER(name) = LOWER(%s)
            """,
            (name,)
        )

        if c.fetchone():
            raise ValueError(
                f"Teacher '{name}' already exists in the system."
            )

        # Insert teacher
        c.execute(
            """
            INSERT INTO teachers(
                name,
                subject,
                contact
            )
            VALUES(%s, %s, %s)
            """,
            (
                name,
                subject,
                contact
            )
        )

        teacher_id = c.lastrowid

        # Create username
        username = name.lower().strip()

        prefixes = [
            "mr. ", "mr ",
            "mrs. ", "mrs ",
            "ms. ", "ms ",
            "miss ",
            "dr. ", "dr "
        ]

        for prefix in prefixes:

            if username.startswith(prefix):

                username = username[len(prefix):]

                break

        username = username.strip()

        # Check for existing username
        c.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(username) = LOWER(%s)
            """,
            (username,)
        )

        if c.fetchone():
            raise ValueError(
                f"Teacher '{name}' already exists in the system."
            )

        password = "teacher123"
        role = "teacher"

        # Create user account
        c.execute(
            """
            INSERT INTO users(
                username,
                password,
                role,
                teacher_id
            )
            VALUES(%s, %s, %s, %s)
            """,
            (
                username,
                password,
                role,
                teacher_id
            )
        )

        # Insert timetable
        for row in timetable:

            day = row[0]
            periods = row[1:]

            c.execute(
                """
                INSERT INTO timetable(
                    teacher_id,
                    day,
                    period1,
                    period2,
                    period3,
                    period4,
                    period5,
                    period6,
                    period7,
                    period8,
                    period9
                )
                VALUES(
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    teacher_id,
                    day,
                    periods[0],
                    periods[1],
                    periods[2],
                    periods[3],
                    periods[4],
                    periods[5],
                    periods[6],
                    periods[7],
                    periods[8]
                )
            )

        # Insert teacher classes
        for class_name in classes:

            c.execute(
                """
                INSERT INTO teacher_classes(
                    teacher_id,
                    class_name
                )
                VALUES(%s, %s)
                """,
                (
                    teacher_id,
                    class_name
                )
            )

        conn.commit()

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        conn.close()

def get_manual_free_teachers(
        cache,
        period,
        absent_teacher_id,
        day):

    free_teachers = []

    teacher_ids = cache["teacher_ids"]

    for teacher_id in teacher_ids:

        # Don't show the teacher
        # who is absent
        if teacher_id == absent_teacher_id:
            continue

        # Don't show teachers
        # absent on this date
        if teacher_id in cache["absent_teachers"]:
            continue

        # Get teacher name
        teacher_name = cache[
            "teacher_names"
        ].get(
            teacher_id,
            "Unknown Teacher"
        )

        # Special availability rule:
        # Mr. Gowtham is unavailable
        # for substitutions on Tuesday
        if is_teacher_unavailable_on_day(
                teacher_name,
                day):

            continue

        # Get teacher timetable
        teacher_timetable = cache[
            "timetables"
        ].get(teacher_id)

        # Safety check
        if teacher_timetable is None:
            continue

        # Teacher must be free
        # during this period
        if teacher_timetable[
                period - 1
        ] != "Free":

            continue

        # Teacher must not already
        # have a substitution
        # during this period
        if period in cache[
                "assigned_periods"
        ].get(
                teacher_id,
                set()
        ):

            continue

        free_teachers.append(
            (
                teacher_id,
                teacher_name
            )
        )

    # Alphabetical order
    free_teachers.sort(
        key=lambda teacher:
        teacher[1].lower()
    )

    return free_teachers

def get_grade_from_class(class_name):

    if not class_name:
        return None

    class_name = class_name.strip()

    # Examples:
    # X       -> X
    # X-A     -> X
    # X-A+B   -> X
    # XII-C+D -> XII

    if "-" in class_name:

        return class_name.split(
            "-",
            1
        )[0].strip()

    return class_name

def get_all_sections_for_grade(
        grade,
        teacher_classes):

    sections = set()

    grade_prefix = grade + "-"

    # teacher_classes structure:
    #
    # {
    #     teacher_id: {"X-A", "X-B"},
    #     teacher_id: {"XI-C"}
    # }

    for classes in teacher_classes.values():

        for class_name in classes:

            if class_name.startswith(
                    grade_prefix):

                # Only collect actual
                # individual sections.
                #
                # X-A   -> Yes
                # X-A+B -> No

                section_part = class_name.split(
                    "-",
                    1
                )[1]

                if "+" not in section_part:

                    sections.add(
                        class_name
                    )

    return sorted(sections)

def get_substitution_classes(
        class_name,
        is_language_teacher,
        teacher_classes):

    grade = get_grade_from_class(
        class_name
    )


    # LANGUAGE TEACHER
    #
    # X
    # X-A+B
    #
    # Both remain ONE substitution

    if is_language_teacher:

        return [
            {
                "class_name": class_name,
                "grade": grade,
                "language_substitution": True
            }
        ]


    # NON-LANGUAGE TEACHER


    # Case 1:
    #
    # X-A+B
    #
    # Becomes:
    #
    # X-A
    # X-B

    if "-" in class_name:

        grade_part, section_part = (
            class_name.split(
                "-",
                1
            )
        )

        sections = section_part.split("+")

        substitution_classes = []

        for section in sections:

            substitution_classes.append(
                {
                    "class_name":
                        grade_part
                        + "-"
                        + section.strip(),

                    "grade":
                        grade,

                    "language_substitution":
                        False
                }
            )

        return substitution_classes


    # Case 2:
    #
    # Plain X
    #
    # Find every section:
    #
    # X-A
    # X-B
    # X-C
    # X-D

    all_sections = get_all_sections_for_grade(
        grade,
        teacher_classes
    )

    substitution_classes = []

    for section in all_sections:

        substitution_classes.append(
            {
                "class_name": section,
                "grade": grade,
                "language_substitution": False
            }
        )

    return substitution_classes

def is_teacher_eligible_for_class(
        teacher_id,
        substitution_class,
        teacher_classes):

    capable_classes = teacher_classes.get(
        teacher_id,
        set()
    )


    # NORMAL SUBSTITUTION
    #
    # Exact section matching

    if not substitution_class[
            "language_substitution"
    ]:

        return (
            substitution_class["class_name"]
            in
            capable_classes
        )


    # LANGUAGE SUBSTITUTION
    #
    # Candidate can teach ANY section
    # belonging to the same grade

    required_grade = substitution_class[
        "grade"
    ]


    for capable_class in capable_classes:

        capable_grade = get_grade_from_class(
            capable_class
        )

        if capable_grade == required_grade:

            return True


    return False

def generate_substitution_candidates(absence_ids):

    total_start = time.perf_counter()

    suggestions = []

    # Process each absence
    for absence_id in absence_ids:

        absence_start = time.perf_counter()

        conn = connect_db()
        c = conn.cursor()

        # Get absence details
        c.execute(
            """
            SELECT
                teacher_id,
                date,
                day

            FROM absences

            WHERE id=%s
            """,

            (absence_id,)
        )

        absence = c.fetchone()

        c.close()
        conn.close()

        print(
            f"\nAbsence details query: "
            f"{time.perf_counter() - absence_start:.4f} seconds"
        )

        # Safety check
        if absence is None:
            continue

        absent_teacher_id, absence_date, day = absence

        cache_start = time.perf_counter()

        # Load all required data once
        cache = load_substitution_cache(
            absence_date,
            day
        )

        print(
            f"Cache loading: "
            f"{time.perf_counter() - cache_start:.4f} seconds"
        )

        # Get absent teacher timetable
        timetable = cache["timetables"].get(
            absent_teacher_id
        )

        # Safety check
        if timetable is None:
            continue

        teacher_ids = cache["teacher_ids"]


        # ---------------------------------
        # GET ABSENT TEACHER SUBJECT
        # ---------------------------------

        absent_teacher_subject = cache[
            "teacher_subjects"
        ].get(
            absent_teacher_id,
            ""
        )


        # Check whether absent teacher
        # is a Language teacher

        is_language_teacher = (

            absent_teacher_subject
            .strip()
            .casefold()

            ==

            "language"
        )


        # Process all 9 periods
        for period in range(1, 10):

            original_class_name = timetable[
                period - 1
            ]

            # Skip free periods
            if original_class_name == "Free":
                continue


            # ---------------------------------
            # GET SUBSTITUTION REQUIREMENTS
            # ---------------------------------

            substitution_classes = (
                get_substitution_classes(

                    original_class_name,

                    is_language_teacher,

                    cache["teacher_classes"]
                )
            )


            # Safety check
            if not substitution_classes:
                continue


            # ---------------------------------
            # PROCESS EACH REQUIREMENT
            # ---------------------------------

            for substitution_class in substitution_classes:

                class_name = substitution_class[
                    "class_name"
                ]

                candidates = []


                # Check every teacher
                for teacher_id in teacher_ids:

                    # Skip the absent teacher
                    if teacher_id == absent_teacher_id:
                        continue


                    # Skip teachers absent
                    # on this date
                    if teacher_id in cache[
                            "absent_teachers"
                    ]:
                        continue

                    # Get teacher name
                    teacher_name = cache[
                        "teacher_names"
                        ].get(
                        teacher_id,
                        "Unknown Teacher")

                    # Special availability rule
                    if is_teacher_unavailable_on_day(
                        teacher_name,
                        day):

                        continue


                    # ---------------------------------
                    # CHECK CLASS ELIGIBILITY
                    # ---------------------------------

                    if not is_teacher_eligible_for_class(

                            teacher_id,

                            substitution_class,

                            cache["teacher_classes"]
                    ):

                        continue


                    # Get teacher timetable
                    teacher_timetable = cache[
                        "timetables"
                    ].get(
                        teacher_id
                    )


                    # Safety check
                    if teacher_timetable is None:
                        continue


                    # Teacher must be free
                    if teacher_timetable[
                            period - 1
                    ] != "Free":

                        continue


                    # Teacher must not already
                    # have substitution this period
                    if period in cache[
                            "assigned_periods"
                    ].get(
                            teacher_id,
                            set()
                    ):

                        continue


                    # Number of substitutions
                    # already assigned today
                    substitutions_today = cache[
                        "substitution_count"
                    ].get(
                        teacher_id,
                        0
                    )


                    # Warning if daily limit reached
                    daily_limit_warning = (

                        substitutions_today

                        >=

                        MAX_SUBSTITUTIONS_PER_DAY
                    )


                    # Number of free periods
                    free_periods = cache[
                        "free_periods"
                    ].get(
                        teacher_id,
                        0
                    )


                    # Check continuous-period warning
                    continuous_warning = (

                        has_three_consecutive_periods_cached(

                            cache,

                            teacher_id,

                            period
                        )
                    )


                    # Same scoring logic
                    score = (

                        free_periods

                        -

                        substitutions_today
                    )

                    candidates.append(
                        (
                            teacher_id,

                            teacher_name,

                            score,

                            continuous_warning,

                            daily_limit_warning
                        )
                    )


                # Preserve your EXACT
                # current sorting
                candidates.sort(
                    key=lambda x: (
                        x[3],
                        x[4],
                        -x[2]
                    )
                )


                # ---------------------------------
                # GET MANUAL FREE TEACHERS
                # ---------------------------------

                free_teachers = (
                    get_manual_free_teachers(

                        cache,

                        period,

                        absent_teacher_id,

                        day
                    )
                )


                # ---------------------------------
                # ADD SUGGESTION
                # ---------------------------------

                suggestions.append(
                    {
                        "absence_id":
                            absence_id,

                        "period":
                            period,

                        "class_name":
                            class_name,

                        "absent_teacher":
                            cache[
                                "teacher_names"
                            ].get(
                                absent_teacher_id,
                                "Unknown Teacher"
                            ),

                        "teachers":
                            candidates,

                        "free_teachers":
                            free_teachers
                    }
                )


        print(
            f"\nTotal processing time: "
            f"{time.perf_counter() - total_start:.4f} seconds"
        )


    # Preserve your existing final sorting
    suggestions.sort(
        key=lambda x: x["period"]
    )

    return suggestions