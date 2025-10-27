from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import Users, Modules, Activities, GameSettings
from app.models import Groups, ModuleAssignments
from functools import wraps
from app.models import Users, Groups, GroupMembers

teacher_bp = Blueprint("teacher", __name__, template_folder="../templates/teacher")

def _require_teacher():
    if current_user.role not in ("teacher", "admin"):
        abort(403)

def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(401)
        role = (current_user.role or "student").strip().lower()
        if role not in ("teacher", "admin"):
            return abort(403)
        return view_func(*args, **kwargs)
    return wrapper


@teacher_bp.route("/dashboard")
@login_required
@teacher_required
def dashboard():
    from app.models import Modules, Activities, Groups

    modules = Modules.query.order_by(Modules.id.desc()).all()
    recent_activities = Activities.query.order_by(Activities.id.desc()).limit(8).all()

    my_groups = Groups.query.filter_by(teacher_id=current_user.id) \
                            .order_by(Groups.id.desc()).all()

    # aplanar estudiantes de todos los grupos y quitar duplicados
    seen, students = set(), []
    for g in my_groups:
        for u in g.students:
            if u.id not in seen:
                seen.add(u.id)
                students.append(u)

    return render_template(
        "teacher/dashboard.html",
        modules=modules,
        recent_activities=recent_activities,
        groups=my_groups,
        students=students,
    )

# ----------------- Modules CRUD -----------------
@teacher_bp.route("/modules/create", methods=["POST"])
@login_required
def module_create():
    _require_teacher()
    title = request.form.get("title", "").strip()
    summary = request.form.get("summary", "").strip()
    level = request.form.get("level")
    xp_reward = request.form.get("xp_reward")
    is_published = True if request.form.get("is_published") == "on" else False
    if not title:
        flash("Título es requerido", "error")
        return redirect(url_for("teacher.dashboard"))
    m = Modules(title=title, summary=summary or None,
                level=int(level) if level else None,
                xp_reward=int(xp_reward) if xp_reward else None,
                is_published=is_published)
    db.session.add(m)
    db.session.commit()
    flash("Módulo creado", "success")
    return redirect(url_for("teacher.dashboard"))

@teacher_bp.post("/modules/<int:module_id>/update", endpoint="module_update")
@login_required
@teacher_required
def module_update(module_id):
    from app.models import Modules
    m = Modules.query.get_or_404(module_id)

    def to_int(val):
        try:
            return int(val) if (val is not None and str(val).strip() != "") else None
        except ValueError:
            return None

    m.title = (request.form.get("title") or "").strip()
    m.level = to_int(request.form.get("level"))
    m.xp_reward = to_int(request.form.get("xp_reward"))
    m.is_published = bool(request.form.get("is_published"))
    m.summary = request.form.get("summary") or None

    db.session.commit()
    flash("Module updated.", "success")
    return redirect(url_for("teacher.dashboard") + "#modules")


# --- Modules ---
@teacher_bp.post("/modules/<int:module_id>/delete")
@login_required
@teacher_required
def module_delete(module_id):
    m = Modules.query.get_or_404(module_id)
    db.session.delete(m)
    db.session.commit()
    flash("Module deleted.", "success")
    # back to dashboard, modules section
    return redirect(url_for("teacher.dashboard") + "#modules")

# ----------------- Activities CRUD -----------------
@teacher_bp.route("/activities/create", methods=["POST"])
@login_required
def activity_create():
    _require_teacher()
    module_id = request.form.get("module_id")
    title = request.form.get("title", "").strip()
    act_type = request.form.get("type", "quiz").strip()
    max_points = request.form.get("max_points")
    position = request.form.get("position")
    is_published = True if request.form.get("is_published") == "on" else False
    content_json = request.form.get("content_json")  # json string

    attempt_limit = request.form.get("attempt_limit", type=int)
    default_xp = request.form.get("default_xp", type=int)
    a = Activities(
        module_id=module_id,
        title=title,
        type= act_type or "quiz",
        max_points=max_points,
        position=position,
        is_published=bool(is_published),
        content_json=content_json or None,
        attempt_limit=attempt_limit,
        default_xp=default_xp,
    )
    db.session.add(a);
    db.session.commit()
    flash("Activity created.", "success")
    return redirect(url_for("teacher.dashboard") + "#activities")


@teacher_bp.route("/activities/<int:activity_id>/update", methods=["POST"])
@login_required
def activity_update(activity_id):
    _require_teacher()
    a = Activities.query.get_or_404(activity_id)
    a.title = request.form.get("title", a.title).strip()
    a.type = request.form.get("type", a.type).strip()
    a.max_points = int(request.form.get("max_points")) if request.form.get("max_points") else a.max_points
    a.position = int(request.form.get("position")) if request.form.get("position") else a.position
    a.is_published = True if request.form.get("is_published") == "on" else False
    a.content_json = request.form.get("content_json") or a.content_json
    a.attempt_limit = request.form.get("attempt_limit", type=int)
    a.default_xp = request.form.get("default_xp", type=int)
    # (keep the rest: title/type/max_points/position/is_published/content_json)
    db.session.commit()
    flash("Activity updated.", "success")
    return redirect(url_for("teacher.dashboard") + "#activities")


@teacher_bp.post("/activities/<int:activity_id>/delete")
@login_required
@teacher_required
def activity_delete(activity_id):
    a = Activities.query.get_or_404(activity_id)
    db.session.delete(a)
    db.session.commit()
    flash("Activity deleted.", "success")
    # back to dashboard, activities section
    return redirect(url_for("teacher.dashboard") + "#activities")




# GROUPS LIST
@teacher_bp.route("/groups")
@login_required
@teacher_required
def groups():
    q = Groups.query
    if current_user.role != "admin":
        q = q.filter_by(teacher_id=current_user.id)
    items = q.order_by(Groups.id.desc()).all()
    return render_template("teacher/groups.html", groups=items)

# Groups
@teacher_bp.post("/groups/create")
@login_required
@teacher_required
def group_create():
    name = (request.form.get("name") or "").strip()
    grade = (request.form.get("grade") or "").strip() or None
    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("teacher.dashboard") + "#groups")
    g = Groups(name=name, grade=grade, teacher_id=current_user.id)
    db.session.add(g); db.session.commit()
    flash("Group created.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")


@teacher_bp.post("/groups/<int:group_id>/edit")
@login_required
@teacher_required
def group_update(group_id):
    g = Groups.query.get_or_404(group_id)
    if current_user.role != "admin" and g.teacher_id != current_user.id:
        abort(403)
    g.name = (request.form.get("name") or "").strip()
    g.grade = (request.form.get("grade") or "").strip() or None
    db.session.commit()
    flash("Group updated.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")


@teacher_bp.post("/groups/<int:group_id>/delete")
@login_required
@teacher_required
def group_delete(group_id):
    g = Groups.query.get_or_404(group_id)
    if current_user.role != "admin" and g.teacher_id != current_user.id:
        abort(403)
    db.session.delete(g)
    db.session.commit()
    flash("Group deleted.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")


# Group membership
@teacher_bp.post("/groups/<int:group_id>/add-student")
@login_required
@teacher_required
def group_add_student(group_id):
    g = Groups.query.get_or_404(group_id)
    if current_user.role != "admin" and g.teacher_id != current_user.id:
        abort(403)
    sid = (request.form.get("student_id") or "").strip()
    from app.models import Users, GroupMembers
    s = Users.query.get(sid) if sid.isdigit() else None
    if not s or s.role != "student":
        flash("Student not found.", "error")
        return redirect(url_for("teacher.dashboard") + "#groups")
    db.session.add(GroupMembers(group_id=g.id, user_id=s.id))
    db.session.commit()
    flash("Student added to group.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")


@teacher_bp.post("/groups/<int:group_id>/remove-student")
@login_required
@teacher_required
def group_remove_student(group_id):
    from app.models import GroupMembers
    gm = GroupMembers.query.filter_by(
        group_id=group_id, user_id=request.form.get("student_id")
    ).first()
    if gm:
        db.session.delete(gm); db.session.commit()
        flash("Student removed.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")


# Assign / unassign modules
@teacher_bp.post("/assignments/create")
@login_required
@teacher_required
def assign_module():
    target_type = request.form.get("target_type")  # 'group' or 'student'
    target_id = int(request.form.get("target_id"))
    module_id = int(request.form.get("module_id"))
    ma = ModuleAssignments(group_id=target_id if target_type == "group" else None,
                           module_id=module_id)
    db.session.add(ma); db.session.commit()
    flash("Module assigned.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")


@teacher_bp.post("/assignments/<int:assign_id>/delete")
@login_required
@teacher_required
def unassign_module(assign_id):
    ma = ModuleAssignments.query.get_or_404(assign_id)
    db.session.delete(ma); db.session.commit()
    flash("Assignment removed.", "success")
    return redirect(url_for("teacher.dashboard") + "#groups")

@teacher_bp.post("/students/<int:user_id>/stats", endpoint="student_edit_stats")
@login_required
@teacher_required
def student_edit_stats(user_id):
    """Update a student's RPG stats from the teacher dashboard."""
    from app.models import Users, StudentProfiles

    # 1) Find the student
    student = Users.query.get_or_404(user_id)
    if student.role != "student":
        abort(400)

    # 2) Ensure a StudentProfiles row exists
    profile = StudentProfiles.query.filter_by(user_id=student.id).first()
    if not profile:
        profile = StudentProfiles(user_id=student.id)
        db.session.add(profile)
        # do not commit yet; we'll commit after setting fields

    # 3) Helpers to parse numbers safely
    def to_int(name, default):
        raw = (request.form.get(name) or "").strip()
        try:
            return int(raw)
        except Exception:
            return default

    def to_float(name, default):
        raw = (request.form.get(name) or "").strip()
        try:
            return float(raw)
        except Exception:
            return default

    # 4) Update fields (fallback to existing values if parsing fails)
    profile.credit_score        = to_int("credit_score",        profile.credit_score or 650)
    profile.cash_balance        = to_float("cash_balance",      profile.cash_balance or 500.0)
    profile.salary_monthly      = to_float("salary_monthly",    profile.salary_monthly or 1200.0)
    profile.has_car             = "has_car" in request.form
    profile.car_payment_monthly = to_float("car_payment_monthly", profile.car_payment_monthly or 0.0)
    profile.level               = to_int("level",               profile.level or 1)
    profile.xp                  = to_int("xp",                  profile.xp or 0)
    profile.energy              = to_int("energy",              profile.energy or 100)

    # 5) Save & go back
    db.session.commit()
    flash("Student stats updated.", "success")
    return redirect(url_for("teacher.dashboard") + "#students")


# Students list (only students)
@teacher_bp.get("/students", endpoint="students_list")
@login_required
@teacher_required
def students_list():
    from app.models import Users, Groups
    students = Users.query.filter_by(role="student").order_by(Users.id.desc()).all()
    groups = Groups.query.filter_by(teacher_id=current_user.id).order_by(Groups.id.desc()).all()
    return render_template("teacher/students.html", students=students, groups=groups)


# Add a student to a group (POST)
@teacher_bp.post("/students/add_to_group", endpoint="students_add_to_group")
@login_required
@teacher_required
def students_add_to_group():
    from app.models import Users, Groups, GroupMembers, db

    sid = (request.form.get("student_id") or "").strip()
    gid = (request.form.get("group_id") or "").strip()

    # basic validation
    if not sid.isdigit() or not gid.isdigit():
        flash("Invalid student or group.", "error")
        return redirect(url_for("teacher.students_list"))

    s = Users.query.get_or_404(int(sid))
    g = Groups.query.get_or_404(int(gid))

    if s.role != "student":
        flash("Selected user is not a student.", "error")
        return redirect(url_for("teacher.students_list"))

    # ownership: only teacher who owns the group (or admin)
    if current_user.role != "admin" and g.teacher_id != current_user.id:
        abort(403)

    exists = GroupMembers.query.filter_by(group_id=g.id, user_id=s.id).first()
    if exists:
        flash("Student is already in that group.", "success")
        return redirect(url_for("teacher.students_list"))

    db.session.add(GroupMembers(group_id=g.id, user_id=s.id))
    db.session.commit()
    flash("Student added to group.", "success")
    return redirect(url_for("teacher.students_list"))


@teacher_bp.route("/modules/<int:module_id>/activities/builder", methods=["GET", "POST"])
@login_required
@teacher_required
def activities_builder(module_id):
    m = Modules.query.get_or_404(module_id)
    if request.method == "POST":
        title = (request.form.get("title") or "New Activity").strip()
        position = request.form.get("position", type=int)
        max_points = request.form.get("max_points", type=int)
        is_published = bool(request.form.get("is_published"))
        content_json = request.form.get("content_json") or "{}"

        a = Activities(
            module_id=m.id,
            title=title,
            position=position,
            type="mcq_sim",
            max_points=max_points,
            is_published=is_published,
            content_json=content_json,
        )
        db.session.add(a)
        db.session.commit()
        flash("MCQ game created.", "success")
        return redirect(url_for("teacher.activities_list", module_id=m.id))
    return render_template("teacher/activity_builder.html", module=m)

def get_settings():
    s = GameSettings.query.get(1)
    if not s:
        s = GameSettings(id=1)
        db.session.add(s)
        db.session.commit()
    return s

@teacher_bp.route("/settings", methods=["GET"])
@login_required
def settings_page():
    if current_user.role not in ("teacher","admin"):
        abort(403)
    s = get_settings()
    return render_template("teacher/settings.html", settings=s)

@teacher_bp.route("/settings", methods=["POST"])
@login_required
def settings_save():
    if current_user.role not in ("teacher","admin"):
        abort(403)
    s = get_settings()
    s.xp_base = request.form.get("xp_base", type=int) or s.xp_base
    s.xp_growth = request.form.get("xp_growth", type=int) or s.xp_growth
    s.max_attempts_default = request.form.get("max_attempts_default", type=int) or s.max_attempts_default
    db.session.commit()
    flash("Game settings saved.", "success")
    return redirect(url_for("teacher.settings_page"))
