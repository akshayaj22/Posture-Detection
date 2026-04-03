import streamlit as st
import pandas as pd
import numpy as np
import serial
import time
import joblib
from collections import deque
import matplotlib.pyplot as plt

PORT = "COM5"       
BAUD = 9600
MODEL_PATH = "posture_model_final.pkl"   
WINDOW_SIZE = 150     
CHECK_INTERVAL = 300  

st.set_page_config(page_title="Posture Detection", layout="wide")
st.title(" Real-time Posture Detection Dashboard")


model = joblib.load(MODEL_PATH)

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    st.sidebar.success(f"Connected to {PORT}")
except:
    ser = None
    st.sidebar.error(" Could not connect to Arduino. Check PORT.")

time_window = deque(maxlen=WINDOW_SIZE)
pitch_window = deque(maxlen=WINDOW_SIZE)
roll_window = deque(maxlen=WINDOW_SIZE)
status_window = deque(maxlen=WINDOW_SIZE)

session_records = []

alert_placeholder = st.empty()
status_placeholder = st.empty()
chart_placeholder = st.empty()
bar_placeholder = st.empty()

last_check = time.time()
while True:
    try:
        if ser is None:
            break

        line = ser.readline().decode("utf-8").strip()
        if not line:
            continue

        parts = line.split(",")
        if len(parts) != 2:
            continue
        pitch, roll = map(float, parts)
        X = np.array([[pitch, roll]])
        pred = model.predict(X)[0]   

        now = time.strftime("%H:%M:%S")
        time_window.append(now)
        pitch_window.append(pitch)
        roll_window.append(roll)
        status_window.append(pred)

        session_records.append(pred)

        if pred == "good":
            status_placeholder.success(f" Current Posture: GOOD Pitch={pitch:.2f}, Roll={roll:.2f}")
        elif pred == "slouching":
            status_placeholder.warning(f" Current Posture: SLOUCHING Pitch={pitch:.2f}, Roll={roll:.2f}")
        else:
            status_placeholder.warning(f" Current Posture: REACHING FORWARD Pitch={pitch:.2f}, Roll={roll:.2f}")
        
        if time.time() - last_check > CHECK_INTERVAL:
            bad_count = sum(1 for s in session_records if s != "good")
            good_count = sum(1 for s in session_records if s == "good")

            if bad_count > good_count:
                alert_placeholder.error(" ALERT: Please change to GOOD posture!")
            else:
                alert_placeholder.success("Great! Mostly good posture in last 5 mins.")

            session_records = []
            last_check = time.time()

        fig, ax = plt.subplots()
        ax.plot(time_window, pitch_window, label="Pitch")
        ax.plot(time_window, roll_window, label="Roll")
        ax.set_xlabel("Time")
        ax.set_ylabel("Angle")
        ax.legend()
        ax.set_title("Pitch & Roll Over Time")
        plt.xticks(rotation=45)
        chart_placeholder.pyplot(fig)

        posture_counts = pd.Series(status_window).value_counts()
        fig2, ax2 = plt.subplots()
        posture_counts.plot(kind="bar", color=["green", "orange", "red"], ax=ax2)
        ax2.set_title("Posture Distribution (recent)")
        ax2.set_ylabel("Count")
        bar_placeholder.pyplot(fig2)

     

    except KeyboardInterrupt:
        break
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        continue