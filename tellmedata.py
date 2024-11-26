import sqlite3

conn = sqlite3.connect('/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Data/OddsData.sqlite')
cursor = conn.cursor()

# 테이블 구조 확인
cursor.execute('PRAGMA table_info("odds_2024-25_new");')
columns = cursor.fetchall()
print("\n테이블 구조:")
for col in columns:
    print(col)

# 샘플 데이터 확인
cursor.execute('SELECT * FROM "odds_2024-25_new" LIMIT 1;')
sample = cursor.fetchone()
print("\n샘플 데이터:")
print(sample)

conn.close()
