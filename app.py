import streamlit as st
import cv2
import numpy as np
import os

st.set_page_config(page_title="Image Based Music Player")

st.title("🎵 Image Recognition Music Player")

TARGET_IMAGE = r"image.png"
SONG_FOLDER = r"songs"


def verify_image(uploaded_image_path, target_image_path):
    target = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)
    uploaded = cv2.imread(uploaded_image_path, cv2.IMREAD_GRAYSCALE)

    if target is None or uploaded is None:
        return False, 0

    sift = cv2.SIFT_create()

    kp1, des1 = sift.detectAndCompute(target, None)
    kp2, des2 = sift.detectAndCompute(uploaded, None)

    if des1 is None or des2 is None:
        return False, 0

    matcher = cv2.FlannBasedMatcher(
        dict(algorithm=1, trees=5),
        dict(checks=50)
    )

    matches = matcher.knnMatch(des1, des2, k=2)

    good_matches = []

    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    if len(good_matches) < 10:
        return False, len(good_matches)

    src_pts = np.float32(
        [kp1[m.queryIdx].pt for m in good_matches]
    ).reshape(-1, 1, 2)

    dst_pts = np.float32(
        [kp2[m.trainIdx].pt for m in good_matches]
    ).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(
        src_pts,
        dst_pts,
        cv2.RANSAC,
        5.0
    )

    if H is None:
        return False, len(good_matches)

    inliers = np.sum(mask)

    if inliers > 15:
        return True, inliers

    return False, inliers


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