from database.db_manager import DatabaseManager


def main():
    db = DatabaseManager()

    print("===== CLEAR DATABASE =====")
    db.clear_all()

    print("\n===== TEST XE VÀO =====")
    success = db.insert_vehicle("59P166480", "motorbike")
    print("Insert:", success)

    print("\n===== TEST XE VÀO TRÙNG =====")
    success = db.insert_vehicle("59P166480", "motorbike")
    print("Insert again:", success)

    print("\n===== XE ĐANG TRONG BÃI =====")
    inside = db.is_vehicle_inside("59P166480")
    print("Is inside:", inside)

    print("\n===== LẤY XE ĐANG TRONG BÃI =====")
    vehicle = db.get_vehicle_in("59P166480")
    print(vehicle)

    print("\n===== XE RA =====")
    success = db.update_vehicle_out("59P166480")
    print("Update out:", success)

    print("\n===== XE RA LẠI =====")
    success = db.update_vehicle_out("59P166480")
    print("Update out again:", success)

    print("\n===== THÊM NHIỀU XE =====")
    db.insert_vehicle("30E43502", "car")
    db.insert_vehicle("51A99999", "car")

    print("\n===== DANH SÁCH XE TRONG BÃI =====")
    vehicles_inside = db.get_all_vehicle_inside()
    for v in vehicles_inside:
        print(v)

    print("\n===== SEARCH THEO BIỂN =====")
    results = db.search(plate="30E")
    for r in results:
        print(r)

    print("\n===== SEARCH XE CHƯA RA =====")
    results = db.search(only_inside=True)
    for r in results:
        print(r)

    print("\n===== LỊCH SỬ =====")
    history = db.get_history()
    for h in history:
        print(h)

    print("\n===== THỐNG KÊ =====")
    print("Xe trong bãi:", db.count_vehicle_inside())
    print("Tổng xe:", db.count_all())

    db.close()


if __name__ == "__main__":
    main()