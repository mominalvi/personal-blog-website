import smtplib
from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import os

# Importing necessary libraries and modules for the web application.
# Flask is used for creating the app, and various Flask extensions are used for additional functionality like forms, user authentication, and database operations.


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

# Initializing the Flask app.
app = Flask(__name__)
# Integrating CKEditor into the Flask app.
ckeditor = CKEditor(app)
# Applying Bootstrap 5 to style the app.
Bootstrap5(app)
# Setting up the login manager for user authentication.
login_manager = LoginManager()
login_manager.init_app(app)

# Database Configuration
# Configuring the database with SQLAlchemy. A secret key is generated and the database URI is obtained from environment variables.
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI')
db = SQLAlchemy()
db.init_app(app)


# Database Models
# Defining the BlogPost model for the database. This includes columns for post ID, title, subtitle, date, body, image URL, and relationships with users and comments.
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")


# Defining the User model. This includes user details like email, password, and name. It also establishes relationships with BlogPost and Comment models to represent user's posts and comments.
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


# Defining the Comment model. This includes columns for comment ID, author ID, post ID, and the comment text. It also defines relationships with the User and BlogPost models.
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    comment_author = relationship("User", back_populates="comments")

    # ***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

# Creating all the database tables defined above in the actual database.
with app.app_context():
    db.create_all()


# Configuring Gravatar for user profile pictures. Parameters like size, rating, and default image are set.
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# Function for loading a user given their user ID. Used by Flask-Login to manage user sessions.
@login_manager.user_loader
def load_user(user_id):
    """
        Callback used by Flask-Login to load a user from the user ID stored in the session.
        :param user_id: The user ID stored in the session.
        :return: User object or None.
    """
    return db.session.execute(db.select(User).where(User.id == int(user_id))).scalar()

def admin_only(f):
    """
        Decorator function to restrict access to only the admin.
        Applied to routes that should only be accessible by the admin user.
        :param f: The original function to be decorated.
        :return: Decorated function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return f(*args, **kwargs)
        return abort(403)
    return decorated_function


@app.route('/register', methods=["GET", "POST"])
def register():
    """
        Route to handle user registration.
        Displays the registration form and processes the form submission to register a new user.
        Redirects to the login page on successful registration.
    """
    # makes an instance of the register form
    form = RegisterForm()
    if form.validate_on_submit():
        # error validation, checking if email exists
        email_exists = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if email_exists:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        # secure the users password
        hashed_password = generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=8)
        new_user = User(email=form.email.data, password=hashed_password, name=form.name.data)
        # add user to database
        db.session.add(new_user)
        db.session.commit()
        #login the new user
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """
        Route to handle user login.
        Displays the login form and processes the form submission to log in the user.
        Redirects to the home page on successful login.
    """
    # makes an instance of the login form
    form = LoginForm()
    # the code below validates that the user is entering valid credentials
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user:
            if check_password_hash(pwhash=user.password, password=password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Password incorrect, please try again.")
                return redirect(url_for('login'))
        else:
            flash("that email does not exist, please try again.")
            return redirect(url_for('login'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    """
       Route to handle user logout.
       Logs out the current user and redirects to the home page.
    """
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    """
        Route to display the home page with all blog posts.
        Retrieve posts from the database and renders them on the home page.
    """
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    """
        Route to display a specific blog post.
        Displays the post along with its comments and a form to add a new comment.
        :param post_id: ID of the blog post to display.
    """
    requested_post = db.get_or_404(BlogPost, post_id)
    # makes an instance of the comment form
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Please log in to be able to comment.")
            return redirect(url_for('login'))
        new_comment = Comment(text=form.comment.data, author_id=current_user.id, post_id=requested_post.id)
        # adds user to database
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    """
       Route for the admin to add a new blog post.
       Displays a form for creating a new post and processes the form submission.
    """
    # makes an instance
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        # adds user to database
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    """
        Route for the admin to edit an existing blog post.
        Displays a form pre-filled with the post's data and processes the form submission.
        :param post_id: ID of the blog post to edit.
    """
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    """
        Route for the admin to delete a blog post.
        Deletes the specified post and redirects to the home page.
        :param post_id: ID of the blog post to delete.
    """
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/delete-comment/<int:comment_id>")
@admin_only
def delete_comment(comment_id):
    """
        Route for the admin to delete a comment.
        Deletes the specified comment and redirects to the corresponding blog post page.
        :param comment_id: ID of the comment to delete.
    """
    comment_to_delete = db.get_or_404(Comment, comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    """
        Route to display the 'About' page.
    """
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
        Route to display and process the contact form.
        On POST request, sends an email with the form data.
    """
    if request.method == "POST":
        post = True
        data = request.form
        send_email(name=data['name'], email=data['email'], phone=data['phone'], message=data['message'])
        return render_template("contact.html", message_sent=post)
    return render_template("contact.html")

def send_email(name, email, phone, message):
    """
        Sends an email with the provided contact information and message.
        :param name: Name of the person sending the message.
        :param email: Email address of the sender.
        :param phone: Phone number of the sender.
        :param message: The message content.
    """
    my_email = os.environ.get('FROM_EMAIL')
    password = os.environ.get('MY_PASSWORD')
    to_email = os.environ.get('TO_EMAIL')
    with smtplib.SMTP(host="173.194.193.108", port=587) as connection:
        connection.starttls()
        connection.login(user=my_email, password=password)
        connection.sendmail(from_addr=my_email,
                            to_addrs=to_email,
                            msg="Subject: New Message!\n\n"
                                f"Name: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}".encode('utf-8'))




if __name__ == "__main__":
    app.run(debug=True)
