from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "GET":
        return render_template("auth/register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip() or None
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for("auth.register"))

    if password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("auth.register"))

    existing = User.query.filter(
        db.or_(User.username == username, User.email == email)
    ).first()
    if existing:
        flash("Username or email already in use.", "danger")
        return redirect(url_for("auth.register"))

    user = User(username=username, email=email, roles="user")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    flash("Account created and logged in!", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "GET":
        return render_template("auth/login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        flash("Invalid username or password.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user)
    flash("Welcome back!", "success")
    next_page = request.args.get("next")
    return redirect(next_page or url_for("main.home"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
