import os
import datetime
import csv
import locale
import sqlite3
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from email_validator import validate_email, EmailNotValidError
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from functions import login_required, apology

# Configure application
app = Flask(__name__)
# email password and username are stored as environment variables per chatGPT advice
email_password = os.getenv("web_app_companies_review_password")
email_username = os.getenv("web_app_companies_review_username")

# create an instance of a bcrypt object
bcrypt = Bcrypt(app)

# Used from CS50's finance problem set - Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Flask mail config
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = email_username
app.config["MAIL_PASSWORD"] = email_password

# create an instance of flask mail object
mail = Mail(app)

# made with help from chatGPT - to enable accurate sorting in accordance with local special characters(like "Ř", "Ž", "Š")
locale.setlocale(locale.LC_ALL, "Czech")


# used from CS50's finance problem set
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


db = SQL("sqlite:///review.db")


@app.route("/")
def index():
    """Show homepage"""
    # get all companies' names for the search bar
    company_names_all = db.execute("SELECT company_name FROM companies")
    company_names = []
    for i in company_names_all:
        company_names.append(i["company_name"])
    # sorting made with help from chatGPT
    company_names = sorted(company_names, key=lambda name: locale.strxfrm(name.lower()))

    # get all the data that is beng shown on the home screen
    reviews = db.execute(
        "SELECT reviews.review_text, reviews.rating, reviews.date_time, companies.company_name, companies.company_type, users.name FROM reviews JOIN companies ON reviews.company_id = companies.id JOIN users ON reviews.user_id = users.id;"
    )
    # sort the data based on time in reverse, so that the most recent comes first
    reviews = sorted(reviews, key=lambda x: x["date_time"], reverse=True)
    return render_template("index.html", reviews=reviews, company_names=company_names)


# login function adapted from CS50's Finance problem set
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("Musíte zadat emailovou adresu")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Musíte zadat heslo")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE email = ?", request.form.get("email")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not bcrypt.check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("Neplatný email nebo heslo")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # added remembering the current users role to enable admin-specific functionality
        session["role"] = rows[0]["role"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# logout function used as in CS50's finance problem set
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# register function adapted from CS50's finance problem set
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("Musíta zadat email")
        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("Musíte zadat heslo")
        # Ensure password confirmation was submited
        if not request.form.get("confirmation"):
            return apology("Musíte zopakovat heslo")
        # Ensure password and confrimation password match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Heslo a opakování se neshodují")
        
        # email validation via addon. Checks the body of the email adress via regex and checks whether the adress provided can receive mail - therefore only valid adresses are permitted.
        # https://pypi.org/project/email-validator/
        try:
            emailinfo = validate_email(
                request.form.get("email"), check_deliverability=True
            )
            email = emailinfo.normalized
        except EmailNotValidError:
            return apology("Tato emailová adresa je neplatná")

        # Register the user into db
        name = request.form.get("name")

        # the role is set through the db by default. The default value is user. Admin has beed added directly through sqlite.
        role = ""
        if request.form.get("register_company") == "on":
            role = "company"
        else:
            role = "user"
        # Password hash - via https://www.geeksforgeeks.org/password-hashing-with-bcrypt-in-flask/
        password = bcrypt.generate_password_hash(request.form.get("password")).decode(
            "utf-8"
        )

        # Try to insert the user.
        try:
            db.execute(
                "INSERT INTO users(email, name, hash, role) VALUES(?, ?, ?, ?)",
                email,
                name,
                password,
                role,
            )
        # If valueError is raised we can infer that the username already exists. sqlite3.IntegrityError added per chatGPT advice after unexpected behaviour. 
        except (ValueError, sqlite3.IntegrityError):
            return apology("Tato emailová adresa je již používána")

        # send mail message via https://flask-mail.readthedocs.io/en/latest/
        msg = Message(
            "Vítejte na stránkách 'Recenze společností'!",
            sender=email_username,
            recipients=[email],
        )
        msg.body = "Právě jste se zaregistrovali na stránku recenze-společností.cz! Jsme rádi, že Vás tu máme."
        mail.send(msg)
        # If all is well, we can return the user to login page
        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/add_company", methods=["GET", "POST"])
@login_required
def add_company():

    if request.method == "POST":
        # error checking
        if (
            not request.form.get("company_name")
            or not request.form.get("company_type")
            or not request.form.get("company_location")
        ):
            return apology("Nebyla vložena požadovaná data")
        if (
            len(request.form.get("company_name")) > 100
            or len(request.form.get("company_type")) > 100
            or len(request.form.get("company_location")) > 100
            or len(request.form.get("company_web")) > 100
            or len(request.form.get("company_adress")) > 100
        ):
            return apology("Příliš obsáhlý vstup")

        # expressing variables
        company_name = request.form.get("company_name")
        company_type = request.form.get("company_type")
        company_location = request.form.get("company_location")
        company_web = ""
        company_adress = ""
        # assigning non-compulsory variables
        if request.form.get("company_web"):
            company_web = request.form.get("company_web")
        if request.form.get("company_adress"):
            company_adress = request.form.get("company_adress")

        # adding a company to the db. If it already exists, it will raise a value error.
        try:
            db.execute(
                "INSERT INTO companies(company_name, company_type, company_location, company_web, company_adress) VALUES(?, ?, ?, ?, ?)",
                company_name,
                company_type,
                company_location,
                company_web,
                company_adress,
            )
        # If valueError is raised we can infer that the company_name already exists.
        except ValueError:
            return apology("Toto jméno společnosti již je používáno")

        # Flashing a message as an confirmation of success
        flash("Společnost byla přidána!")
        # redirecting the user to add a review - ideally to the company he added just now
        return redirect("/add_review")
    else:
        # get company types dynamically from a csv file so that it can be easily changed later
        company_types = []
        # create a list of possible locations - all counties within Czechia
        company_locations = [
            "Hlavní město Praha",
            "Středočeský kraj",
            "Jihočeský kraj",
            "Plzeňský kraj",
            "Karlovarský kraj",
            "Ústecký kraj",
            "Liberecký kraj",
            "Královéhradecký kraj",
            "Pardubický kraj",
            "Kraj Vysočina",
            "Jihomoravský kraj",
            "Zlínský kraj",
            "Olomoucký kraj",
            "Moravskoslezský kraj",
        ]
        with open("company_types.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                company_types.append(row[0])
        # sorting made with help from chatGPT
        company_types = sorted(
            company_types, key=lambda name: locale.strxfrm(name.lower())
        )
        return render_template(
            "add_company.html",
            company_types=company_types,
            company_locations=company_locations,
        )


@app.route("/add_review", methods=["GET", "POST"])
@login_required
def add_review():
    if request.method == "POST":
        # error checking
        if (
            not request.form.get("company_name")
            or not request.form.get("company_rating")
            or not request.form.get("company_review")
        ):
            return apology("Neplatná recenze")
        # get the names of all companies in the db for the searchbar
        company_names_all = db.execute("SELECT company_name FROM companies")
        # make a list of the company names in the db - for easier showing
        company_names = []
        for i in company_names_all:
            company_names.append(i["company_name"])
        # if company does not exist - flash that it does not exist and redirect the user to add_company
        if request.form.get("company_name") not in company_names:
            flash("Neplatné jméno společnosti. Nejdříve přidejte novou společnost.")
            return redirect("/add_company")
        # safeguard
        if len(request.form.get("company_review")) > 1000:
            return apology("Příliš dlouhý text.")

        # expressing variables
        company_name = request.form.get("company_name")
        company_rating = int(request.form.get("company_rating"))
        company_review = request.form.get("company_review")
        company_id = db.execute(
            "SELECT id FROM companies WHERE company_name = ?", company_name
        )
        company_id = company_id[0]["id"]
        user_id = session["user_id"]
        date_time = datetime.datetime.now()

        # inserting a review into the temp_reviews table so that it can be checked by the admin
        db.execute(
            "INSERT INTO temp_reviews (review_text, rating, company_id, user_id, date_time) VALUES (?, ?, ?, ?, ?)",
            company_review,
            company_rating,
            company_id,
            user_id,
            date_time,
        )

        # appending the companies table with current data
        current_company_data = db.execute(
            "SELECT current_score, number_of_reviews, points_total FROM companies WHERE id = ?",
            company_id,
        )
        current_company_rating = float(current_company_data[0]["current_score"])
        current_number_of_reviews = int(current_company_data[0]["number_of_reviews"])
        points_total = int(current_company_data[0]["points_total"])
        new_points_total = points_total + company_rating
        new_number_of_reviews = current_number_of_reviews + 1
        new_company_rating = new_points_total / new_number_of_reviews
        db.execute(
            "UPDATE companies SET number_of_reviews = ?, current_score = ?, points_total = ? WHERE id = ?",
            new_number_of_reviews,
            new_company_rating,
            new_points_total,
            company_id
        )
        
        # get the current users email and send a confirmation email
        user_email = db.execute("SELECT email FROM users WHERE id = ?", user_id)
        msg = Message(
            "Právě jste přidali recenzi na stránce: 'Recenze společností'!",
            sender=email_username,
            recipients=[user_email[0]["email"]],
        )
        msg.body = f"Vaše recenze na firmu: {company_name} byla úspěšně vložena. Text vaší recenze: {company_review}. Vaše hodnocení této firmy je {company_rating} z 5ti. O schválení vaší recenze Vás budeme informovat emailem."
        mail.send(msg)
        # flash confirmation in case of success
        flash(
            "Recenze přidána! O jejím schválení administrátorem Vás budeme informovat emailem."
        )
        # redirect to homepage
        return redirect("/")
    else:
        # get the current list of registered companies to the add_review.html so that the user knows which companies already exist and therefore can be reviewed
        company_names_all = db.execute("SELECT company_name FROM companies")
        company_names = []
        for i in company_names_all:
            company_names.append(i["company_name"])
        # sorting made with help from chatGPT
        company_names = sorted(
            company_names, key=lambda name: locale.strxfrm(name.lower())
        )
        return render_template("add_review.html", company_names=company_names)


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    if request.method == "POST":
        # get all company names for the search algorithm
        company_names_all = db.execute("SELECT company_name FROM companies")
        company_names = []
        for i in company_names_all:
            company_names.append(i["company_name"])
        # error checking
        if not request.form.get("company_name"):
            return apology("Musíte vložit jméno společnosti")

        # case insensitive search algorithm for partial inputs
        we_have_it = False
        company_name_flag = ""
        companies_found_count = 0
        companies_found = []
        searched_name = request.form.get("company_name").lower()
        for i in company_names:
            if searched_name in i.lower():
                we_have_it = True
                company_name_flag = i
                companies_found.append(i)
                companies_found_count += 1

        # if the company is not in the db - a flash message is shown and the user is redirected to adding a company. 
        if we_have_it == False:
            flash("Tato společnost zatím neexistuje. Přidejte ji. Pro přidání nové společnosti se musíte zaregistrovat a přihlásit.")
            return redirect("/add_review")
           

        # if there are more companies that match the (partial) input:
        if companies_found_count > 1:
            company = []
            warning_text = "Takových společností máme v databázi několik. Vyberte si prosím jednu z nich."
            # append all their data to the list
            for i in companies_found:
                temp = db.execute("SELECT * FROM companies WHERE company_name = ?", i)
                if temp:
                    company.extend(temp)
            # and return all of them so the user can choose
            return render_template(
                "reviews.html",
                company=company,
                company_names=company_names,
                warning_text=warning_text,
            )

        # else, if only one company was found: get its' data
        company = db.execute(
            "SELECT * FROM companies WHERE company_name = ?", company_name_flag
        )
        # get its' reviews with associated user
        company_reviews = db.execute(
            "SELECT * FROM reviews JOIN users ON reviews.user_id = users.id WHERE company_id = ?",
            company[0]["id"],
        )
        # and return it
        return render_template(
            "reviews.html",
            company=company,
            company_names=company_names,
            company_reviews=company_reviews,
        )
    else:
        # get all companies' names for the search bar
        company_names_all = db.execute("SELECT company_name FROM companies")
        company_names = []
        for i in company_names_all:
            company_names.append(i["company_name"])
        # sorting made with help from chatGPT
        company_names = sorted(
            company_names, key=lambda name: locale.strxfrm(name.lower())
        )
        return render_template("reviews.html", company_names=company_names)


@app.route("/account")
@login_required
def search():
    # get user id
    user_id = session["user_id"]
    # get information about the user
    user = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    # get all reviews that the user has created and that were checked by the admin
    user_reviews = db.execute(
        "SELECT reviews.review_text, reviews.id, reviews.rating, reviews.date_time, companies.company_name FROM reviews JOIN companies ON reviews.company_id = companies.id WHERE user_id = ?",
        user_id,
    )
    # datetime checking because there shall be a window of only three days for editing a review
    for review in user_reviews:
        review_date_check = review["date_time"]
        review_date_check = datetime.datetime.strptime(
            review_date_check, "%Y-%m-%d %H:%M:%S"
        )
        # based on the check, a new key:value pair is added to the data that the html gets. Based on this, changing a specific review is either allowed or not.
        if (datetime.datetime.now() - datetime.timedelta(days=3)) > review_date_check:
            review["state"] = "disabled"
        else:
            review["state"] = "enabled"
    # sorting the reviews based on the date and time in reverse so that the most recent reviews come first
    user_reviews = sorted(user_reviews, key=lambda x: x["date_time"], reverse=True)
    return render_template("account.html", user=user, user_reviews=user_reviews)


@app.route("/cookies_policy")
def cookies_policy():
    return render_template("cookies_policy.html")

# just plain html showing placeholder cookie policy


@app.route("/privacy_policy")
def privacy_policy():
    return render_template("privacy_policy.html")

# just plain html showing placeholder privacy policy

@app.route("/terms_conditions")
def terms_conditions():
    return render_template("terms_conditions.html")

# just plain html showing placeholder terms and conditions

@app.route("/change_email", methods=["GET", "POST"])
@login_required
def change_email():
    if request.method == "POST":
        # general error checking - all fields must be filler
        if (
            not request.form.get("current_email")
            or not request.form.get("password")
            or not request.form.get("new_email")
            or not request.form.get("new_email_again")
        ):
            return apology("Chybějící údaje")
        # len check - protection 
        if (
            len(request.form.get("current_email")) > 100
            or len(request.form.get("password")) > 100
            or len(request.form.get("new_email")) > 100
            or len(request.form.get("new_email_again")) > 100
        ):
            return apology("Neplatné údaje")
        # new email must be different from the old one
        if request.form.get("current_email") == request.form.get("new_email"):
            return apology("Nový email nemůže být stejný jako ten původní")
        # new email must be the same as its' confirmation
        if request.form.get("new_email") != request.form.get("new_email_again"):
            return apology("Zadané nové emaily se neshodují")

        # get current user ID
        user_id = session["user_id"]

        # compare the inputed current email adress with the db for the current user.
        # without this it is possible to change an email with another users email and password
        current_user_current_email_check = db.execute(
            "SELECT email FROM users WHERE id = ?", user_id
        )
        if current_user_current_email_check[0]["email"] != request.form.get(
            "current_email"
        ):
            return apology("Současná emailová adresa je neplatná")
        # look in the db for the inputed user
        validation = db.execute("SELECT * FROM users WHERE id = ?", user_id)

        # Ensure username exists and password is correct
        if len(validation) != 1 or not bcrypt.check_password_hash(
            validation[0]["hash"], request.form.get("password")
        ):
            return apology("Neplatný email nebo heslo")

        # is the new email adress legit? The same validation as in /register
        try:
            emailinfo = validate_email(
                request.form.get("new_email"), check_deliverability=True
            )
            email = emailinfo.normalized
        except EmailNotValidError:
            return apology("Nová emailová adresa je neplatná")

        # Try to change the email value of the user.

        try:
            db.execute("UPDATE users SET email = ? WHERE id = ?", email, user_id)
        # If valueError is raised we can infer that the email adress already exists. sqlite3.IntegrityError added per chatGPT advice after unexpected behaviour.
        except (ValueError, sqlite3.IntegrityError):
            return apology("Nová emailová adresa je již používána")

        # email confirmation for the user sent to both the new and the old emails
        msg = Message(
            "Na stránkách recenze-společností jste změnili svoji emailovou adresu",
            sender=email_username,
            recipients=[email, request.form.get("current_email")],
        )
        msg.body = f"Právě jste změnili svou emailovou adresu na stránce: recenze společností. Vaše původní adresa: {request.form.get("current_email")}, vaše nová adresa: {email}"
        mail.send(msg)

        flash("E-mailová adresa změněna!")
        return redirect("/account")
    else:
        return render_template("email_change.html")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        # general error checking - all fields must be filler
        if (
            not request.form.get("email")
            or not request.form.get("password")
            or not request.form.get("new_password")
            or not request.form.get("new_password_again")
        ):
            return apology("Chybějící údaje")

        # len check - just in case
        if (
            len(request.form.get("email")) > 100
            or len(request.form.get("password")) > 100
            or len(request.form.get("new_password")) > 100
            or len(request.form.get("new_password_again")) > 100
        ):
            return apology("Neplatné údaje")

        # password repeat check
        if request.form.get("new_password") != request.form.get("new_password_again"):
            return apology("Nové heslo se neshoduje s jeho opakováním")
        # get current user id
        user_id = session["user_id"]
        # new password must be different than the old one and general password and email check
        password_validation = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        if request.form.get("email") != password_validation[0]["email"]:
            return apology("Neplatný email")
        if not bcrypt.check_password_hash(
            password_validation[0]["hash"], request.form.get("password")
        ):
            return apology("Zadané heslo je neplatné")
        if bcrypt.check_password_hash(
            password_validation[0]["hash"], request.form.get("new_password")
        ):
            return apology("Nové heslo se musí lišit od toho původního")

        # hashing the new password
        new_hash = bcrypt.generate_password_hash(
            request.form.get("new_password")
        ).decode("utf-8")
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, user_id)

        # confirmation email
        user_email = db.execute("SELECT email FROM users WHERE id = ?", user_id)

        msg = Message(
            "Na stránkách recenze-společností jste změnili své heslo",
            sender=email_username,
            recipients=[user_email[0]["email"]],
        )
        msg.body = (
            f"Právě jste změnili svoje přístupové heslo na stránce recenze-společností."
        )
        mail.send(msg)

        flash("Heslo bylo změněno")
        return redirect("/account")
    else:
        return render_template("password_change.html")


@app.route("/edit_review_passthrough", methods=["POST"])
@login_required
def edit_review_passtrough():
    """Error checking and passing it through so that this function does not go through GET"""
    # datetime checking because there shall be a window of only three days for editing a review
    review = db.execute(
        "SELECT date_time FROM reviews WHERE id = ?",
        int(request.form.get("edit_review")),
    )
    review = review[0]["date_time"]
    review = datetime.datetime.strptime(review, "%Y-%m-%d %H:%M:%S")
    if (datetime.datetime.now() - datetime.timedelta(days=3)) > review:
        return apology(
            "Toto hodnocení již nemůžete upravit. Doba na úpravu hodnocení jsou tři(3) dny."
        )
    # get the current contents of the review and serve it to the user so that he can change it
    review_id = request.form.get("edit_review")
    review_content = db.execute(
        "SELECT reviews.id, reviews.review_text, reviews.rating, reviews.date_time, companies.company_name FROM reviews JOIN companies ON reviews.company_id = companies.id WHERE reviews.id = ?",
        review_id,
    )
    # the current review lenght for the character counter's initial value
    length = len(review_content[0]["review_text"])
    return render_template(
        "edit_review.html", review_content=review_content, length=length
    )


@app.route("/edit_review", methods=["POST"])
@login_required
def edit_review():
    # error checking
    if (
        not request.form.get("company_rating")
        or not request.form.get("company_review")
        or not request.form.get("review_id")
        or not request.form.get("company_name")
    ):
        return apology("Chybně zadané údaje.")
    
    # getting the updated values
    new_date_time = datetime.datetime.now()
    new_rating = int(request.form.get("company_rating"))
    new_review = request.form.get("company_review")
    review_id = request.form.get("review_id")
    
    # updating the review in the database
    db.execute(
        "UPDATE reviews SET review_text = ?, rating = ?, date_time = ? WHERE id = ?",
        new_review,
        new_rating,
        new_date_time,
        review_id,
    )

    # send a confirmation message to the user
    user_id = db.execute("SELECT user_id FROM reviews WHERE id = ?", review_id)
    user_email = db.execute(
        "SELECT email FROM users WHERE id = ?", int(user_id[0]["user_id"])
    )
    msg = Message(
        "Na stránkách recenze-společností jste upravili jedno z Vašich hodnocení",
        sender=email_username,
        recipients=[user_email[0]["email"]],
    )
    msg.body = f"Právě jste upravili své hodnocení společnost: {request.form.get("company_name")}. Text vašeho nového hodnocení: {new_review}. Vaše nové hodnocení společnosti: {new_rating} z 5ti."
    mail.send(msg)

    flash("Recenze byla změněna!")
    return redirect("/account")


@app.route("/delete_review_passthrough", methods=["POST"])
@login_required
def delete_review_passtrough():
    """Get the data concerned and pass it through to /delete_review so that it does not go through GET"""
    review_id = request.form.get("delete_review")
    review_data = db.execute(
        "SELECT reviews.id, reviews.review_text, reviews.rating, reviews.company_id, reviews.date_time, companies.company_name FROM reviews JOIN companies ON reviews.company_id = companies.id WHERE reviews.id = ?",
        review_id,
    )
    return render_template("delete_review.html", review_data=review_data)


@app.route("/delete_review", methods=["POST"])
@login_required
def delete_review():
    # error checking
    if not request.form.get("confirmation_check") or not request.form.get(
        "delete_review_id"
    ):
        return apology("Neplatně zadané údaje")
    # get the data concerning the review to delete
    review_to_be_deleted_id = request.form.get("delete_review_id")
    review_to_be_deleted = db.execute(
        "SELECT review_text, rating, company_id, date_time FROM reviews WHERE id = ?",
        review_to_be_deleted_id,
    )
    # anonymous user for this purpose
    user_id = 5
    review_text = review_to_be_deleted[0]["review_text"]
    rating = int(review_to_be_deleted[0]["rating"])
    company_id = int(review_to_be_deleted[0]["company_id"])
    date_time = review_to_be_deleted[0]["date_time"]

    # get the user id from the review before it is changed
    user_id = db.execute(
        "SELECT user_id FROM reviews WHERE id = ?", int(review_to_be_deleted_id)
    )
    user_email = db.execute(
        "SELECT email FROM users WHERE id = ?", user_id[0]["user_id"]
    )
    company_name = db.execute(
        "SELECT company_name FROM companies WHERE id = ?", company_id
    )

    # email confirmation
    msg = Message(
        "Na stránkách recenze-společností jste smazali jedno z Vašich hodnocení",
        sender=email_username,
        recipients=[user_email[0]["email"]],
    )
    msg.body = f"Právě jste smazali své hodnocení společnost: {company_name[0]["company_name"]}. Text vašeho nového hodnocení zůstane na stránce recenze-společností. Jakákoli jeho spojitost s vaší osobou bude smazána."
    mail.send(msg)

    # put everything into temp_reviews table, so that the admin can potentially anonymize the contents of the review and then put it back into the main reviews table
    db.execute(
        "INSERT INTO temp_reviews (review_text, rating, company_id, user_id, date_time) VALUES (?, ?, ?, ?, ?)",
        review_text,
        rating,
        company_id,
        user_id,
        date_time,
    )
    # delete from reviews table the particular review the user selected - it will be put back later and anonymous
    db.execute("DELETE FROM reviews WHERE id = ?", review_to_be_deleted_id)
    flash("Vaše spojení s touto recenzí bylo smazáno!")
    return redirect("/account")


@app.route("/user_data", methods=["POST"])
@login_required
def user_data():
    """
    This would allow users to ask for the copy of the data that has beec collected.
    So far this only sends email to the user with the confirmation of the request being made.
    It also sends an email to the admin with the information that this request was made and he has to react.
    No automatic data collection was implemented yet.
    """
    # error checking
    if not request.form.get("get_data_copy"):
        return apology("Chybný vstup")

    # get user email
    user_id = int(request.form.get("get_data_copy"))
    user_email = db.execute("SELECT email FROM users WHERE id = ?", user_id)
    # send confirmation email to user
    msg = Message(
        "Na stránkách recenze-společností jste zažádal/a o kopii Vašich dat",
        sender=email_username,
        recipients=[user_email[0]["email"]],
    )
    msg.body = f"Právě jste na stránkách recenze-společností zažádal/a o kopii vašich uživatelských dat. Kopie vašich dat bude zaslána na Vaši emailovou adresu do 30ti dnů. S pozdravem, tým Recenze-společností."
    mail.send(msg)

    # get admin email
    admin_email = db.execute("SELECT email FROM users WHERE role = 'admin'")
    # send email to admin - so that he takes care of it
    msg = Message(
        "Žádost o kopii uživatelských dat",
        sender=email_username,
        recipients=[admin_email[0]["email"]],
    )
    msg.body = f"Uživatel s emailovou adresou: {user_email[0]["email"]} s id: {user_id} právě požádal o kopii svých uživatelských dat. Na splnění jeho požadavku máte 30 dnů."
    mail.send(msg)
    # confirmation flash
    flash(
        "Žádost o kopii Vašich dat byla odeslána. Kopii Vašich dat obdržíte do 30ti dnů!"
    )

    return redirect("/account")


@app.route("/delete_account", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "POST":
        # error checking. The user has to confirm that he agrees with the conditions of the account deletion.
        if not request.form.get("confirmation_check"):
            return apology("Chybně zadaná data. Musíte souhlasit s podmínkami.")
        user_id = session["user_id"]
        # get all of the users reviews and their ids.
        all_review_ids = db.execute("SELECT id FROM reviews WHERE user_id = ?", user_id)
        all_reviews_to_anonymize = db.execute(
            "SELECT review_text, rating, company_id, date_time FROM reviews WHERE user_id = ?",
            user_id,
        )

        # copy all review content to temp_reviews
        for i, review in enumerate(range(len(all_reviews_to_anonymize))):
            user_id_copy = 5
            db.execute(
                "INSERT INTO temp_reviews (review_text, rating, company_id, user_id, date_time) VALUES (?, ?, ?, ?, ?)",
                all_reviews_to_anonymize[i]["review_text"],
                int(all_reviews_to_anonymize[i]["rating"]),
                int(all_reviews_to_anonymize[i]["company_id"]),
                user_id_copy,
                all_reviews_to_anonymize[i]["date_time"],
            )

        # delete all user reviews from reviews
        for id in all_review_ids:
            db.execute("DELETE FROM reviews WHERE id = ?", id["id"])

        # get user email
        user_email = db.execute("SELECT email FROM users WHERE id = ?", user_id)
        # send confirmation email
        msg = Message(
            "Účet smazán", sender=email_username, recipients=[user_email[0]["email"]]
        )
        msg.body = f"Váš uživatelský účet na stránkách recenze-společností byl smazán."
        mail.send(msg)

        # log user out
        session.clear()
        # delete user from users
        db.execute("DELETE FROM users WHERE id = ?", user_id)

        # redirect the user to the main page and flash confirmation.
        flash("Uživatelský účet byl smazán.")
        return redirect("/")
    else:
        return render_template("delete_account.html")


"""ADMIN FUNCTIONS"""


@app.route("/admin_index", methods=["GET"])
@login_required
def admin_index():
    # error checking
    user_identity = db.execute("SELECT id FROM users WHERE role = 'admin'")
    user_id = session["user_id"]
    
    # check whether the user accessing the admin console is authorised to do so
    if user_id != user_identity[0]["id"]:
        return apology("Nepovolený přístup")
    
    # get all the reviews to be checked and/or anonymized
    reviews_to_check = db.execute("SELECT * FROM temp_reviews;")
    # add a lenght parameter for the character count initial value
    for review in reviews_to_check:
        length = len(review["review_text"])
        review["review_length"] = length
        
    # get all reviews sorted by time in reverse order so that there is an easy way to delete them later if they do not confirm to the terms and conditions.
    all_reviews = db.execute("SELECT * FROM reviews")
    all_reviews = sorted(all_reviews, key=lambda x: x["date_time"], reverse=True)
    return render_template("admin_index.html", reviews_to_check=reviews_to_check, all_reviews=all_reviews)


@app.route("/admin_anonymize", methods=["POST"])
@login_required
def admin_company():
    """
    Manages output from the admin console for anonymization. 
    """
    # error checking
    if (
        not request.form.get("review_id")
        or not request.form.get("review_text")
        or not request.form.get("review_rating")
        or not request.form.get("company_id")
        or not request.form.get("user_id")
        or not request.form.get("date_time")
    ):
        return apology("Chybí vstupní data")
    # get data
    review_id_to_delete = request.form.get("review_id")
    review_text = request.form.get("review_text")
    review_rating = request.form.get("review_rating")
    review_company_id = request.form.get("company_id")
    review_user_id = request.form.get("user_id")
    review_date_time = request.form.get("date_time")
    # write the review into reviews table
    db.execute(
        "INSERT INTO reviews (review_text, rating, company_id, user_id, date_time) VALUES (?, ?, ?, ?, ?)",
        review_text,
        review_rating,
        review_company_id,
        review_user_id,
        review_date_time,
    )

    # remove the review from temp_reviews
    db.execute("DELETE FROM temp_reviews WHERE id = ?", review_id_to_delete)

    flash(
        f"Recenze id: {review_id_to_delete} s textem {review_text} byla úspěšně přesunuta do tabulky reviews."
    )
    return redirect("/admin_index")


@app.route("/admin_allow", methods=["POST"])
@login_required
def admin_review():
    """Manages output from the admin console for checking a review of as acceptable"""
    # error checking
    if (
        not request.form.get("review_id")
        or not request.form.get("review_text")
        or not request.form.get("review_rating")
        or not request.form.get("company_id")
        or not request.form.get("user_id")
        or not request.form.get("date_time")
    ):
        return apology("Chybí vstupní data")

    # get data
    review_id_to_delete = request.form.get("review_id")
    review_text = request.form.get("review_text")
    review_rating = request.form.get("review_rating")
    review_company_id = request.form.get("company_id")
    review_user_id = request.form.get("user_id")
    review_date_time = request.form.get("date_time")
    # write the review into reviews table
    db.execute(
        "INSERT INTO reviews (review_text, rating, company_id, user_id, date_time) VALUES (?, ?, ?, ?, ?)",
        review_text,
        review_rating,
        review_company_id,
        review_user_id,
        review_date_time,
    )

    # remove the review from temp_reviews
    db.execute("DELETE FROM temp_reviews WHERE id = ?", review_id_to_delete)

    # get user email
    user_email = db.execute("SELECT email FROM users WHERE id = ?", review_user_id)
    # send confirmation email to user
    msg = Message(
        "Vaše recenze na stránkách Recenze-společnosti byla schválena",
        sender=email_username,
        recipients=[user_email[0]["email"]],
    )
    msg.body = f"Vámi přidaná recenze na stránkách Recenze-společností byla právě schválena administrátorem a byla přidána mezi ostatní recenze. tým Recenze-společností."
    mail.send(msg)

    flash(
        f"Recenze id: {review_id_to_delete} s textem {review_text} byla úspěšně přesunuta do tabulky reviews."
    )
    return redirect("/admin_index")


@app.route("/admin_delete", methods=["POST"])
@login_required
def admin_deleted():
    """Output from the admin console when the admin decides to delete a review."""
    # error checking
    if (
        not request.form.get("review_id")
        or not request.form.get("review_text")
        or not request.form.get("review_rating")
        or not request.form.get("company_id")
        or not request.form.get("user_id")
        or not request.form.get("date_time")
    ):
        return apology("Chybí vstupní data")

    # get data
    review_id_to_delete = request.form.get("review_id")
    review_text = request.form.get("review_text")
    review_rating = request.form.get("review_rating")
    review_company_id = request.form.get("company_id")
    review_user_id = request.form.get("user_id")
    review_date_time = request.form.get("date_time")

    # get user email
    user_email = db.execute("SELECT email FROM users WHERE id = ?", review_user_id)
    # send confirmation email to user
    msg = Message(
        "Vaše recenze na stránkách Recenze-společnosti byla zamítnuta",
        sender=email_username,
        recipients=[user_email[0]["email"]],
    )
    msg.body = f"Vámi přidaná recenze na stránkách Recenze-společností byla administrátorem zamítnuta. Vaše recenze bohužel není v souladu s našimi uživatelskými podmínkami. Podmínky můžete nalézt na adrese: {'127.0.0.1:5000/terms_conditions'}. Tým Recenze-společností."
    mail.send(msg)

    # remove the review from temp_reviews
    db.execute("DELETE FROM temp_reviews WHERE id = ?", review_id_to_delete)

    flash(f"Recenze id: {review_id_to_delete} z tabulky temp_reviews s textem {review_text} byla smazána.")
    return redirect("/admin_index")


@app.route("/admin_delete_older", methods=["POST"])
@login_required
def admin_deleted_older():
    """Output from the admin console when the admin decides to delete an older review that has already been approved."""
    # error checking
    if (
        not request.form.get("review_id")
        or not request.form.get("review_text")
        or not request.form.get("review_rating")
        or not request.form.get("company_id")
        or not request.form.get("user_id")
        or not request.form.get("date_time")
    ):
        return apology("Chybí vstupní data")

    # get data
    review_id_to_delete = request.form.get("review_id")
    review_text = request.form.get("review_text")
    review_rating = request.form.get("review_rating")
    review_company_id = request.form.get("company_id")
    review_user_id = request.form.get("user_id")
    review_date_time = request.form.get("date_time")

    # get user email
    user_email = db.execute("SELECT email FROM users WHERE id = ?", review_user_id)
    # send confirmation email to user
    msg = Message(
        "Vaše recenze na stránkách Recenze-společnosti byla smazána",
        sender=email_username,
        recipients=[user_email[0]["email"]],
    )
    msg.body = f"Vámi přidaná recenze na stránkách Recenze-společností byla administrátorem smazána. Vaše recenze bohužel není v souladu s našimi uživatelskými podmínkami. Podmínky můžete nalézt na adrese: {'127.0.0.1:5000/terms_conditions'}. Tým Recenze-společností."
    mail.send(msg)

    # remove the review from temp_reviews
    db.execute("DELETE FROM reviews WHERE id = ?", review_id_to_delete)

    flash(f"Recenze id: {review_id_to_delete} z tabulky reviews, s textem {review_text} byla smazána.")
    return redirect("/admin_index")
