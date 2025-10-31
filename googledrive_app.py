import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import pandas as pd
import json, io
from PIL import Image
import os

# --- Google Drive Setup ---
st.title("Ultrasound Quality Scoring Tool - Google Drive Version")

@st.cache_resource
def init_gdrive():
    creds = json.loads(st.secrets["GDRIVE_CREDENTIALS_JSON"])
    with open("temp_credentials.json", "w") as f:
        json.dump(creds, f)
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile("temp_credentials.json")
    gauth.LocalWebserverAuth()
    gauth.SaveCredentialsFile("mycreds.json")
    return gauth

drive = init_gdrive()

# --- Configuration ---
IMAGE_FOLDER_ID = st.secrets["GDRIVE_IMAGE_FOLDER_ID"]  # your Drive folder ID
SCORED_FILE_NAME = "ultrasound_scores.csv"

# --- CRITERIA ---
CRITERIA = {
    '1. Mid-sagittal section': 'Midline facial profile, fetal spine and rump all visible in one complete image. Zoom box and sample gate in center of vessel',
    '2. Neutral position': 'Fluid visible between the chin and the chest of the fetus and the profile line',
    '3. Horizontal orientation': 'Fetus should be horizontal with line connecting crown and rump positioned between 75° and 105° to ultrasound beam',
    '4. Crown and rump clearly visible': 'Crown and rump should both be clearly visible',
    '5. Correct caliper placement': 'Should be placed correctly (outer border of skin covering skull and outer border of skin covering rump)',
    '6. Magnification': 'Fetus should fill more than two-thirds of image',
}
SCORES = [0, 1]

# --- Load images from Google Drive ---
@st.cache_resource
def load_images_from_gdrive():
    file_list = drive.ListFile({'q': f"'{IMAGE_FOLDER_ID}' in parents and trashed=false"}).GetList()
    images = [f for f in file_list if f['title'].lower().endswith(('.jpg', '.jpeg', '.png'))]
    return images

# --- Load or create CSV ---
def load_or_create_csv():
    file_list = drive.ListFile({'q': f"title='{SCORED_FILE_NAME}' and trashed=false"}).GetList()
    if not file_list:
        df = pd.DataFrame(columns=['Filename'] + list(CRITERIA.keys()) + ['Comments'])
        df.to_csv(SCORED_FILE_NAME, index=False)
        upload_file_to_gdrive(SCORED_FILE_NAME)
        return df
    else:
        file_obj = file_list[0]
        content = file_obj.GetContentString()
        df = pd.read_csv(io.StringIO(content))
        return df

def upload_file_to_gdrive(local_path):
    """Uploads or overwrites a CSV file in Drive."""
    existing = drive.ListFile({'q': f"title='{SCORED_FILE_NAME}' and trashed=false"}).GetList()
    if existing:
        file_obj = existing[0]
    else:
        file_obj = drive.CreateFile({'title': SCORED_FILE_NAME})
    file_obj.SetContentFile(local_path)
    file_obj.Upload()

# --- Save Scores ---
def save_scores(scores_dict, filename, comments):
    new_row = {'Filename': filename, 'Comments': comments}
    new_row.update(scores_dict)
    new_row_df = pd.DataFrame([new_row])
    st.session_state.scores_df = pd.concat([st.session_state.scores_df, new_row_df], ignore_index=True)
    csv_buffer = io.StringIO()
    st.session_state.scores_df.to_csv(csv_buffer, index=False)
    with open(SCORED_FILE_NAME, "w", encoding="utf-8") as f:
        f.write(csv_buffer.getvalue())
    upload_file_to_gdrive(SCORED_FILE_NAME)

# --- App Logic ---
if 'images' not in st.session_state:
    st.session_state.images = load_images_from_gdrive()
if 'scores_df' not in st.session_state:
    st.session_state.scores_df = load_or_create_csv()
if 'current_image_index' not in st.session_state:
    st.session_state.current_image_index = 0

if st.session_state.images:
    current_file = st.session_state.images[st.session_state.current_image_index]
    image_bytes = current_file.GetContentIOBuffer()
    img = Image.open(image_bytes)
    st.image(img, caption=f"{current_file['title']}")

    with st.form(key=f"scoring_form_{current_file['id']}"):
        st.markdown("### Score Criteria")
        scores = {}
        for criterion, description in CRITERIA.items():
            scores[criterion] = st.radio(
                label=f"**{criterion}**",
                options=SCORES,
                key=f"score_{criterion}",
                horizontal=True,
                help=description
            )
        comments = st.text_area("Comments", "N/A")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Save and Next")
        with col2:
            skip = st.form_submit_button("Skip")

    if submit:
        save_scores(scores, current_file['title'], comments)
        st.session_state.current_image_index += 1
        st.rerun()
    elif skip:
        st.session_state.current_image_index += 1
        st.rerun()
else:
    st.success("🎉 All images processed!")
    st.dataframe(st.session_state.scores_df)
