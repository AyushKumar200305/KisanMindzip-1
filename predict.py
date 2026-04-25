import joblib
import pandas as pd

# Load model
model = joblib.load("crop_model.pkl")

def predict_crop(N, P, K, temp, humidity, ph, rainfall):
    data = pd.DataFrame([{
        "N": N,
        "P": P,
        "K": K,
        "temperature": temp,
        "humidity": humidity,
        "ph": ph,
        "rainfall": rainfall
    }])

    prediction = model.predict(data)
    return prediction[0]


# Test
if __name__ == "__main__":
    result = predict_crop(90, 40, 40, 25, 80, 6.5, 200)
    print("Recommended Crop:", result)