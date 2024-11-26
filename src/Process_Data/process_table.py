import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect("../../Data/OddsData.sqlite")
cursor = conn.cursor()

# 현재 테이블 목록 확인
print("삭제 전 테이블 목록:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(tables)

# 24-25 시즌 관련 테이블 삭제
try:
    cursor.execute('DROP TABLE IF EXISTS "2024-25"')
    cursor.execute('DROP TABLE IF EXISTS "odds_2024-25_new"')
    conn.commit()
    print("\n테이블이 성공적으로 삭제되었습니다.")
except sqlite3.Error as e:
    print("\n오류 발생:", e)

# 삭제 후 테이블 목록 확인
print("\n삭제 후 테이블 목록:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(tables)

conn.close()
