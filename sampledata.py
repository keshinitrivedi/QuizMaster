# Run this in a separate script to add initial users
from pymongo import MongoClient
import bcrypt

client = MongoClient("mongodb://localhost:27017/")
db = client["QuizMasterStreamlit"]
users_collection = db["users"]

users = [
    {"username": "teacher1", "password": bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()), "role": "teacher"},
    {"username": "student1", "password": bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()), "role": "student"},
    {"username": "admin1", "password": bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()), "role": "admin"}
]

users_collection.insert_many(users)