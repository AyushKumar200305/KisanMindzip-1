"""
Curated dataset of major Indian mandi (APMC) cities with coordinates.
Used to find the nearest mandis by haversine distance from the user's GPS.

Each entry: (city_or_market_name, district, state, lat, lon)
Names match common spellings used by data.gov.in's mandi API where possible,
so we can join live price rows back to coordinates.
"""

MANDI_CITIES = [
    # Delhi NCR
    ("Azadpur", "North Delhi", "NCT of Delhi", 28.7081, 77.1750),
    ("Najafgarh", "South West Delhi", "NCT of Delhi", 28.6092, 76.9802),
    ("Narela", "North Delhi", "NCT of Delhi", 28.8527, 77.0934),
    ("Keshopur", "West Delhi", "NCT of Delhi", 28.6362, 77.0883),
    ("Ghazipur", "East Delhi", "NCT of Delhi", 28.6390, 77.3262),

    # Haryana
    ("Sonipat", "Sonipat", "Haryana", 28.9931, 77.0151),
    ("Panipat", "Panipat", "Haryana", 29.3909, 76.9635),
    ("Karnal", "Karnal", "Haryana", 29.6857, 76.9905),
    ("Kurukshetra", "Kurukshetra", "Haryana", 29.9695, 76.8783),
    ("Rohtak", "Rohtak", "Haryana", 28.8955, 76.6066),
    ("Hisar", "Hisar", "Haryana", 29.1492, 75.7217),
    ("Sirsa", "Sirsa", "Haryana", 29.5346, 75.0244),
    ("Ambala Cantt.", "Ambala", "Haryana", 30.3398, 76.8417),
    ("Faridabad", "Faridabad", "Haryana", 28.4089, 77.3178),
    ("Gurgaon", "Gurugram", "Haryana", 28.4595, 77.0266),
    ("Rewari", "Rewari", "Haryana", 28.1990, 76.6173),
    ("Bhiwani", "Bhiwani", "Haryana", 28.7975, 76.1322),
    ("Jind", "Jind", "Haryana", 29.3155, 76.3144),
    ("Yamunanagar", "Yamunanagar", "Haryana", 30.1290, 77.2674),

    # Punjab
    ("Ludhiana", "Ludhiana", "Punjab", 30.9010, 75.8573),
    ("Amritsar", "Amritsar", "Punjab", 31.6340, 74.8723),
    ("Jalandhar", "Jalandhar", "Punjab", 31.3260, 75.5762),
    ("Patiala", "Patiala", "Punjab", 30.3398, 76.3869),
    ("Bathinda", "Bathinda", "Punjab", 30.2110, 74.9455),
    ("Mohali", "S.A.S Nagar", "Punjab", 30.7046, 76.7179),
    ("Khanna", "Ludhiana", "Punjab", 30.7050, 76.2222),
    ("Moga", "Moga", "Punjab", 30.8138, 75.1717),
    ("Hoshiarpur", "Hoshiarpur", "Punjab", 31.5344, 75.9119),
    ("Sangrur", "Sangrur", "Punjab", 30.2458, 75.8421),

    # Uttar Pradesh
    ("Lucknow", "Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("Kanpur", "Kanpur Nagar", "Uttar Pradesh", 26.4499, 80.3319),
    ("Varanasi", "Varanasi", "Uttar Pradesh", 25.3176, 82.9739),
    ("Agra", "Agra", "Uttar Pradesh", 27.1767, 78.0081),
    ("Meerut", "Meerut", "Uttar Pradesh", 28.9845, 77.7064),
    ("Ghaziabad", "Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538),
    ("Noida", "Gautam Buddha Nagar", "Uttar Pradesh", 28.5355, 77.3910),
    ("Bareilly", "Bareilly", "Uttar Pradesh", 28.3670, 79.4304),
    ("Aligarh", "Aligarh", "Uttar Pradesh", 27.8974, 78.0880),
    ("Moradabad", "Moradabad", "Uttar Pradesh", 28.8386, 78.7733),
    ("Saharanpur", "Saharanpur", "Uttar Pradesh", 29.9680, 77.5552),
    ("Muzaffarnagar", "Muzaffarnagar", "Uttar Pradesh", 29.4727, 77.7085),
    ("Allahabad", "Prayagraj", "Uttar Pradesh", 25.4358, 81.8463),
    ("Gorakhpur", "Gorakhpur", "Uttar Pradesh", 26.7606, 83.3732),
    ("Jhansi", "Jhansi", "Uttar Pradesh", 25.4484, 78.5685),
    ("Mathura", "Mathura", "Uttar Pradesh", 27.4924, 77.6737),
    ("Hapur", "Hapur", "Uttar Pradesh", 28.7306, 77.7800),
    ("Sitapur", "Sitapur", "Uttar Pradesh", 27.5670, 80.6829),
    ("Etawah", "Etawah", "Uttar Pradesh", 26.7855, 79.0148),
    ("Faizabad", "Ayodhya", "Uttar Pradesh", 26.7733, 82.1497),
    ("Mainpuri", "Mainpuri", "Uttar Pradesh", 27.2348, 79.0245),
    ("Hardoi", "Hardoi", "Uttar Pradesh", 27.4185, 80.1207),
    ("Shahjahanpur", "Shahjahanpur", "Uttar Pradesh", 27.8826, 79.9117),

    # Rajasthan
    ("Jaipur", "Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("Jodhpur", "Jodhpur", "Rajasthan", 26.2389, 73.0243),
    ("Kota", "Kota", "Rajasthan", 25.2138, 75.8648),
    ("Udaipur", "Udaipur", "Rajasthan", 24.5854, 73.7125),
    ("Ajmer", "Ajmer", "Rajasthan", 26.4499, 74.6399),
    ("Bikaner", "Bikaner", "Rajasthan", 28.0229, 73.3119),
    ("Alwar", "Alwar", "Rajasthan", 27.5530, 76.6346),
    ("Sikar", "Sikar", "Rajasthan", 27.6094, 75.1399),
    ("Bhilwara", "Bhilwara", "Rajasthan", 25.3463, 74.6364),
    ("Ganganagar", "Sri Ganganagar", "Rajasthan", 29.9094, 73.8800),
    ("Hanumangarh", "Hanumangarh", "Rajasthan", 29.5817, 74.3294),
    ("Pali", "Pali", "Rajasthan", 25.7711, 73.3234),
    ("Tonk", "Tonk", "Rajasthan", 26.1693, 75.7849),
    ("Bharatpur", "Bharatpur", "Rajasthan", 27.2152, 77.4977),

    # Madhya Pradesh
    ("Indore", "Indore", "Madhya Pradesh", 22.7196, 75.8577),
    ("Bhopal", "Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("Gwalior", "Gwalior", "Madhya Pradesh", 26.2183, 78.1828),
    ("Jabalpur", "Jabalpur", "Madhya Pradesh", 23.1815, 79.9864),
    ("Ujjain", "Ujjain", "Madhya Pradesh", 23.1765, 75.7885),
    ("Sagar", "Sagar", "Madhya Pradesh", 23.8388, 78.7378),
    ("Dewas", "Dewas", "Madhya Pradesh", 22.9676, 76.0534),
    ("Satna", "Satna", "Madhya Pradesh", 24.5667, 80.8167),
    ("Ratlam", "Ratlam", "Madhya Pradesh", 23.3343, 75.0376),
    ("Khandwa", "Khandwa", "Madhya Pradesh", 21.8252, 76.3522),
    ("Mandsaur", "Mandsaur", "Madhya Pradesh", 24.0734, 75.0682),
    ("Vidisha", "Vidisha", "Madhya Pradesh", 23.5251, 77.8081),
    ("Hoshangabad", "Narmadapuram", "Madhya Pradesh", 22.7475, 77.7222),

    # Maharashtra
    ("Mumbai", "Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("Pune", "Pune", "Maharashtra", 18.5204, 73.8567),
    ("Nagpur", "Nagpur", "Maharashtra", 21.1458, 79.0882),
    ("Nashik", "Nashik", "Maharashtra", 19.9975, 73.7898),
    ("Aurangabad", "Aurangabad", "Maharashtra", 19.8762, 75.3433),
    ("Solapur", "Solapur", "Maharashtra", 17.6599, 75.9064),
    ("Kolhapur", "Kolhapur", "Maharashtra", 16.7050, 74.2433),
    ("Sangli", "Sangli", "Maharashtra", 16.8524, 74.5815),
    ("Latur", "Latur", "Maharashtra", 18.4088, 76.5604),
    ("Akola", "Akola", "Maharashtra", 20.7002, 77.0082),
    ("Amravati", "Amravati", "Maharashtra", 20.9374, 77.7796),
    ("Jalgaon", "Jalgaon", "Maharashtra", 21.0077, 75.5626),
    ("Lasalgaon", "Nashik", "Maharashtra", 20.1453, 74.2391),
    ("Vashi", "Thane", "Maharashtra", 19.0760, 72.9989),
    ("Ahmednagar", "Ahmednagar", "Maharashtra", 19.0948, 74.7480),

    # Gujarat
    ("Ahmedabad", "Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("Surat", "Surat", "Gujarat", 21.1702, 72.8311),
    ("Vadodara", "Vadodara", "Gujarat", 22.3072, 73.1812),
    ("Rajkot", "Rajkot", "Gujarat", 22.3039, 70.8022),
    ("Bhavnagar", "Bhavnagar", "Gujarat", 21.7645, 72.1519),
    ("Junagadh", "Junagadh", "Gujarat", 21.5222, 70.4579),
    ("Jamnagar", "Jamnagar", "Gujarat", 22.4707, 70.0577),
    ("Gondal", "Rajkot", "Gujarat", 21.9610, 70.8022),
    ("Mahuva", "Bhavnagar", "Gujarat", 21.0900, 71.7700),
    ("Unjha", "Mehsana", "Gujarat", 23.8033, 72.3940),
    ("Mehsana", "Mehsana", "Gujarat", 23.5880, 72.3693),
    ("Anand", "Anand", "Gujarat", 22.5645, 72.9289),

    # Bihar
    ("Patna", "Patna", "Bihar", 25.5941, 85.1376),
    ("Gaya", "Gaya", "Bihar", 24.7914, 85.0002),
    ("Muzaffarpur", "Muzaffarpur", "Bihar", 26.1209, 85.3647),
    ("Bhagalpur", "Bhagalpur", "Bihar", 25.2425, 86.9842),
    ("Darbhanga", "Darbhanga", "Bihar", 26.1542, 85.8918),
    ("Purnia", "Purnia", "Bihar", 25.7771, 87.4753),
    ("Begusarai", "Begusarai", "Bihar", 25.4182, 86.1272),

    # West Bengal
    ("Kolkata", "Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Howrah", "Howrah", "West Bengal", 22.5958, 88.2636),
    ("Siliguri", "Darjeeling", "West Bengal", 26.7271, 88.3953),
    ("Asansol", "Paschim Bardhaman", "West Bengal", 23.6739, 86.9524),
    ("Durgapur", "Paschim Bardhaman", "West Bengal", 23.5204, 87.3119),
    ("Burdwan", "Purba Bardhaman", "West Bengal", 23.2324, 87.8615),
    ("Malda", "Malda", "West Bengal", 25.0119, 88.1411),

    # Karnataka
    ("Bengaluru", "Bengaluru Urban", "Karnataka", 12.9716, 77.5946),
    ("Mysuru", "Mysuru", "Karnataka", 12.2958, 76.6394),
    ("Hubballi", "Dharwad", "Karnataka", 15.3647, 75.1240),
    ("Mangaluru", "Dakshina Kannada", "Karnataka", 12.9141, 74.8560),
    ("Belagavi", "Belagavi", "Karnataka", 15.8497, 74.4977),
    ("Davangere", "Davangere", "Karnataka", 14.4644, 75.9218),
    ("Ballari", "Ballari", "Karnataka", 15.1394, 76.9214),
    ("Tumakuru", "Tumakuru", "Karnataka", 13.3409, 77.1010),
    ("Shivamogga", "Shivamogga", "Karnataka", 13.9299, 75.5681),
    ("Raichur", "Raichur", "Karnataka", 16.2076, 77.3463),
    ("Gadag", "Gadag", "Karnataka", 15.4290, 75.6360),
    ("Kalaburagi", "Kalaburagi", "Karnataka", 17.3297, 76.8343),

    # Tamil Nadu
    ("Chennai", "Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("Coimbatore", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
    ("Madurai", "Madurai", "Tamil Nadu", 9.9252, 78.1198),
    ("Tiruchirappalli", "Tiruchirappalli", "Tamil Nadu", 10.7905, 78.7047),
    ("Salem", "Salem", "Tamil Nadu", 11.6643, 78.1460),
    ("Tirunelveli", "Tirunelveli", "Tamil Nadu", 8.7139, 77.7567),
    ("Erode", "Erode", "Tamil Nadu", 11.3410, 77.7172),
    ("Vellore", "Vellore", "Tamil Nadu", 12.9165, 79.1325),
    ("Thanjavur", "Thanjavur", "Tamil Nadu", 10.7870, 79.1378),
    ("Dindigul", "Dindigul", "Tamil Nadu", 10.3673, 77.9803),

    # Telangana
    ("Hyderabad", "Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Warangal", "Warangal Urban", "Telangana", 17.9784, 79.6000),
    ("Karimnagar", "Karimnagar", "Telangana", 18.4386, 79.1288),
    ("Nizamabad", "Nizamabad", "Telangana", 18.6725, 78.0941),
    ("Khammam", "Khammam", "Telangana", 17.2473, 80.1514),
    ("Mahbubnagar", "Mahbubnagar", "Telangana", 16.7488, 77.9854),

    # Andhra Pradesh
    ("Visakhapatnam", "Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    ("Vijayawada", "Krishna", "Andhra Pradesh", 16.5062, 80.6480),
    ("Guntur", "Guntur", "Andhra Pradesh", 16.3067, 80.4365),
    ("Tirupati", "Chittoor", "Andhra Pradesh", 13.6288, 79.4192),
    ("Kurnool", "Kurnool", "Andhra Pradesh", 15.8281, 78.0373),
    ("Nellore", "Sri Potti Sriramulu Nellore", "Andhra Pradesh", 14.4426, 79.9865),
    ("Anantapur", "Anantapur", "Andhra Pradesh", 14.6819, 77.6006),
    ("Kadapa", "Y.S.R.", "Andhra Pradesh", 14.4753, 78.8298),
    ("Rajahmundry", "East Godavari", "Andhra Pradesh", 17.0005, 81.8040),

    # Kerala
    ("Thiruvananthapuram", "Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    ("Kochi", "Ernakulam", "Kerala", 9.9312, 76.2673),
    ("Kozhikode", "Kozhikode", "Kerala", 11.2588, 75.7804),
    ("Thrissur", "Thrissur", "Kerala", 10.5276, 76.2144),
    ("Palakkad", "Palakkad", "Kerala", 10.7867, 76.6548),

    # Odisha
    ("Bhubaneswar", "Khordha", "Odisha", 20.2961, 85.8245),
    ("Cuttack", "Cuttack", "Odisha", 20.4625, 85.8828),
    ("Rourkela", "Sundargarh", "Odisha", 22.2604, 84.8536),
    ("Sambalpur", "Sambalpur", "Odisha", 21.4669, 83.9756),
    ("Berhampur", "Ganjam", "Odisha", 19.3149, 84.7941),

    # Chhattisgarh
    ("Raipur", "Raipur", "Chhattisgarh", 21.2514, 81.6296),
    ("Bilaspur", "Bilaspur", "Chhattisgarh", 22.0797, 82.1409),
    ("Durg", "Durg", "Chhattisgarh", 21.1904, 81.2849),

    # Jharkhand
    ("Ranchi", "Ranchi", "Jharkhand", 23.3441, 85.3096),
    ("Jamshedpur", "East Singhbhum", "Jharkhand", 22.8046, 86.2029),
    ("Dhanbad", "Dhanbad", "Jharkhand", 23.7957, 86.4304),

    # Uttarakhand
    ("Dehradun", "Dehradun", "Uttarakhand", 30.3165, 78.0322),
    ("Haridwar", "Haridwar", "Uttarakhand", 29.9457, 78.1642),
    ("Haldwani", "Nainital", "Uttarakhand", 29.2183, 79.5130),
    ("Rudrapur", "Udham Singh Nagar", "Uttarakhand", 28.9845, 79.4123),

    # Himachal Pradesh
    ("Shimla", "Shimla", "Himachal Pradesh", 31.1048, 77.1734),
    ("Solan", "Solan", "Himachal Pradesh", 30.9045, 77.0967),
    ("Mandi", "Mandi", "Himachal Pradesh", 31.7080, 76.9318),

    # Assam
    ("Guwahati", "Kamrup Metropolitan", "Assam", 26.1445, 91.7362),
    ("Dibrugarh", "Dibrugarh", "Assam", 27.4728, 94.9120),
    ("Silchar", "Cachar", "Assam", 24.8333, 92.7789),
    ("Jorhat", "Jorhat", "Assam", 26.7509, 94.2037),

    # J&K
    ("Srinagar", "Srinagar", "Jammu and Kashmir", 34.0837, 74.7973),
    ("Jammu", "Jammu", "Jammu and Kashmir", 32.7266, 74.8570),

    # Goa
    ("Panaji", "North Goa", "Goa", 15.4909, 73.8278),
    ("Margao", "South Goa", "Goa", 15.2832, 73.9862),
]


def all_states():
    return sorted({c[2] for c in MANDI_CITIES})
