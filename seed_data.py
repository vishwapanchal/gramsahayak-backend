import asyncio
import random
from app.database import db
from app.security import get_password_hash

# --- Data Arrays for Random Generation ---
first_names_male = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya", "Manav", "Deepak", "Ramesh", "Suresh", "Vikram", "Rahul", "Ankit", "Pankaj", "Amit", "Sumit", "Rohan", "Karan", "Nikhil", "Raj"]
first_names_female = ["Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Anjali", "Neha", "Pooja", "Sneha", "Riya", "Priya", "Meera", "Kavita", "Sunita", "Anita", "Deepa", "Rekha", "Suman", "Kiran", "Laxmi", "Nisha", "Rani", "Asha", "Usha", "Vani"]
last_names = ["Kumar", "Sharma", "Singh", "Patel", "Verma", "Gupta", "Reddy", "Rao", "Nair", "Iyer", "Gowda", "Yadav", "Das", "Mishra", "Jha", "Chauhan", "Mehta", "Jain", "Saxena", "Pandey"]

villages = ["Rampur", "Lakhanpur", "Sonpur", "Madhopur", "Kishanpur", "Shantipur", "Govindpur", "Chandpur"]
taluks = ["Rampur Taluk", "Gandhinagar", "Varanasi North", "Thane West", "Patna Rural"]
districts = ["Varanasi", "Ahmedabad", "Pune", "Patna", "Jaipur", "Lucknow", "Bangalore Rural"]
states = ["Uttar Pradesh", "Gujarat", "Maharashtra", "Bihar", "Rajasthan", "Karnataka"]

def generate_phone(index):
    # Generates unique 10 digit number starting with 9
    # Base: 9000000000 + index
    return str(9000000000 + index)

async def seed_large_data():
    print("--- STARTING LARGE DATASET RESEED ---")
    
    # 1. Clear ALL existing data
    print("Clearing old users...")
    await db.villagers.delete_many({})
    await db.contractors.delete_many({})
    await db.government_officials.delete_many({})
    print("All collections cleared.")

    # 2. Setup Common Password
    COMMON_PASSWORD = "password123"
    hashed_pwd = get_password_hash(COMMON_PASSWORD)
    
    users_to_add = []

    # --- 3. Generate 50 Villagers ---
    print("Generating 50 Villagers...")
    villagers = []
    for i in range(50):
        # Randomly pick gender and name
        if random.choice([True, False]):
            name = f"{random.choice(first_names_male)} {random.choice(last_names)}"
            gender = "Male"
        else:
            name = f"{random.choice(first_names_female)} {random.choice(last_names)}"
            gender = "Female"
            
        v = {
            "name": name,
            "gender": gender,
            "age": random.randint(18, 70),
            "email": f"villager{i+1}@gram.com",
            "phone_number": generate_phone(i), # 9000000000 to 9000000049
            "village_name": random.choice(villages),
            "taluk": random.choice(taluks),
            "district": random.choice(districts),
            "state": random.choice(states),
            "password": hashed_pwd,
            "role": "villager"
        }
        villagers.append(v)
    
    if villagers:
        await db.villagers.insert_many(villagers)
        print(">> Added 50 Villagers.")

    # --- 4. Generate 5 Contractors ---
    print("Generating 5 Contractors...")
    contractors = []
    contractor_names = ["Ramesh Infra", "Suresh Builds", "Ganga Constructions", "Vikas Developers", "Hind Engineering"]
    
    for i in range(5):
        c = {
            "name": contractor_names[i],
            "email": f"contractor{i+1}@infra.com",
            "phone_number": str(8000000000 + i),
            "contractor_id": f"CNT{str(i+1).zfill(3)}", # CNT001 to CNT005
            "password": hashed_pwd,
            "role": "contractor"
        }
        contractors.append(c)

    if contractors:
        await db.contractors.insert_many(contractors)
        print(">> Added 5 Contractors.")

    # --- 5. Generate 10 Government Officials ---
    print("Generating 10 Officials...")
    officials = []
    
    for i in range(10):
        name = f"Officer {random.choice(first_names_male)} {random.choice(last_names)}"
        o = {
            "name": name,
            "email": f"officer{i+1}@gov.in",
            "government_id": f"GOV{str(i+1).zfill(3)}", # GOV001 to GOV010
            "password": hashed_pwd,
            "role": "government_official"
        }
        officials.append(o)

    if officials:
        await db.government_officials.insert_many(officials)
        print(">> Added 10 Officials.")

if __name__ == "__main__":
    asyncio.run(seed_large_data())
    print("--- RESEED COMPLETE ---")
    print("Villager Logins: 9000000000 to 9000000049")
    print("Contractor IDs: CNT001 to CNT005")
    print("Official IDs: GOV001 to GOV010")
    print("Common Password: password123")
