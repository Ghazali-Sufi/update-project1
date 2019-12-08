import requests
import os

from flask import Flask, session, render_template, request, redirect, flash, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# # Check for environment variable
# if not os.getenv("DATABASE_URL"):
#     raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine('postgres://uzvefitabhvrhp:b85137d2b0792a5ef233fe84ec66d7bb484170acd32d145c84fcb55176bd9591@ec2-174-129-252-255.compute-1.amazonaws.com:5432/dfdb5v2t94nlp4')
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template ("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
	# if request.method == "GET":
	# 	return ("please submit the form instead")
	username = request.form.get("new_username")
	password = request.form.get("new_password")
	email = request.form.get("email")

	if request.method =="POST":
		if db.execute("select * from users where user=:user", {"user":username}).rowcount==1:
			return render_template ("signup.html", message="Username was taken")


		elif db.execute("select * from users where email=:email", {"email":email}).rowcount==1:
			return render_template ("signup.html", message="Email  was taken")
		else:
			db.execute("insert into users(username, password, email) values (:username, :password, :email)",
			{"username": username, "password": password, "email": email})
			db.commit()
			session['username'] = username
			session['logged'] = True


			return redirect("/search", username=username)

	return render_template ("signup.html")


@app.route("/login", methods=["POST", "GET"])
def login():
	username = request.form.get('username')
	password = request.form.get('password')
	message = "Welcome You are logged in"
	if request.method=="POST":
		if db.execute("SELECT * from users where username = :username AND password =:password", {"username":username, "password":password}).rowcount==1:
			session['username'] = username
			session['logged']=True
			return render_template("search.html", username=session['username'] , message= message)
			# return redirect("search")
		else:
			return "incorrect username or password"

	return render_template('login.html')




@app.route('/search', methods=['GET','POST'])
def search():
	if request.method == "POST":
		searchQuery = request.form.get("searchQuery")
		session['searchedFor'] = searchQuery
		searchResult = db.execute("SELECT isbn, author, title FROM books WHERE isbn iLIKE '%"+searchQuery+"%' OR author iLIKE '%"+searchQuery+"%' OR title iLIKE '%"+searchQuery+"%'").fetchall()
		print("searchQuery")

		session["books"] = []
		noResult = db.execute("SELECT isbn, author, title FROM books WHERE isbn iLIKE '%"+searchQuery+"%' OR author iLIKE '%"+searchQuery+"%' OR title iLIKE '%"+searchQuery+"%'")
		if noResult.rowcount==0:
			message = "No result was found"
			return render_template("results.html", message = message)
		for row in searchResult:
			book = dict()
			book["isbn"] = row[0]
			book["author"] = row[1]
			book["title"]  = row[2]

			session["books"].append(book)
		return render_template("results.html", username=session['username'], searchedFor=searchQuery, books=session["books"])

	return render_template('search.html', username=session['username'])



@app.route("/book/<isbn>")
def book(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    book_id = db.execute("SELECT book_id FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    session['book_id'] = book_id
    if session['username'] is None:
        return render_template("login.html", message="You loggin  first!!")
        if book is None:
            return render_template("error.html", message="book does not exist")

    # Processing the json data
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "BOEcczsw3RDsqb68oFERw", "isbns": book.isbn}).json()["books"][0]
    ratings_count = res["ratings_count"]
    average_rating = res["average_rating"]

    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.book_id}).fetchall()
    users = []
    for review in reviews:
        username = session["username"]
        users.append((username, review))

    return render_template("book.html", book=book, users=users,
                           ratings_count=ratings_count, average_rating=average_rating, username=session["username"])

#Page for Reviewing the Books
@app.route('/review', methods=['GET','POST'])
def review():
    if request.method == "POST":
        username = session["username"]
        user_id = db.execute("SELECT user_id FROM users WHERE username = :username", {"username": username}).fetchone()
        book_id = session["book_id"]
        user_id = user_id[0]
        book_id = book_id[0]
        ratingg = request.form.get("rating")
        rating = int(ratingg)
        comment = request.form.get("comment")

        if db.execute("SELECT * FROM reviews WHERE user_id = user_id AND book_id = book_id").rowcount == 1:
            db.execute(
                "UPDATE reviews SET comment = :comment, rating = :rating WHERE user_id = :user_id AND book_id = :book_id",
                {"comment": comment, "rating": rating, "user_id": user_id, "book_id": book_id})
            db.commit()
            return render_template('error.html', message='Your changed your review, update completed, please go back')

        else:
            db.execute("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                       {"user_id": user_id,
                        "book_id": book_id,
                        "comment": comment,
                        "rating": rating})
        db.commit()
        return render_template('error.html', message='You submitted your review, please go back')
    return response


# Page for the website's API
@app.route("/api/<ISBN>", methods=["GET"])
def api(ISBN):
    book = db.execute("SELECT * FROM books WHERE isbn = :ISBN", {"ISBN": ISBN}).fetchone()
    if book is None:
        return render_template("error.html", error_message="We got an invalid ISBN. "
                                                           "Please check for the errors and try again.")
    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
    count = 0
    rating = 0
    for review in reviews:
        count += 1
        rating += review.rating
    if count:
        average_rating = rating / count
    else:
        average_rating = 0

    return jsonify(
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
        review_count=count,
        average_score=average_rating
    )

@app.route("/logout")
def logout():
    flash ("Hello, logout!!")

    session['logged'] = False
    return render_template("index.html")


#





#     Select username, password from users where username = :username AND password=:password},{:username=username, }


# https://github.com/otherbit/libros
