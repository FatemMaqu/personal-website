from flask import (render_template, redirect, url_for, session, request, flash,
                   abort)
import os

from . import admin
from app import db
from utils import admin_only, check_image, and_profile
from models import Ability, Experience, Contact, Message
from forms import (LoginForm, ProfileForm, AbilityForm, ExperienceForm,
                   ChangePasswordForm, ContactForm)
from sqlalchemy.exc import IntegrityError


# ------------------ START ------------------ #
@admin.route('/login', methods=["GET", "POST"])
@and_profile
def login(profile):
    form = LoginForm(request.form)
    if request.method == "POST":
        if not form.validate_on_submit:
            abort(400)

        if not profile.check_password(form.password.data):
            flash("Incorrect Password", "danger")
            return render_template("admin/login/login.html",
                                   form=form,
                                   profile=profile)

        session['fullname'] = profile.fullname
        return redirect(url_for("admin.set_profile"))
    if session.get("fullname"):
        flash("You already logged in", 'info')
        return redirect(url_for("admin.set_profile"))
    return render_template("admin/login/login.html", form=form,
                           profile=profile)


# ------------------ PROFILE ------------------ #
@admin.route('/', methods=['GET', 'POST'])
@admin.route('/profile', methods=['GET', 'POST'])
@and_profile
@admin_only
def set_profile(profile):
    form = ProfileForm(obj=profile)
    if request.method == 'POST':
        if not form.validate_on_submit:
            abort(400)
        if form.thumbnail.data:
            afile = form.thumbnail.data
            filename = check_image(afile.filename)
            if profile.thumbnail != "thumbnail-img.jpg":
                os.remove(os.path.join(
                    "static/images/thumbnail" + profile.thumbnail))
            afile.save(os.path.join('static/images/thumbnail', filename))
            profile.thumbnail = filename
        if form.bg.data:
            afile = form.bg.data
            filename = check_image(afile.filename)
            if profile.bg != "background-img.jpg":
                os.remove(os.path.join("static/images/bg" + profile.bg))
            afile.save(os.path.join('static/images/bg', filename))
            profile.bg = filename
        profile.fullname = form.fullname.data
        profile.location = form.location.data
        profile.birth = form.birth.data
        profile.age = form.age.data
        profile.about = form.about.data
        db.session.commit()
        flash("Profile modified", "success")
        return redirect(url_for('admin.set_profile'))

    return render_template("admin/index.html", form=form, profile=profile)


@admin.route('/profile/change/password', methods=['GET', 'POST'])
@admin.route('/change/password', methods=['GET', 'POST'])
@and_profile
@admin_only
def change_password(profile):
    form = ChangePasswordForm(request.form)
    if request.method == "POST":
        if not form.validate_on_submit:
            abort(400)
        if not profile.check_password(form.old_password.data):
            flash("""Wrong password, please input your current password in the
                    firstfield""", "danger")
            return redirect(url_for('admin.change_password'))
        if form.new_password.data != form.config_password.data:
            flash("""New password and configure password were not match, try
                    again""", "warning")
            return redirect(url_for('admin.change_password'))
        try:
            profile.password = form.new_password.data
            db.session.commit()
            flash("password changed", "success")
            return redirect(url_for('admin.change_password'))
        except ValueError as e:
            flash(str(e), "warning")
    return render_template("admin/change_password.html",
                           form=form,
                           profile=profile)


@admin.route('/profile/delete/img/thumbnail')
@and_profile
@admin_only
def delete_thumbnail(profile):
    if profile.thumbnail == "thumbnail-img.jpg":
        flash('You can\'t set thumbnail image null', "warning")
        return redirect(url_for('admin.set_profile'))
    os.remove(os.path.join("static/images/thumbnail/" + profile.thumbnail))
    profile.thumbnail = "thumbnail-img.jpg"
    db.session.commit()
    flash("Thubmnail image deleted", "success")
    return redirect(url_for('admin.set_profile'))


@admin.route('/profile/delete/img/bg')
@and_profile
@admin_only
def delete_background(profile):
    if profile.bg == "background-img.jpg":
        flash('You can\'t set background image null', "warning")
        return redirect(url_for('admin.set_profile'))
    os.remove(os.path.join("static/images/bg/" + profile.bg))
    profile.bg = "background-img.jpg"   # Set Defualt
    db.session.commit()
    flash("Background image deleted", "success")
    return redirect(url_for('admin.set_profile'))


# ------------------ RESUME ------------------ #
# ------------------ Abilities ----------------#
@admin.route('/resume/skills', methods=['GET'])
@and_profile
@admin_only
def skills(profile):
    form = AbilityForm(request.form)
    skills = reversed(Ability.query.filter(
        Ability.kind == 'skill').order_by(Ability.id).all())
    return render_template('admin/abilities.html',
                           form=form,
                           abilities=skills,
                           kind='skill',
                           profile=profile
                           )


@admin.route('/resume/languages', methods=['GET'])
@and_profile
@admin_only
def languages(profile):
    form = AbilityForm(request.form)
    langs = reversed(Ability.query.filter(
        Ability.kind == 'lang').order_by(Ability.id).all())
    return render_template('admin/abilities.html', form=form, abilities=langs,
                           kind='language',
                           profile=profile
                           )


@admin.route('/resume/abilities/<string:kind>/new', methods=['POST'])
@admin_only
def new_ability(kind):
    if kind not in ['language', 'skill']:
        abort(404)

    private_page = f"admin.{kind}s"
    form = AbilityForm(request.form)
    if not form.validate_on_submit:
        abort(400)
    try:
        scale = form.scale.data if form.scale.data else form.progress.data
        new_ability = Ability(
            name=form.name.data,
            scale=scale,
            kind="skill" if kind == 'skill' else 'lang',
        )
        db.session.add(new_ability)
        db.session.commit()
        flash(f"New {kind} added successfully!", 'success')
        return redirect(url_for(private_page))
    except ValueError as e:
        flash(str(e), 'warning')
    except IntegrityError:
        db.session.rollback()
        flash(f"This {kind} is allready exist", 'danger')
    return redirect(url_for(private_page))


@admin.route('/resume/delete/ability/<int:id>', methods=['GET'])
@admin_only
def delete_ability(id):
    ability = Ability.query.filter(Ability.id == id).first()
    if not ability:
        abort(404)
    private_page = "admin.skills" if ability.kind == 'skill' else 'admin.languages'
    db.session.delete(ability)
    db.session.commit()
    flash(f"{ability.kind} deleted", "success")
    return redirect(url_for(private_page))


# ------------------ Experiences ----------------`` #
@admin.route('/resume/educations', methods=['GET'])
@and_profile
@admin_only
def educations(profile):
    form = ExperienceForm(request.form)
    educations = reversed(Experience.query.filter(
        Experience.kind == "education").order_by(Experience.id).all())
    return render_template("admin/experiences.html",
                           experiences=educations,
                           form=form,
                           kind='education',
                           profile=profile
                           )


@admin.route('/resume/careers', methods=['GET'])
@and_profile
@admin_only
def careers(profile):
    form = ExperienceForm(request.form)
    careers = reversed(Experience.query.filter(
        Experience.kind == "career").order_by(Experience.id).all())

    return render_template("admin/experiences.html",
                           experiences=careers,
                           form=form,
                           kind="career",
                           profile=profile,
                           )


@admin.route('/resume/experiences/<string:kind>/new/', methods=['POST'])
@admin_only
def new_experience(kind):
    if kind not in ("career", "education"):
        abort(404)
    private_page = f"admin.{kind.lower()}s"
    form = ExperienceForm(request.form)
    if not form.validate_on_submit:
        abort(400)

    new_experience = Experience(form.title.data,
                                form.start_date.data,
                                form.finish_date.data,
                                form.location.data,
                                kind,
                                form.description.data
                                )
    db.session.add(new_experience)
    db.session.commit()
    flash(f"New {kind} added successfully!", "success")
    return redirect(url_for(private_page))


@admin.route('/resume/experiences/edit/<int:id>', methods=['GET', 'POST'])
@and_profile
@admin_only
def edit_experience(profile, id):
    experience = Experience.query.filter(Experience.id == id).first()
    if not experience:
        abort(404)
    private_page = f"admin.{experience.kind}s"

    form = ExperienceForm(obj=experience)
    if request.method == "POST":
        if not form.validate_on_submit:
            abort(400)

        experience.title = form.title.data
        experience.start_date = form.start_date.data
        experience.finish_date = form.finish_date.data
        experience.location = form.location.data
        experience.description = form.description.data
        db.session.commit()
        flash("Experience edited!", "success")
        return redirect(url_for(private_page))

    return render_template('admin/edit_experience.html',
                           form=form,
                           id=id,
                           private_page=private_page,
                           profile=profile
                           )


@admin.route('/resume/experiences/delete/<int:id>', methods=['GET'])
@admin_only
def delete_experience(id):
    experience = Experience.query.filter(Experience.id == id).first()
    if not experience:
        abort(404)
    private_page = f"admin.{experience.kind}s"

    db.session.delete(experience)
    db.session.commit()
    flash("Experience deleted!", "success")
    return redirect(url_for(private_page))


# ------------------ CONTACTS ------------------ #
@admin.route('/contacts', methods=['GET', 'POST'])
@and_profile
@admin_only
def contact_info(profile):
    contacts = reversed(Contact.query.all())
    form = ContactForm()
    if request.method == 'POST':
        if not form.validate_on_submit:
            abort(400)

        try:
            new_contact_address = Contact(form.name.data, form.address.data)

            if form.logo.data:
                afile = form.logo.data
                filename = check_image(afile.filename)
                afile.save(os.path.join('static/images/logo/', filename))
                new_contact_address.logo = filename

            db.session.add(new_contact_address)
            db.session.commit()

            flash("New contact address added!", "success")
            return redirect(url_for('admin.contact_info'))
        except IntegrityError:
            db.session.rollback()
            flash("Duplicated contact", "danger")

    return render_template('admin/contact_info.html',
                           contacts=contacts,
                           form=form, profile=profile
                           )


@admin.route('contacts/<int:id>/delete', methods=['GET'])
@admin_only
def delete_contact(id):
    contact = Contact.query.filter(Contact.id == id).first()
    if not contact:
        abort(404)

    os.remove(os.path.join("static/images/logo/" + contact.logo))
    db.session.delete(contact)
    db.session.commit()
    flash('Contact address deleted successfully!', 'success')
    return redirect(url_for('admin.contact_info'))


@admin.route('/contact/inbox')
@and_profile
@admin_only
def inbox(profile):
    messages = reversed(Message.query.order_by(Message.postage_date).all())
    return render_template('admin/inbox.html',
                           messages=messages,
                           profile=profile
                           )


@admin.route('contact/inbox/<int:id>')
@and_profile
@admin_only
def read_mail(profile, id):
    message = Message.query.filter(Message.id == id).first()
    if not message:
        abort(404)

    return render_template('admin/single_message.html',
                           message=message,
                           profile=profile
                           )


@admin.route('/contact/inbox/<int:id>/delete', methods=['GET'])
@admin_only
def delete_mail(id):
    message = Message.query.filter(Message.id == id).first()
    if not message:
        abort(404)

    db.session.delete(message)
    db.session.commit()
    flash("Message deleted!", "success")
    return redirect(url_for('admin.inbox'))


# ------------------ THE END ------------------ #
@admin.route('/logout')
@admin_only
def logout():
    session.clear()
    return redirect(url_for("index"))
