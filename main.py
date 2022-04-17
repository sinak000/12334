#  -----------------------------------------------------------------------------------------
from flask import Flask, render_template, redirect, abort, request, Blueprint, jsonify
import requests
import os
import sqlalchemy
from data import db_session
from data.estate_items import Item
from data.users import User                               # импорт библиотек
from data.images import Image
from data.signings import Signing
from forms.user import RegisterForm, LoginForm
from forms.buildings_edit import BuildingForm
from forms.sign_for_show import SignForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
#  ------------------------------------------------------------------------------------------

app = Flask(__name__, template_folder='../templates')

app.config['SECRET_KEY'] = 'yandex_secret_key'

login_manager = LoginManager()

login_manager.init_app(app)

blueprint = Blueprint(
    'estate_api',
    __name__,
    template_folder='templates'
)

# -----------------------------------------------------------------


@blueprint.route('/api/estate')


def get_estate():

    db_sess = db_session.create_session()
    estates = db_sess.query(Item).all()
    for item in estates:
        print(item)                                  # о враче
    print(1)
    return jsonify(
        {
            'news':
                [item.to_dict(only=('name', 'about', 'address', 'price', 'image_link', 'tags'))
                 for item in estates]
        }
    )


# -----------------------------------------------------------------


@login_manager.user_loader


def load_user(user_id):

    db_sess = db_session.create_session()
    print(2)
    return db_sess.query(User).get(user_id)


# -----------------------------------------------------------------------


@app.route('/logout')
@login_required

                                           # выход из записи
def logout():

    logout_user()
    print(3)
    return redirect("/")

# ------------------------------------------------------------------------


@app.route('/index')
@app.route('/')

                                           # главная страница
def index():

    print(4)
    return render_template('main.html', title='Главная')

# ------------------------------------------------------------------------


@app.route('/catalog')


def catalog():

    db_sess = db_session.create_session()                                 # каталог
    estates = db_sess.query(Item)
    print(5)
    return render_template('catalog.html', title='Каталог', estates=estates)


# ------------------------------------------------------------------------


@app.route('/usluga/<int:id>')


def building(id):

    print(6)
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        building = db_sess.query(Item).get(id)
        enabled = db_sess.query(Signing).filter(Signing.user_id == current_user.id, Signing.estate_id == id).all()
        if len(enabled) > 0:
            enabled = True
        else:                                                       # верхнее окно сайта
            enabled = False
        images = db_sess.query(Image).filter(Image.estate_id == id).all()
        return render_template('usluga.html', building=building, title=building.name, house_id=id, images=images,
                               enabled=enabled)
    else:
        return redirect('/login')


# ----------------------------------------------------------------------------------------


@app.route('/usluga/sign_for/<int:id>', methods=['GET', 'POST'])
@login_required


def sign_for(id):

    print(7)
    db_sess = db_session.create_session()
    building = db_sess.query(Item).get(id)
    form = SignForm()
    form.name.data = current_user.name
    form.surname.data = current_user.surname
    if form.validate_on_submit():
        signing = Signing(

            name=form.name.data,

            surname=form.surname.data,

            patronymic=form.patronymic.data,

            phone=form.phone.data,                                     # вход в запись

            date=form.date.data,

            user_id=current_user.id,

            estate_id=id
        )
        db_sess.add(signing)
        db_sess.commit()
        return redirect('/index')
    return render_template('sign_for.html', form=form, title='Запись на осмотр')


# --------------------------------------------------------------------------------------


@app.route('/register', methods=['GET', 'POST'])


def reqister():

    print(8)
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,                                        # окно регистрации
                                   message="Такой пользователь уже есть")
        user = User(

            name=form.name.data,

            surname=form.surname.data,

            email=form.email.data,
        )
        user.is_admin = False
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


# -----------------------------------------------------------------------------


@app.route('/login', methods=['GET', 'POST'])


def login():

    print(9)
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):          # ошибка входа
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


# ---------------------------------------------------------------------------------


@app.route('/post_edit')


def post_edit():

    print(10)
    db_sess = db_session.create_session()
    estates = db_sess.query(Item).filter(current_user.id == Item.user_id)
    return render_template('post_edit.html', title='Мои услуги', estates=estates)


@app.route('/usluga_info_edit', methods=['GET', 'POST'])
@login_required


def add_building():

    print(11)
    form = BuildingForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if len(form.tags.data) >= 29 * 3:
            line_tags = form.tags.data[:29 * 3 - 3] + '...'
        else:
            line_tags = form.tags.data + ' ' * (29 * 3 - len(form.tags.data))
        item = Item(
            name=form.name.data,

            about=form.about.data,

            tags=line_tags,

            price=form.price.data,                                              # фигня с услугами

            address=form.address.data,

            image_link=form.image_link.data.split()[0])

        current_user.items.append(item)
        db_sess.merge(current_user)
        db_sess.commit()
        for items in form.image_link.data.split():
            image = Image(
                estate_id=db_sess.query(Item).filter(Item.name == item.name).first().id,
                link=items
            )
            db_sess.add(image)
        db_sess.commit()
        return redirect('/catalog')
    return render_template('usluga_info_edit.html', title='Добавление услуги',
                           form=form)


# ---------------------------------------------------------------------------------------------


@app.route('/usluga_info_edit/<int:id>', methods=['GET', 'POST'])
@login_required


def edit_building(id):

    print(12)
    form = BuildingForm()
    db_sess = db_session.create_session()
    arr = []
    for i in db_sess.query(Image).filter(Image.estate_id == id).all():
        arr.append(i.link)
    images_h = ' '.join(arr)
    if request.method == "GET":
        db_sess = db_session.create_session()
        items = db_sess.query(Item).filter(Item.id == id,
                                           Item.user == current_user
                                           ).first()
        print(items)
        if items:
            form.name.data = items.name
            form.about.data = items.about
            form.tags.data = items.tags
            form.price.data = items.price
            form.address.data = items.address
            form.image_link.data = images_h
            print(items)
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()                         # тоже фигня с услугами
        items = db_sess.query(Item).filter(Item.id == id,
                                           Item.user == current_user
                                           ).first()
        print(len(form.tags.data))
        if len(form.tags.data) >= 29 * 3:
            line_tags = form.tags.data[:29 * 3 - 3] + '...'
        else:
            line_tags = form.tags.data + ' ' * (29 * 3 - len(form.tags.data))
        if items:
            items.name = form.name.data
            items.about = form.about.data
            items.tags = line_tags
            items.price = form.price.data
            items.address = form.address.data
            items.image_link = form.image_link.data.split()[0]
            for item in form.image_link.data.split():
                if item not in images_h:
                    image = Image(
                        estate_id=id,
                        link=item
                    )
                    db_sess.add(image)
            db_sess.commit()
            return redirect('/post_edit')
        else:
            abort(404)

    return render_template('usluga_info_edit.html',
                           title='Редактирование информации о услуге',
                           form=form
                           )


# -----------------------------------------------------------------------------------------------------


@app.route('/usluga_info_delete/<int:id>', methods=['GET', 'POST'])
@login_required


def building_delete(id):

    print(13)
    db_sess = db_session.create_session()
    items = db_sess.query(Item).filter(Item.id == id,
                                       Item.user == current_user             # удалить услугу
                                       ).first()
    if items:
        db_sess.delete(items)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/post_edit')


# -------------------------------------------------------------------------------------------------------


@app.route('/profile', methods=['GET', 'POST'])
@login_required


def profile():

    print(14)
    db_sess = db_session.create_session()
    query = db_sess.query(Signing, Item)
    query = query.join(Item, Item.id == Signing.estate_id)
    query = query.filter(Signing.user_id == current_user.id).all()
    return render_template('profile.html', info=query)


@app.route('/dev')


def dev():

    print(15)
    return render_template('dev.html', title='Разработчикам')


@app.route('/users', methods=['GET', 'POST'])


def users():

    print(16)
    if current_user.is_authenticated:
        if current_user.is_admin:
            db_sess = db_session.create_session()
            query = db_sess.query(User).all()
            return render_template('users.html', title='Пользователи', users=query)
        else:
            return 'Недостаточно прав'
    else:
        return redirect('/login')


@app.route('/user_no_admin/<int:id>', methods=['GET', 'POST'])


def user_admin(id):

    print(17)
    if current_user.is_authenticated:
        if current_user.is_admin:
            db_sess = db_session.create_session()
            query = db_sess.query(User).filter(User.id == id).all()
            for i in query:
                i.is_admin = True
            db_sess.flush()
            db_sess.commit()
            return redirect('/users')
        else:
            return 'Недостаточно прав'
    else:
        return redirect('/login')


@app.route('/user_admin/<int:id>', methods=['GET', 'POST'])


def user_no_admin(id):

    print(18)
    if current_user.is_authenticated:
        if current_user.is_admin:
            db_sess = db_session.create_session()
            query = db_sess.query(User).filter(User.id == id).all()
            for i in query:
                i.is_admin = False
            db_sess.flush()
            db_sess.commit()
            return redirect('/users')
        else:
            return 'Недостаточно прав'
    else:
        return redirect('/login')


@app.route('/signings', methods=['GET', 'POST'])
@login_required


def signings():

    print(19)
    db_sess = db_session.create_session()
    query = db_sess.query(Signing, Item)
    query = query.join(Item, Item.id == Signing.estate_id).all()
    return render_template('signings.html', info=query)


def main():

    print("start")
    db_session.global_init("db/estate.db")
    # db_sess = db_session.create_session()

    app.register_blueprint(blueprint)
    app.run(host='127.0.0.1', port=5000)


def abcf():

    print(20)
    db_sess = db_session.create_session()
    query = db_sess.query(Signing, Item)
    query = query.join(Item, Item.id == Signing.estate_id).all()
    return render_template('signings.html', info=query)


# test
# http://127.0.0.1:5000/


def pusto():

    print(21)

    return ""


def dest():

    print(22)

    return "            "


if __name__ == '__main__':
    main()
