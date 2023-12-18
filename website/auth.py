from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    is_admin = False

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == 'admin' and password == 'admin':

            flash('Logged in as admin!', category='success')
            return redirect(url_for('views.admin_home'))

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            flash('Logged in successfully!', category='success')
            login_user(user, remember=True)
            return redirect(url_for('views.home'))

        flash('Incorrect email or password. Please try again.', category='error')

    return render_template("login.html", user=current_user, is_admin=is_admin)


@auth.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Recherchez l'utilisateur dans la base de données par e-mail
        user = User.query.filter_by(email=email).first()

        # Vérifiez que le nouveau mot de passe et la confirmation correspondent
        if new_password != confirm_password:
            flash('Les mots de passe ne correspondent pas. Veuillez réessayer.', category='error')
        else:
            if user:
                # Mettez à jour le mot de passe de l'utilisateur existant
                user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Mot de passe mis à jour avec succès.', category='success')
                return redirect(url_for('views.home'))
            else:
                # Si l'utilisateur n'existe pas, informez l'utilisateur
                flash('Aucun utilisateur associé à cet e-mail. Veuillez vous inscrire.', category='error')

    return render_template("forgot.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)
