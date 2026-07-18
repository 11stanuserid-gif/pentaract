# =============================================================================
# IDENTITY GENERATION ENGINE
# Generates unique synthetic Indian identities for each test account
# =============================================================================

import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Set


class IdentityGenerator:
    """Generates unique synthetic identities with Indian demographic data."""

    # Indian first names (male & female)
    FIRST_NAMES_MALE = [
        "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Arnav",
        "Ayaan", "Krishna", "Ishaan", "Rohan", "Karan", "Raj", "Vikram",
        "Rahul", "Amit", "Nikhil", "Siddharth", "Rishi", "Dev", "Kabir",
        "Aryan", "Reyansh", "Shaurya", "Mohammed", "Ali", "Farhan",
        "Imran", "Zayed", "Rehan", "Akash", "Vijay", "Sunil", "Manish",
        "Deepak", "Rakesh", "Suresh", "Gaurav", "Ankit", "Praveen",
        "Sandeep", "Naveen", "Pankaj", "Ravi", "Shiva", "Ganesh",
    ]

    FIRST_NAMES_FEMALE = [
        "Aaradhya", "Diya", "Saanvi", "Ananya", "Navya", "Myra", "Pari",
        "Kavya", "Sara", "Ira", "Neha", "Priya", "Sneha", "Pooja",
        "Riya", "Tanya", "Anika", "Zara", "Ishita", "Meera", "Nisha",
        "Simran", "Divya", "Shreya", "Fatima", "Ayesha", "Zainab",
        "Maryam", "Hafsa", "Khadija", "Aditi", "Isha", "Sonia",
        "Kavita", "Anjali", "Sunita", "Rekha", "Madhuri", "Priyanka",
        "Deepika", "Katrina", "Alia", "Shraddha", "Kangana", "Sonam",
    ]

    LAST_NAMES = [
        "Sharma", "Kumar", "Singh", "Patel", "Gupta", "Reddy", "Nair",
        "Iyer", "Joshi", "Mehta", "Desai", "Shah", "Verma", "Rao",
        "Malhotra", "Chopra", "Banerjee", "Das", "Mishra", "Agarwal",
        "Yadav", "Thakur", "Pandey", "Tiwari", "Bhat", "Menon",
        "Pillai", "Naik", "Kamat", "Shetty", "Kapoor", "Khanna",
        "Chauhan", "Rajput", "Bajaj", "Srinivasan", "Murthy", "Kulkarni",
        "Deshpande", "Chakraborty", "Mukherjee", "Bhattacharya",
    ]

    # Indian cities with lat/long
    CITIES = [
        {"name": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lng": 72.8777},
        {"name": "Delhi", "state": "Delhi", "lat": 28.6139, "lng": 77.2090},
        {"name": "Bangalore", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946},
        {"name": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867},
        {"name": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707},
        {"name": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lng": 88.3639},
        {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
        {"name": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714},
        {"name": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lng": 75.7873},
        {"name": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lng": 80.9462},
        {"name": "Chandigarh", "state": "Chandigarh", "lat": 30.7333, "lng": 76.7794},
        {"name": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lng": 77.4126},
        {"name": "Patna", "state": "Bihar", "lat": 25.5941, "lng": 85.1376},
        {"name": "Thiruvananthapuram", "state": "Kerala", "lat": 8.5241, "lng": 76.9366},
        {"name": "Bhubaneswar", "state": "Odisha", "lat": 20.2961, "lng": 85.8245},
        {"name": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lng": 75.8577},
        {"name": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lng": 79.0882},
        {"name": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lng": 83.2185},
        {"name": "Coimbatore", "state": "Tamil Nadu", "lat": 11.0168, "lng": 76.9558},
        {"name": "Mysore", "state": "Karnataka", "lat": 12.2958, "lng": 76.6394},
    ]

    # Email domains for testing (wide variety to avoid domain-based blocking)
    EMAIL_DOMAINS = [
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "rediffmail.com", "icloud.com", "protonmail.com",
        "mail.com", "zoho.com", "yandex.com", "gmx.com",
        "fastmail.com", "aol.com", "live.com", "msn.com",
        "inbox.com", "mailinator.com", "tutanota.com",
        "hushmail.com", "keemail.me", "dispostable.com",
        "tempmail.org", "guerrillamail.com", "trashmail.com",
    ]

    def __init__(self):
        self._used_emails: Set[str] = set()
        self._used_names: Set[str] = set()
        self._used_phones: Set[str] = set()

    def _generate_username(self, first: str, last: str) -> str:
        """Generate a unique username pattern."""
        patterns = [
            lambda f, l: f"{f.lower()}.{l.lower()}{random.randint(1, 9999)}",
            lambda f, l: f"{f[0].lower()}{l.lower()}{random.randint(10, 999)}",
            lambda f, l: f"{f.lower()}_{l.lower()}_{random.randint(1, 99)}",
            lambda f, l: f"{l.lower()}.{f.lower()}{random.randint(1, 999)}",
            lambda f, l: f"{f.lower()}{l[0].lower()}{random.randint(100, 9999)}",
            lambda f, l: f"{f.lower()}.{random.randint(1, 99)}.{l.lower()}",
            lambda f, l: f"{f.lower()}{random.randint(1, 99)}{l.lower()}",
            lambda f, l: f"{f.lower()}-{l.lower()}-{random.randint(1, 99)}",
            lambda f, l: f"{f.lower()}{l.lower()}{random.randint(2020, 2026)}",
            lambda f, l: f"{l.lower()}{f[0].lower()}{random.randint(1, 9999)}",
        ]
        pattern = random.choice(patterns)
        return pattern(first, last)

    def generate_name(self) -> Dict[str, str]:
        """Generate a unique full name."""
        is_male = random.choice([True, False])
        first_names = self.FIRST_NAMES_MALE if is_male else self.FIRST_NAMES_FEMALE

        max_attempts = 100
        for _ in range(max_attempts):
            first = random.choice(first_names)
            last = random.choice(self.LAST_NAMES)
            full_name = f"{first} {last}"

            if full_name not in self._used_names:
                self._used_names.add(full_name)
                return {
                    "first": first,
                    "last": last,
                    "full": full_name,
                    "gender": "male" if is_male else "female"
                }

        # Fallback with random suffix
        first = random.choice(first_names)
        last = random.choice(self.LAST_NAMES)
        full_name = f"{first} {last} {random.randint(1, 999)}"
        self._used_names.add(full_name)
        return {
            "first": first,
            "last": last,
            "full": full_name,
            "gender": "male" if is_male else "female"
        }

    def generate_email(self, first: str, last: str) -> str:
        """Generate a unique email address."""
        max_attempts = 100
        for _ in range(max_attempts):
            username = self._generate_username(first, last)
            domain = random.choice(self.EMAIL_DOMAINS)
            email = f"{username}@{domain}"

            if email not in self._used_emails:
                self._used_emails.add(email)
                return email

        # Fallback with UUID-like suffix
        import uuid
        email = f"{first.lower()}.{last.lower()}.{str(uuid.uuid4())[:8]}@{random.choice(self.EMAIL_DOMAINS)}"
        self._used_emails.add(email)
        return email

    def generate_password(self, length: int = None) -> str:
        """Generate a simple random password (lowercase letters only)."""
        if length is None:
            length = random.randint(8, 14)
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    def generate_weak_password(self) -> str:
        """Generate a weak password for policy testing."""
        weak_passwords = [
            "password", "123456", "qwerty", "abc123",
            "password123", "letmein", "welcome",
            "111111", "admin", "user123",
            "test", "hello", "monkey",
            "master", "sunshine", "princess",
        ]
        return random.choice(weak_passwords)

    def generate_phone(self) -> str:
        """Generate a valid Indian mobile number."""
        max_attempts = 100
        for _ in range(max_attempts):
            prefix = random.choice([6, 7, 8, 9])
            remaining = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            phone = f"+91-{prefix}{remaining}"

            if phone not in self._used_phones:
                self._used_phones.add(phone)
                return phone

        # Fallback
        prefix = random.choice([6, 7, 8, 9])
        remaining = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        phone = f"+91-{prefix}{remaining}{random.randint(10000, 99999)}"
        self._used_phones.add(phone)
        return phone

    def generate_location(self) -> Dict[str, str]:
        """Generate a location with realistic coordinates."""
        city_data = random.choice(self.CITIES)

        # Add small random offset for realism
        lat_offset = random.uniform(-0.05, 0.05)
        lng_offset = random.uniform(-0.05, 0.05)

        latitude = round(city_data["lat"] + lat_offset, 4)
        longitude = round(city_data["lng"] + lng_offset, 4)

        # Generate 6-digit pincode (first 2 digits 11-99)
        pincode = f"{random.randint(11, 99)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"

        return {
            "city": city_data["name"],
            "state": city_data["state"],
            "country": "India",
            "latitude": latitude,
            "longitude": longitude,
            "pincode": pincode
        }

    def generate_dob(self) -> str:
        """Generate a random date of birth (age 18-45)."""
        start_date = datetime(1980, 1, 1)
        end_date = datetime(2006, 12, 28)

        days_between = (end_date - start_date).days
        random_days = random.randint(0, days_between)
        dob = start_date + timedelta(days=random_days)

        return dob.strftime("%Y-%m-%d")

    def generate_identity(self, weak_password: bool = False) -> Dict:
        """Generate a complete identity profile."""
        name = self.generate_name()
        email = self.generate_email(name["first"], name["last"])

        if weak_password:
            password = self.generate_weak_password()
        else:
            password = self.generate_password()

        phone = self.generate_phone()
        location = self.generate_location()
        dob = self.generate_dob()

        return {
            "name": name,
            "email": email,
            "password": password,
            "phone": phone,
            "location": location,
            "dob": dob,
            "is_weak_password": weak_password
        }

    def generate_batch(self, count: int, weak_password_ratio: float = 0.0) -> List[Dict]:
        """Generate a batch of unique identities."""
        identities = []
        weak_count = int(count * weak_password_ratio)

        for i in range(count):
            is_weak = i < weak_count
            identity = self.generate_identity(weak_password=is_weak)
            identities.append(identity)

        return identities

    def reset(self):
        """Reset used sets for a new test run."""
        self._used_emails.clear()
        self._used_names.clear()
        self._used_phones.clear()
