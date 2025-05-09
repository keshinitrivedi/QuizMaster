import pymongo

MONGODB_URI = "mongodb://localhost:27017/"
client = pymongo.MongoClient(MONGODB_URI)
db = client["QuizMasterStreamlit"]
users_collection = db["users"]
quizzes_collection = db["quizzes"]
results_collection = db["results"]

# Test connection
try:
    client.server_info()
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")