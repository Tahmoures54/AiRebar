# db/models.py
import datetime
import hashlib
import json

from .database import db
import config


class ProjectModel:
    @staticmethod
    def create(name, client=None):
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty.")
        now = datetime.datetime.now().isoformat()
        return db.execute(
            "INSERT INTO projects (name, client, last_accessed) VALUES (?, ?, ?)",
            (name, client, now), commit=True
        )

    @staticmethod
    def get_last():
        return db.fetchone(
            "SELECT id, name, client FROM projects ORDER BY last_accessed DESC LIMIT 1"
        )

    @staticmethod
    def get_all():
        return db.fetchall("SELECT id, name FROM projects ORDER BY name")

    @staticmethod
    def get_by_id(pid):
        return db.fetchone("SELECT id, name, client FROM projects WHERE id = ?", (pid,))

    @staticmethod
    def update(pid, name, client):
        db.execute(
            "UPDATE projects SET name=?, client=? WHERE id=?",
            (name, client, pid), commit=True
        )

    @staticmethod
    def update_access(pid):
        now = datetime.datetime.now().isoformat()
        db.execute("UPDATE projects SET last_accessed = ? WHERE id = ?", (now, pid), commit=True)

    @staticmethod
    def delete(pid):
        db.execute("DELETE FROM projects WHERE id = ?", (pid,), commit=True)


class ListoferModel:
    @staticmethod
    def get_or_create(project_id, number, description=""):
        row = db.fetchone(
            "SELECT id FROM listofers WHERE project_id = ? AND number = ?",
            (project_id, number)
        )
        if row:
            if description:
                db.execute(
                    "UPDATE listofers SET description = ? WHERE id = ?",
                    (description, row[0]), commit=True
                )
            return row[0]
        return db.execute(
            "INSERT INTO listofers (project_id, number, description) VALUES (?, ?, ?)",
            (project_id, number, description), commit=True
        )

    @staticmethod
    def get_numbers(project_id):
        rows = db.fetchall(
            "SELECT DISTINCT number FROM listofers WHERE project_id = ? ORDER BY number",
            (project_id,)
        )
        return [r[0] for r in rows]

    @staticmethod
    def get_descriptions(project_id):
        rows = db.fetchall(
            "SELECT DISTINCT description FROM listofers "
            "WHERE project_id = ? AND description IS NOT NULL AND description != '' "
            "ORDER BY description",
            (project_id,)
        )
        return [r[0] for r in rows]

    @staticmethod
    def get_number_by_id(listofer_id):
        row = db.fetchone("SELECT number FROM listofers WHERE id = ?", (listofer_id,))
        return row[0] if row else ""

    @staticmethod
    def get_description(listofer_id):
        row = db.fetchone("SELECT description FROM listofers WHERE id = ?", (listofer_id,))
        return row[0] if row else ""

    @staticmethod
    def get_description_by_number(project_id, number):
        row = db.fetchone(
            "SELECT description FROM listofers WHERE project_id = ? AND number = ?",
            (project_id, number)
        )
        return row[0] if row else ""

    @staticmethod
    def rename(project_id, old_number, new_number, new_description=""):
        db.execute(
            "UPDATE listofers SET number = ?, description = ? WHERE project_id = ? AND number = ?",
            (new_number, new_description, project_id, old_number), commit=True
        )

    @staticmethod
    def delete_by_number(project_id, number):
        row = db.fetchone(
            "SELECT id FROM listofers WHERE project_id = ? AND number = ?",
            (project_id, number)
        )
        if row:
            lf_id = row[0]
            db.execute("DELETE FROM rebars WHERE listofer_id = ?", (lf_id,), commit=False)
            db.execute("DELETE FROM listofers WHERE id = ?", (lf_id,), commit=True)


class RebarModel:
    @staticmethod
    def add(listofer_id, pos, diameter, shape_name, dimensions, quantity,
            location, element_type, user, date, grade=None, standard="bs"):
        if grade is None:
            grade = config.DEFAULT_REBAR_GRADE
        if not standard:
            standard = "bs"
        return db.execute(
            "INSERT INTO rebars "
            "(listofer_id, pos, diameter, shape_name, dimensions, quantity, location, element_type, "
            "added_by, date_added, grade, standard) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (listofer_id, pos, diameter, shape_name, dimensions, quantity, location, element_type,
             user, date, grade, standard),
            commit=True
        )

    @staticmethod
    def update(rebar_id, listofer_id, pos, diameter, shape_name, dimensions, quantity,
               location, element_type, user, date, grade=None, standard="bs"):
        if grade is None:
            grade = config.DEFAULT_REBAR_GRADE
        if not standard:
            standard = "bs"
        db.execute(
            "UPDATE rebars SET listofer_id=?, pos=?, diameter=?, shape_name=?, dimensions=?, quantity=?, "
            "location=?, element_type=?, added_by=?, date_added=?, grade=?, standard=? WHERE id=?",
            (listofer_id, pos, diameter, shape_name, dimensions, quantity, location, element_type,
             user, date, grade, standard, rebar_id),
            commit=True
        )

    @staticmethod
    def delete(rebar_id):
        db.execute("DELETE FROM rebars WHERE id = ?", (rebar_id,), commit=True)

    @staticmethod
    def get_by_id(rebar_id):
        row = db.fetchone(
            "SELECT r.id, l.number, l.description, r.pos, r.diameter, r.shape_name, r.dimensions, r.quantity, "
            "r.location, r.element_type, r.added_by, r.date_added, "
            "COALESCE(r.grade, ?), COALESCE(r.standard, 'bs') "
            "FROM rebars r JOIN listofers l ON r.listofer_id = l.id WHERE r.id = ?",
            (config.DEFAULT_REBAR_GRADE, rebar_id)
        )
        if not row:
            return None
        return {
            "id": row[0],
            "listofer_number": row[1],
            "listofer_desc": row[2],
            "listofer_id": None,
            "pos": row[3],
            "diameter": row[4],
            "shape_name": row[5],
            "dimensions": row[6],
            "quantity": row[7],
            "location": row[8],
            "element_type": row[9],
            "user": row[10],
            "date": row[11],
            "grade": row[12],
            "standard": row[13],
        }

    @staticmethod
    def get_for_project(project_id, listofer_number=None):
        params = [config.DEFAULT_REBAR_GRADE, project_id]
        query = """
            SELECT r.id, l.number, l.description, r.pos, r.diameter, r.shape_name,
                   r.dimensions, r.quantity, r.location, r.element_type, r.added_by, r.date_added,
                   COALESCE(r.grade, ?), COALESCE(r.standard, 'bs')
            FROM rebars r
            JOIN listofers l ON r.listofer_id = l.id
            WHERE l.project_id = ?
        """
        if listofer_number and listofer_number != "-- Show All --":
            query += " AND l.number = ?"
            params.append(listofer_number)
        query += " ORDER BY l.number, r.pos"
        return db.fetchall(query, tuple(params))


class ScrapModel:
    @staticmethod
    def add_scrap(project_id, diameter, length_mm, grade=None, date=None, listofer_number=None):
        if grade is None:
            grade = config.DEFAULT_REBAR_GRADE
        if date is None:
            date = datetime.datetime.now().isoformat()

        existing = db.fetchone(
            "SELECT id FROM scraps WHERE project_id = ? AND diameter = ? "
            "AND length_mm = ? AND grade = ? "
            "AND ((listofer_number = ?) OR (listofer_number IS NULL AND ? IS NULL)) "
            "AND used = 0",
            (project_id, diameter, length_mm, grade, listofer_number, listofer_number)
        )
        if existing:
            return existing[0]

        return db.execute(
            "INSERT INTO scraps (project_id, diameter, length_mm, grade, date_created, used, listofer_number) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (project_id, diameter, length_mm, grade, date, listofer_number),
            commit=True
        )

    @staticmethod
    def get_available_scraps(project_id, diameter, grade=None):
        query = "SELECT id, length_mm, grade, listofer_number FROM scraps WHERE project_id = ? AND diameter = ? AND used = 0"
        params = [project_id, diameter]
        if grade is not None:
            query += " AND grade = ?"
            params.append(grade)
        query += " ORDER BY length_mm DESC"
        rows = db.fetchall(query, tuple(params))
        return [(row[0], row[1], row[2], row[3]) for row in rows]

    @staticmethod
    def mark_as_used(scrap_id):
        db.execute("UPDATE scraps SET used = 1 WHERE id = ?", (scrap_id,), commit=True)

    @staticmethod
    def delete_scrap(scrap_id):
        db.execute("DELETE FROM scraps WHERE id = ?", (scrap_id,), commit=True)

    @staticmethod
    def get_all_scraps(project_id, diameter=None, grade=None):
        query = """
            SELECT id, diameter, length_mm, grade, date_created, used, listofer_number
            FROM scraps
            WHERE project_id = ?
        """
        params = [project_id]
        if diameter is not None:
            query += " AND diameter = ?"
            params.append(diameter)
        if grade is not None:
            query += " AND grade = ?"
            params.append(grade)
        query += " ORDER BY diameter, length_mm DESC"
        return db.fetchall(query, tuple(params))


class StockModel:
    @staticmethod
    def add(project_id, diameter, length, quantity, grade=None):
        if grade is None:
            grade = config.DEFAULT_REBAR_GRADE
        return db.execute(
            "INSERT INTO stock (project_id, diameter, length, quantity, grade) VALUES (?, ?, ?, ?, ?)",
            (project_id, diameter, length, quantity, grade),
            commit=True
        )

    @staticmethod
    def update(stock_id, diameter, length, quantity, grade=None):
        if grade is None:
            grade = config.DEFAULT_REBAR_GRADE
        db.execute(
            "UPDATE stock SET diameter=?, length=?, quantity=?, grade=? WHERE id=?",
            (diameter, length, quantity, grade, stock_id),
            commit=True
        )

    @staticmethod
    def update_quantity(stock_id, quantity: int):
        db.execute(
            "UPDATE stock SET quantity = ? WHERE id = ?",
            (int(quantity), int(stock_id)),
            commit=True
        )

    @staticmethod
    def delete(stock_id):
        db.execute("DELETE FROM stock WHERE id=?", (stock_id,), commit=True)

    @staticmethod
    def get_all(project_id=None):
        if project_id is not None:
            rows = db.fetchall(
                "SELECT id, project_id, diameter, length, quantity, grade FROM stock "
                "WHERE project_id = ? OR project_id IS NULL ORDER BY diameter, length",
                (project_id,)
            )
        else:
            rows = db.fetchall(
                "SELECT id, project_id, diameter, length, quantity, grade FROM stock ORDER BY diameter, length"
            )
        return rows

    @staticmethod
    def get_for_diameter(project_id, diameter, grade=None):
        query = "SELECT id, diameter, length, quantity, grade FROM stock WHERE (project_id = ? OR project_id IS NULL) AND diameter = ?"
        params = [project_id, diameter]
        if grade is not None:
            query += " AND grade = ?"
            params.append(grade)
        query += " ORDER BY length DESC"
        return db.fetchall(query, tuple(params))

    @staticmethod
    def add_stock(project_id, diameter, length_mm, quantity, grade=None):
        if grade is None:
            grade = config.DEFAULT_REBAR_GRADE

        row = db.fetchone(
            "SELECT id, quantity FROM stock WHERE project_id IS ? AND diameter = ? AND length = ? AND grade = ?",
            (project_id, diameter, length_mm, grade)
        )
        if row:
            stock_id, qty0 = row
            new_qty = int(qty0 or 0) + int(quantity or 0)
            StockModel.update_quantity(stock_id, new_qty)
            return stock_id

        return StockModel.add(project_id, diameter, length_mm, quantity, grade)


class CuttingPlanModel:
    @staticmethod
    def compute_data_hash(project_id, listofer_filter, stock_length_m):
        rebars = RebarModel.get_for_project(project_id, listofer_filter)
        scraps = ScrapModel.get_all_scraps(project_id)

        # rebars now include grade at index 12 and standard at index 13
        data_str = json.dumps({
            "rebars": [
                {"id": r[0], "lf": r[1], "pos": r[3], "dia": r[4],
                 "shape": r[5], "dims": r[6], "qty": r[7], "grade": r[12], "standard": r[13]}
                for r in rebars
            ],
            "scraps": [
                {"id": s[0], "dia": s[1], "len": s[2], "grade": s[3], "used": s[5], "lf": s[6]}
                for s in scraps
            ],
            "stock_len": stock_length_m,
            "listofer_filter": listofer_filter or "-- All --"
        }, sort_keys=True, default=str)

        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    # بقیه متدهای CuttingPlanModel را اگر در پروژه داری همان قبلی نگه دار
    # (اینجا کوتاه کردم چون سؤال اصلی DB init/Models بود)


class CustomShapeModel:
    @staticmethod
    def create(code, name, definition_json):
        return db.execute(
            "INSERT INTO custom_shapes (code, name, definition) VALUES (?, ?, ?)",
            (code, name, json.dumps(definition_json)), commit=True
        )

    @staticmethod
    def get_by_code(code):
        row = db.fetchone(
            "SELECT id, code, name, definition FROM custom_shapes WHERE code = ?",
            (code,)
        )
        if row:
            return {"id": row[0], "code": row[1], "name": row[2], "definition": json.loads(row[3])}
        return None

    @staticmethod
    def get_all():
        rows = db.fetchall("SELECT id, code, name, definition FROM custom_shapes ORDER BY name")
        return [{"id": r[0], "code": r[1], "name": r[2], "definition": json.loads(r[3])} for r in rows]

    @staticmethod
    def update(code, name, definition_json):
        db.execute(
            "UPDATE custom_shapes SET name = ?, definition = ? WHERE code = ?",
            (name, json.dumps(definition_json), code), commit=True
        )

    @staticmethod
    def delete(code):
        db.execute("DELETE FROM custom_shapes WHERE code = ?", (code,), commit=True)