#!/usr/bin/env python3

import sqlite3
import sys

tax_id = int(sys.argv[1])

conn = sqlite3.connect("events.db")

cursor = conn.cursor()

cursor.execute(f"SELECT * FROM taxonomy WHERE tax_id = {tax_id};")

# Fetch all matching rows
rows = cursor.fetchall()

# Check if any rows were found and print them
if rows:
    for row in rows:
        print(row)
else:
    print("No rows found")


# cursor.execute("""
# select
#  tax_id,
#  count(*) as event_count
# from
#  taxonomy
# where
#  event_name != 'delete'
# group by
#  tax_id
# order by
#  event_count desc
# limit 10
# """)
## Fetch all matching rows
# rows = cursor.fetchall()
#
# for row in rows:
#    print(row)
#
## Close the connection
# conn.close()
