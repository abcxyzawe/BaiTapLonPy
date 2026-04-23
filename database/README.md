# Database EAUT - PostgreSQL

## Khoi dong database

```bash
# tu thu muc goc project
docker compose up -d
```

Lan dau chay se:
1. Tai image `postgres:16-alpine`
2. Chay `schema.sql` tao bang
3. Chay `seed.sql` insert mock data
4. Mo pgAdmin tai http://localhost:5050

## Connect Postgres

| Truong | Gia tri |
|--------|---------|
| Host | localhost |
| Port | 5432 |
| Database | eaut_db |
| Username | eaut_admin |
| Password | eaut_password |

## Connect pgAdmin

Mo http://localhost:5050
- Email: admin@eaut.edu.vn
- Password: admin123

Them server moi:
- Name: EAUT
- Host: postgres (ten container, khong phai localhost)
- Port: 5432
- Username: eaut_admin
- Password: eaut_password

## Dung va khoi dong lai

```bash
docker compose down           # dung, giu data
docker compose down -v        # dung va XOA data (chay lai se seed moi)
docker compose up -d          # khoi dong lai
```

## Xem log

```bash
docker compose logs -f postgres
```

## Connect tu Python

```python
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    database='eaut_db',
    user='eaut_admin', password='eaut_password'
)
cur = conn.cursor()
cur.execute("SELECT * FROM v_class_detail")
for row in cur.fetchall():
    print(row)
```
