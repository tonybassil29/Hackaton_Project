import codecs
import csv
from datetime import datetime
from sqlite3 import IntegrityError
from io import TextIOWrapper
from datetime import datetime
import requests
from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect, Response
from flask_login import login_required, current_user
from .models import Note, User, Contact
from . import db
import json
from flask import jsonify
from sqlalchemy import or_, asc

views = Blueprint('views', __name__)


@views.route('/profile', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        note = request.form.get('note')
        if len(note) < 1:
            flash('Note is too short!', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)


@views.route('/delete-note', methods=['POST'])
def delete_note():
    note = json.loads(request.data)
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})


@views.route('/')
def admin():
    is_admin = True
    users = User.query.all()

    return render_template("index.html", user=current_user)

@views.route('/users', methods=['GET', 'POST'])
def admin_users():
    is_admin = True

    if request.method == 'POST':
        # Récupérez l'ID de l'utilisateur à supprimer à partir du formulaire
        user_id = request.form.get('id')

        # Vérifiez si l'ID est valide et effectuez l'opération de suppression
        if user_id:
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()

    # Récupérez la liste mise à jour des utilisateurs après la suppression
    users = User.query.all()

    return render_template("admin_users.html", users=users, is_admin=is_admin, user=current_user)

@views.route('/admin')
def admin_home():
    is_admin = True
    users = User.query.all()

    return render_template("admin.html", user=current_user, is_admin=is_admin)


from flask import redirect, url_for


@views.route('/delete_user/<int:id>', methods=['POST'])
def delete_user(id):
    user = User.query.get(id)

    if user:
        db.session.delete(user)
        db.session.commit()

    # Redirigez l'administrateur vers la page des utilisateurs après la suppression
    return redirect(url_for('views.admin_users'))


from sqlalchemy import desc



@views.route('/contacts', methods=['GET'])
@login_required
def contacts():
    contacts_query = Contact.query.filter_by(user_id=current_user.id)
    contacts_query = contacts_query.order_by(asc(Contact.created_at))

    contacts = contacts_query.all()

    return render_template("contacts.html", user=current_user, contacts=contacts)



@views.route('/contacts/sort', methods=['GET'])
@login_required
def sort_contacts():
    # Get the sorting criterion and order from the request parameters
    sort_by = request.args.get('sort_by', 'created_at_asc')

    # Set the default sorting to 'created_at' in ascending order
    sort_column, sort_order = 'created_at', 'asc'

    # Determine the actual sorting criterion and order based on the user's selection
    if sort_by == 'first_name':
        sort_column, sort_order = 'first_name', 'asc'  # Default to ascending order for names

    elif sort_by == 'last_name':
        sort_column, sort_order = 'last_name', 'asc'  # Default to ascending order for names

    elif sort_by == 'email':
        sort_column, sort_order = 'email', 'asc'  # Default to ascending order for email

    elif sort_by == 'created_at_asc':
        sort_column, sort_order = 'created_at', 'asc'
    elif sort_by == 'created_at_desc':
        sort_column, sort_order = 'created_at', 'desc'

    # Query the contacts based on the user's ID and apply sorting
    contacts = (
        Contact.query
        .filter_by(user_id=current_user.id)
        .order_by(asc(sort_column) if sort_order == 'asc' else desc(sort_column))
        .all()
    )

    return render_template("contacts.html", user=current_user, contacts=contacts)


from sqlalchemy.exc import IntegrityError

@views.route('/add-contact', methods=['GET', 'POST'])
@login_required
def add_contact():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        birthday = request.form.get('birthday')
        email = request.form.get('email')
        phone = request.form.get('phone')
        category = request.form.get('category')

        birthday = datetime.strptime(birthday, '%Y-%m-%d').date() if birthday else None
        existing_contact = Contact.query.filter_by(email=email, user_id=current_user.id).first()

        if existing_contact:
            flash('Un contact avec la même adresse e-mail existe déjà!', category='error')
        else:
            new_contact = Contact(
                first_name=first_name,
                last_name=last_name,
                address=address,
                postal_code=postal_code,
                birthday=birthday,
                email=email,
                phone=phone,
                category=category,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                user_id=current_user.id
            )

            db.session.add(new_contact)

            try:
                db.session.commit()
                flash('Contact ajouté!', category='success')
            except IntegrityError as e:
                db.session.rollback()
                flash('Erreur lors de l\'ajout du contact. Veuillez réessayer.', category='error')
                print(f"IntegrityError: {str(e)}")

    return render_template("add_contact.html", user=current_user)


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views.route('/export-contacts-csv', methods=['GET'])
@login_required
def export_contacts_csv():
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    csv_data = [['Nom', 'Prenom', 'Adresse', 'Code postal', 'Date d\'anniversaire', 'Email', 'Numero de telephone', 'Categorie']]

    for contact in contacts:
        cleaned_address = clean_address(contact.address)
        csv_data.append([
            contact.first_name,
            contact.last_name,
            cleaned_address,
            contact.postal_code,
            contact.birthday,
            contact.email,
            contact.phone,
            contact.category
        ])

    csv_content = '\n'.join([','.join(map(str, row)) for row in csv_data])
    csv_content = codecs.encode(csv_content, 'utf-8')

    response = Response(csv_content, content_type='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename=all_contacts.csv'

    return response

def clean_address(address):
    # Ajoute ici toute logique de nettoyage nécessaire pour les adresses
    # Par exemple, suppression de caractères spéciaux indésirables, formatage, etc.
    cleaned_address = address.replace(',', ' ')  # Remplacer les virgules par un espace
    return cleaned_address


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@views.route('/import-csv', methods=['POST'])
@login_required
def import_csv():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné.', category='error')
        return redirect(url_for('views.contacts'))

    file = request.files['file']

    if file.filename == '':
        flash('Aucun fichier sélectionné.', category='error')
        return redirect(url_for('views.contacts'))

    if file:
        try:
            csv_reader = csv.reader(TextIOWrapper(file, encoding='utf-8'), delimiter=',', quotechar='"')
            next(csv_reader)

            for row in csv_reader:
                first_name = row[0]
                last_name = row[1]
                address = row[2]
                postal_code = row[3]
                birthday = row[4]
                email = row[5]
                phone = row[6]
                category = row[7]

                existing_contact = Contact.query.filter_by(email=email).first()

                if not existing_contact:
                    new_contact = Contact(
                        first_name=first_name,
                        last_name=last_name,
                        address=address,
                        postal_code=postal_code,
                        birthday=birthday,
                        email=email,
                        phone=phone,
                        category=category,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        user_id=current_user.id
                    )

                    db.session.add(new_contact)

            db.session.commit()

            flash('Importation réussie.', category='success')
        except csv.Error as e:
            flash(f'Erreur lors de l\'importation du fichier CSV: {e}', category='error')

    return redirect(url_for('views.contacts'))

@views.route('/toggle_user/<int:id>', methods=['POST'])
def toggle_user(id):
    # Récupérer l'utilisateur de la base de données en utilisant l'id
    user = User.query.get(id)

    # Inverser l'état d'activation/désactivation
    user.is_active = not user.is_active

    # Sauvegarder les modifications dans la base de données
    db.session.commit()

    # Ajouter un message flash en fonction de l'état actuel de l'utilisateur
    if user.is_active:
        flash(f'Utilisateur {user.id} a été activé.', category='success')
    else:
        flash(f'Utilisateur {user.id} a été désactivé.', category='success')

    return redirect(url_for('views.admin_users'))

@views.route('/edit-contact/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    contact = Contact.query.get(contact_id)

    if request.method == 'POST':
        contact.first_name = request.form.get('first_name')
        contact.last_name = request.form.get('last_name')
        contact.address = request.form.get('address')
        contact.postal_code = request.form.get('postal_code')
        contact.birthday = request.form.get('birthday')
        contact.email = request.form.get('email')
        contact.phone = request.form.get('phone')
        contact.category = request.form.get('category')
        contact.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Contact updated!', category='success')
        return redirect(url_for('views.contacts'))

    return render_template("edit_contact.html", user=current_user, contact=contact)


@views.route('/delete-contact/<int:contact_id>', methods=['GET'])
@login_required
def delete_contact(contact_id):
    contact = Contact.query.get(contact_id)

    if contact:
        db.session.delete(contact)
        db.session.commit()
        flash('Contact deleted!', category='success')

    return redirect(url_for('views.contacts'))



@views.route('/autocomplete', methods=['GET'])
@login_required
def autocomplete():
    # Récupérer le terme de recherche depuis les paramètres de requête
    query = request.args.get('query', '')

    # Construire l'URL de l'API Adresse avec le terme de recherche
    url = f"https://api-adresse.data.gouv.fr/search/?q={query}&autocomplete=1"

    try:
        # Faire la requête à l'API Adresse
        response = requests.get(url)
        data = response.json()

        # Récupérer les résultats de la réponse
        results = data.get('features', [])

        # Formater les résultats
        formatted_results = [
            {
                'label': result['properties']['label'],
                'score': result['properties']['score'],
                'housenumber': result['properties']['housenumber'],
                'id': result['properties']['id'],
                'name': result['properties']['name'],
                'postcode': result['properties']['postcode'],
                'citycode': result['properties']['citycode'],
                'x': result['properties']['x'],
                'y': result['properties']['y'],
                'city': result['properties']['city'],
                'context': result['properties']['context'],
                'type': result['properties']['type'],
                'importance': result['properties']['importance'],
                'street': result['properties']['street'],
            }
            for result in results
        ]

        # Retourner les résultats au format JSON
        return jsonify(formatted_results)

    except Exception as e:
        # En cas d'erreur, retourner une réponse d'erreur
        return jsonify({'error': str(e)}), 500



