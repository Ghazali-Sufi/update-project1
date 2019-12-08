
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine('postgres://uzvefitabhvrhp:b85137d2b0792a5ef233fe84ec66d7bb484170acd32d145c84fcb55176bd9591@ec2-174-129-252-255.compute-1.amazonaws.com:5432/dfdb5v2t94nlp4')

db = scoped_session(sessionmaker(bind=engine))


def main():
    f = open("books.csv", "r")  # needs to be opened during reading csv
    reader = csv.reader(f)# wuxuu soo aqrinaa fileka la furay
    next(reader)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
               {"isbn": isbn, "title": title, "author": author, "year": year})
        db.commit()
        print(f"Added book with ISBN: {isbn} Title: {title}  Author: {author}  Year: {year}")


if __name__ == '__main__':
    main()