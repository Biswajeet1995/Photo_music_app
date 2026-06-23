import streamlit as st
import os

from verify import TARGET_IMAGE, SONG_FOLDER, verify_image

st.set_page_config(page_title="Image Based Music Player")

st.title("🎵 Image Recognition Music Player")

uploaded_file = st.file_uploader(
    "Upload or Scan an Image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file:

    temp_path = "temp_upload.jpg"

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    st.image(temp_path, caption="Uploaded Image")

    matched, score = verify_image(
        temp_path,
        TARGET_IMAGE
    )

    st.write(f"Matching Score: {score}")

    if matched:

        st.success("✅ Authorized Image Detected")

        songs = [
            file for file in os.listdir(SONG_FOLDER)
            if file.endswith(".mp3")
        ]

        if songs:

            selected_song = st.selectbox(
                "Choose a Song",
                songs
            )

            song_path = os.path.join(
                SONG_FOLDER,
                selected_song
            )

            audio_file = open(song_path, "rb")

            st.audio(
                audio_file.read(),
                format="audio/mp3"
            )

        else:
            st.warning("No songs found.")

    else:
        st.error("❌ Image Not Recognized")
