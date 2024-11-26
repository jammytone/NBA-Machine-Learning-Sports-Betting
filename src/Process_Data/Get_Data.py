import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import toml

sys.path.insert(1, os.path.join(sys.path[0], '../..'))
from src.Utils.tools import get_json_data, to_data_frame

config = toml.load("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/config.toml")

url = config['data_url']

# config에서 24-25 시즌만 선택
season_key = "2024-25"
season_config = {
    season_key: {
        'start_date': config['get-data'][season_key]['start_date'],
        'end_date': datetime.now().strftime('%Y-%m-%d'),  # 현재 날짜까지만
        'start_year': config['get-data'][season_key]['start_year']
    }
}

# 기존 데이터베이스에 연결
con = sqlite3.connect("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Data/TeamData.sqlite")

# 데이터 가져오기
for key, value in season_config.items():
    date_pointer = datetime.strptime(value['start_date'], "%Y-%m-%d").date()
    end_date = datetime.strptime(value['end_date'], "%Y-%m-%d").date()

    while date_pointer <= end_date:
        print("Getting data: ", date_pointer)

        raw_data = get_json_data(
            url.format(date_pointer.month, date_pointer.day, value['start_year'], date_pointer.year, key))
        df = to_data_frame(raw_data)

        date_pointer = date_pointer + timedelta(days=1)

        df['Date'] = str(date_pointer)

        df.to_sql(date_pointer.strftime("%Y-%m-%d"), con, if_exists="replace")

        time.sleep(random.randint(1, 3))

        # TODO: Add tests

con.close()
