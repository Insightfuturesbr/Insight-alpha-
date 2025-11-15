from mongodb import db

users = db["users"]

# Insert one user
users.insert_one({"name": "Charlie", "age": 35})

# Fetch all users
all_users = list(users.find())

print("Users:", all_users)