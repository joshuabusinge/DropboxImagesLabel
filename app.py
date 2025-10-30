import streamlit as st
import dropbox
import pandas as pd
import io
from PIL import Image
import os

# --- Configuration ---
ACCESS_TOKEN = 'sl.u.AGFtP13phJQCOWpWTYkV_Bsihrbp0Op9Xye-EhHxRcyQnItww4DivBtHNR8SIEA_0PId0ZIJVZydMmUUxIvcjhtMjyG2x961v0IjEEksCiE8mfkzs8WnGqkQkMCAqsLHxI-HbM11osTJtAjBB_D20dcSA_j20p9YsBEuNJJrdvH6bfunX_1wtC_GD4Q5FTNh0StGBXG4tL_S2ZS2wFGg-IabhMI_dDR6Y0Rn__Xt31_aa-r5V5URS7iLiREiyHtZJHWJDUfppzAMyCz3df6NcoKKl-TnwmrpnQ9Bjil1RPMH0Hj2QDGOFBnN4rKIm3PX-ZBxXoUUXe-1ObJBKs_soPuk8-3DzyNPQvs7yhHMEwhFdFLoTeD-S8CP-2cedpwDW6dNkmG50ipyVR0UkhUu-xHRrXjy_UOYEDrmOP-6ZWMp6UwISvceUSNVQoBvoja2plCIadPiHnMSnK30erKB5PDmmtEc_SP_4gPAjEHpNs_8tGjTAOCFfB4xD4CmA1bbUw6ye09_8APaGpwkWJveb45-j4v8NGEMv89mwivrkelDLiRI8goAyTLPot6nMzIRTfbXQ9VOL3h9lWwYyqCYLeEu6yC6GDz2dOT1D68cy5qH8NfNhAU6NjofaENxXk8val18ICGh8k3L5l3JojC84e0tTym_YwVvmwvN56kCx4wlPZI5YV1O-uusb6GZFo6DV_oOX6cjSH1rbhGORcEr4TyBkpPcL49LRxZwIFGWun1VwY7TVhSxcOjLRmid5BLuvHYMtm1fz8KTZj-15AHxkot_e19DHLLMrA0-75A9jG6DeuZjHlurNKJtY_OibNm7kQhp8CFLNTNHUzOTHRdLpZ_iFTVh0t5_M4OnLBYcgKmkHmPZp6bXT7FC0P4VV9gcMCrOrvnrbHovvnJcMBTdv6R-Fenqy47GIud6aOv1wlYg5GyMrsu4DcfODD0itP4B2Gz4UQ_1MrnkInOv6NaCqwM-VHvQtDM1gqeVl_YeN5CkPAawnAdVllyHfyt7qlKq-R-O4Ldf2olXGFVuHcgc1gFHz7R4_wJSGfPAOBDKyy8XuHcas8EnaLCMxY-OGBjIyG1BB-YIVr3O8yV_IgvGvQlpSwMX1CkAX0MIjFo14tXrHgctwzpo0-QUPf0G4DO-ijmk2G7FBF7_EZ9HbdZ5e56MQkObtbNRUid4sREpVoW1-8Pm5GRBq0doedU0jE-MvM7R5Tn__j6BUQCZ4xuJ5IzbRrUmbuOOY7LEqj6c4M8xiWw97sSR_kMdjZRQCRW7mTmI2iS4puJrnDBLvcIW_1TM'
IMAGE_FOLDER_PATH = '/Apps/MedicalImagesUltraSound'
SCORED_DATA_FILE = 'ultrasound_scores.csv' # File to save scores in Dropbox
SCORES = [0, 1] # Assuming a binary scoring system as implied by the form

# Initialize Dropbox client
dbx = dropbox.Dropbox(ACCESS_TOKEN)

# Criteria extracted from the image
CRITERIA = {
    '1. Mid-sagittal section': 'Midline facial profile, fetal spine and rump all visible in one complete image. Zoom box and sample gate in center of vessel',
    '2. Neutral position': 'Fluid visible between the chin and the chest of the fetus and the profile line',
    '3. Horizontal orientation': 'Fetus should be horizontal with line connecting crown and rump positioned between 75° and 105° to ultrasound beam',
    '4. Crown and rump clearly visible': 'Crown and rump should both be clearly visible',
    '5. Correct caliper placement': 'Should be placed correctly (outer border of skin covering skull and outer border of skin covering rump)',
    '6. Magnification': 'Fetus should fill more than two-thirds of image',
}

# --- State Management and Data Loading Functions ---
if 'images' not in st.session_state:
    st.session_state.images = []
if 'current_image_index' not in st.session_state:
    st.session_state.current_image_index = 0
if 'scores_df' not in st.session_state:
    st.session_state.scores_df = pd.DataFrame(columns=['Filename'] + list(CRITERIA.keys()) + ['Comments'])

@st.cache_resource
def load_images_from_dropbox():
    """Fetches the list of image files from the specified Dropbox folder."""
    try:
        res = dbx.files_list_folder(IMAGE_FOLDER_PATH)
        images = [
            entry.path_display for entry in res.entries
            if entry.path_display.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        return images
    except dropbox.exceptions.ApiError as err:
        st.error(f"Error accessing Dropbox: {err}")
        return []

def get_image_bytes(path):
    """Downloads an image from Dropbox."""
    try:
        _, res = dbx.files_download(path)
        return res.content
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

def save_scores(scores_dict, filename, comments):
    """Appends scores to the DataFrame and saves it to Dropbox as a CSV."""
    # Append the new data as a new row
    new_row = {'Filename': os.path.basename(filename), 'Comments': comments}
    new_row.update(scores_dict)
    st.session_state.scores_df = pd.concat([st.session_state.scores_df, pd.DataFrame([new_row])], ignore_index=True)
    
    # Save the full DataFrame to a CSV file in memory and upload to Dropbox
    csv_buffer = io.StringIO()
    st.session_state.scores_df.to_csv(csv_buffer, index=False)
    dbx.files_upload(csv_buffer.getvalue().encode('utf-8'), f"/{SCORED_DATA_FILE}", mode=dropbox.files.WriteMode('overwrite'))


# --- Streamlit UI ---
st.title("Ultrasound Quality Scoring Tool")

# Load images on the first run
if not st.session_state.images:
    st.session_state.images = load_images_from_dropbox()
    st.info(f"Found {len(st.session_state.images)} images to score.")

if st.session_state.images:
    current_path = st.session_state.images[st.session_state.current_image_index]
    image_bytes = get_image_bytes(current_path)

    if image_bytes:
        img = Image.open(io.BytesIO(image_bytes))
        st.image(img, caption=f"Scoring image {st.session_state.current_image_index + 1}/{len(st.session_state.images)}: {os.path.basename(current_path)}")

        # Create a form for scoring
        with st.form("scoring_form"):
            st.markdown("### Score Criteria")
            scores = {}
            for criterion, description in CRITERIA.items():
                col1, col2, col3 = st.columns([0.5, 3, 1])
                with col1:
                    st.write(criterion.split('.')[0])
                with col2:
                    st.markdown(f'<p style="font-size:14px; color:gray;">{description}</p>', unsafe_allow_html=True)
                with col3:
                    scores[criterion] = st.selectbox("Score", options=SCORES, key=f"score_{criterion}")
            
            comments = st.text_area("Comments", "N/A")
            
            # Form submission buttons
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_button = st.form_submit_button("Save Score and Next Image")
            with col_btn2:
                # Use a different key for skip button
                skip_button = st.form_submit_button("Skip Image") 
        
        if submit_button:
            save_scores(scores, current_path, comments)
            st.session_state.images.pop(st.session_state.current_image_index)
            if st.session_state.current_image_index >= len(st.session_state.images):
                st.session_state.current_image_index = 0
            st.rerun() # Rerun to display next image and clear form
        elif skip_button:
            st.session_state.current_image_index += 1
            if st.session_state.current_image_index >= len(st.session_state.images):
                st.session_state.current_image_index = 0
            st.rerun() # Rerun to display next image

else:
    st.write("All available images have been processed or labeled.")
