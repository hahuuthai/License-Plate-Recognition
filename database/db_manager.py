import os
import sys
import sqlite3
from datetime import datetime, timedelta

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)  # exe folder
    return os.path.dirname(os.path.abspath(__file__))  # python file folder

class DatabaseManager:
    def __init__(self, db_path=None):
        BASE_DIR = get_base_dir()

        # Tạo thư mục data nằm cùng exe
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        print("BASE DIR:", BASE_DIR)
        print("DATA DIR:", data_dir)

        # Đường dẫn DB chuẩn
        if db_path is None:
            db_path = os.path.join(data_dir, "parking.db")

        print("DB PATH:", db_path)  # debug 

        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    # =========================
    # CREATE TABLE
    # =========================
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS parking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT NOT NULL,
            vehicle_type TEXT,
            time_in TEXT,
            time_out TEXT,
            image_path TEXT,
            plate_image_path TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    # =========================
    # XE VÀO
    # =========================
    def insert_vehicle(self, plate, vehicle_type,
                       image_path=None, plate_image_path=None):

        if self.is_vehicle_inside(plate):
            return False  # đã tồn tại
        
        # Nếu xe đã từng vào và ĐÃ RA (có time_out), 
        # xóa các bản ghi cũ của biển số này để tránh trùng lặp/rác dữ liệu
        query_delete_old = "DELETE FROM parking WHERE plate = ? AND time_out IS NOT NULL"
        self.conn.execute(query_delete_old, (plate,))

        now = datetime.now().isoformat()

        query_insert = """
        INSERT INTO parking (
            plate, vehicle_type, time_in, time_out,
            image_path, plate_image_path
        )
        VALUES (?, ?, ?, NULL, ?, ?)
        """

        try:
            self.conn.execute(query_insert, (
                plate, vehicle_type, now,
                image_path, plate_image_path
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Lỗi khi insert: {e}")
            self.conn.rollback()
            return False

    # =========================
    # XE RA
    # =========================
    def update_vehicle_out(self, plate):
        if not self.is_vehicle_inside(plate):
            return False

        now = datetime.now().isoformat()

        query = """
        UPDATE parking
        SET time_out = ?
        WHERE plate = ? AND time_out IS NULL
        """

        self.conn.execute(query, (now, plate))
        self.conn.commit()
        return True

    # =========================
    # KIỂM TRA XE TRONG BÃI
    # =========================
    def is_vehicle_inside(self, plate):
        query = """
        SELECT 1 FROM parking
        WHERE plate = ? AND time_out IS NULL
        LIMIT 1
        """
        cursor = self.conn.execute(query, (plate,))
        return cursor.fetchone() is not None

    # =========================
    # LẤY XE ĐANG TRONG BÃI
    # =========================
    def get_vehicle_in(self, plate):
        query = """
        SELECT * FROM parking
        WHERE plate = ? AND time_out IS NULL
        LIMIT 1
        """
        cursor = self.conn.execute(query, (plate,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # =========================
    # LẤY TOÀN BỘ XE TRONG BÃI
    # =========================
    def get_all_vehicle_inside(self):
        query = """
        SELECT * FROM parking
        WHERE time_out IS NULL
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    # =========================
    # SEARCH NÂNG CAO
    # =========================
    def search(self, plate=None, date_from=None,
               date_to=None, only_inside=False):

        query = "SELECT * FROM parking WHERE 1=1"
        params = []

        if plate:
            query += " AND plate LIKE ?"
            params.append(f"%{plate}%")

        if date_from:
            query += " AND time_in >= ?"
            params.append(date_from)

        if date_to:
            query += " AND time_in <= ?"
            params.append(date_to)

        if only_inside:
            query += " AND time_out IS NULL"

        query += " ORDER BY time_in DESC"

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # =========================
    # LỊCH SỬ
    # =========================
    def get_history(self, plate=None):
        if plate:
            query = """
            SELECT * FROM parking
            WHERE plate = ?
            ORDER BY time_in DESC
            """
            cursor = self.conn.execute(query, (plate,))
        else:
            query = """
            SELECT * FROM parking
            ORDER BY time_in DESC
            """
            cursor = self.conn.execute(query)

        return [dict(row) for row in cursor.fetchall()]

    # =========================
    # DELETE
    # =========================
    def delete_by_id(self, record_id):
        query = "DELETE FROM parking WHERE id = ?"
        self.conn.execute(query, (record_id,))
        self.conn.commit()

    # =========================
    # CLEAR ALL (DEV)
    # =========================
    def clear_all(self):
        self.conn.execute("DELETE FROM parking")
        self.conn.commit()

    # =========================
    # THỐNG KÊ
    # =========================
    def count_vehicle_inside(self):
        query = """
        SELECT COUNT(*) as total
        FROM parking
        WHERE time_out IS NULL
        """
        cursor = self.conn.execute(query)
        return cursor.fetchone()["total"]

    def count_all(self):
        query = "SELECT COUNT(*) as total FROM parking"
        cursor = self.conn.execute(query)
        return cursor.fetchone()["total"]
    
    def get_all(self):
        query = """
        SELECT * FROM parking
        ORDER BY time_in DESC
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    # =========================
    # AUTO CLEAN OLD RECORDS
    # =========================
    def clean_old_records(self, days=30):

        cutoff_date = (
            datetime.now() - timedelta(days=days)
        ).isoformat()

        query = """
        SELECT *
        FROM parking
        WHERE time_out IS NOT NULL
        AND time_out < ?
        """

        rows = self.conn.execute(
            query,
            (cutoff_date,)
        ).fetchall()

        deleted = 0

        for row in rows:

            image_path = row["image_path"]
            plate_image_path = row["plate_image_path"]

            # ===== XÓA ẢNH XE =====
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print("Delete image error:", e)

            # ===== XÓA ẢNH BIỂN SỐ =====
            if plate_image_path and os.path.exists(plate_image_path):
                try:
                    os.remove(plate_image_path)
                except Exception as e:
                    print("Delete plate image error:", e)

            # ===== XÓA DB =====
            self.conn.execute(
                "DELETE FROM parking WHERE id=?",
                (row["id"],)
            )

            deleted += 1

        self.conn.commit()

        print(
            f"🗑 Auto cleaned {deleted} records older than {days} days"
        )

        return deleted

    # =========================
    # CLOSE
    # =========================
    def close(self):
        self.conn.close()