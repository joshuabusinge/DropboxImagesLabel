import streamlit as st
import dropbox
import pandas as pd
import io
from PIL import Image
import os

# --- Configuration ---
ACCESS_TOKEN = 'sl.u.AGGYeTX6m6AHYv8m0nuG-lFBzk19jLstxC8YGEZMDYvzjgtahO_i8QmxY7XhyntMOxLexyjDCzxD3bVQcZBNwHcb9Kns-t2A90Jfsh76hjF-QTZqxpngKWU4dHQZEP_Xr8WlYigrgZSZs3beRKa5ywQ9nvqEzL19KfxTN9DmtkRqqWJe8n6lrO60_WdycQiwZ9vqNAsY-vhCWK9xIOl0XmBLq4ceP0Jha5Vr5QhpY0mRrupCVv4DKOaeuVuBN1caczJHbqhS-QDuh6lsIOJN1MNoCb7OBV4Lzuj3lgW0HkXshNmNmJr-Cou-WvxVpdFNiJzRhi16ysAbT38hxZMch05CpV8Fpc-tWWgj9x7MT9pLdTivTnf1Q-ZkdHxM2rLl_-mTE8Z-ARFkXRmoF1XvZSgaP6WMOFZLOxKQVcXJXGRhwvs9XBXjDa-Imcu1BUcZvS8d1Im0OD0DZa4hdFmF62Kavy_RU1Feo1xkho4Wf6fBYaF_bfjZ3K-5-q6ijgxgx9UphtutKJ6ECv_PRjzXrOeKZ-ALQNYbGnO0oyb5C9nNs7udjqpriJSpJRGlZrZ--vy5TGFj0wjreYTikcMsYCq14eMCjLDLM_EgpSdfEqa8zpyDJyc3d0iHp_Q_fQ-RTFaGumQRJzoatA3ExtmjhXDqv9VwNVadir5_vBuNNMNapKwdPwiwQ1tHar8_4VhQRFPxCD8ElAeH0ZPX2GvAGhVp_J9OLOP53W4Qi1vvmyrfHGgxopTItbL6YcUk_ZyTMQF9lhTq65h7z7A3ojTotp1hB84UxPH-gge1UukjEJ88Nb2fSRtHduAlfdz1d08tPw3tA3lILPQfthlXzbIpQRcubEUjOPf476p3OScKPfA8m7Lu69_cK3O4bThsR_nPTna5oh7ZLMvVNCmcAdMzusgCJ4z8jAtf1HqiAnnuADH55JpeBwoYJKTxruiaoiXJNgVjlc-FQ036-ZxpwO56DtakumADASE-jIVDhUBtSgWBr0Qp8LH_AovzJybzGBFV9OT1_0upxp-w0vEohVv7Q0kNEcR9ZLuEzDmGXSFEvoLRFbK0hCxB6cm7oSW8Zo3ehsbXnx6U-HrGooA3BHuh7M4IB3ThThzZidbhrg4566kdPiyLaD9CaZwUEthRQHJqF5R53sFUCQCMWGhxIwFTWI8QrjiNDdWL67IzrUxA00Reqn-FTR0UHVYKS-NfszRq7_CDc1Bp2tSENX5Fsag3rrVgI2e17K1cgCoImU5Jphh3gfa_mkYtSoAGFhupizfI9R9DdnttIY44Z3aUkKJBoOHm'
IMAGE_FOLDER_PATH = '/home/Apps/iTECH_CRL_IMAGES'
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
