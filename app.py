import streamlit as st
import dropbox
import pandas as pd
import io
from PIL import Image
import os

# --- Configuration ---
ACCESS_TOKEN = st.secrets["DBX_ACCESS_TOKEN"]
IMAGE_FOLDER_PATH = '/Apps/iTECH_CRL_IMAGES'
SCORED_DATA_FILE = 'ultrasound_scores.csv' # File to save scores in Dropbox
SCORES = [0, 1] # Assuming a binary scoring system as implied by the form

# Initialize Dropbox client
try:
    dbx = dropbox.Dropbox(ACCESS_TOKEN)
except Exception as e:
    st.error(f"Error connecting to Dropbox. Check your ACCESS_TOKEN: {e}")
    st.stop()

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
        if isinstance(err.error, dropbox.files.ListFolderError) and err.error.is_path() and err.error.get_path().is_not_found():
            st.error(f"Error: Dropbox folder not found: {IMAGE_FOLDER_PATH}")
            st.error("Please ensure the path is correct and the app has permissions.")
        else:
            st.error(f"Error accessing Dropbox: {err}")
        return []

@st.cache_data(ttl=300) # Cache image bytes for 5 minutes
def get_image_bytes(path):
    """Downloads an image from Dropbox."""
    try:
        _, res = dbx.files_download(path)
        return res.content
    except Exception as e:
        st.error(f"Error loading image '{path}': {e}")
        return None

# 3. FIX: Add function to load existing scores
@st.cache_resource
def load_scores_from_dropbox():
    """Loads the existing CSV from Dropbox, or returns an empty DataFrame."""
    try:
        _, res = dbx.files_download(SCORED_DATA_FILE)
        csv_data = res.content.decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_data))
        st.success(f"Loaded {len(df)} existing scores.")
        return df
    except dropbox.exceptions.ApiError as err:
        # If the file doesn't exist, just return an empty DF
        if isinstance(err.error, dropbox.files.DownloadError) and err.error.is_path() and err.error.get_path().is_not_found():
            st.info("No existing score file found. Starting a new one.")
            return pd.DataFrame(columns=['Filename'] + list(CRITERIA.keys()) + ['Comments'])
        else:
            st.error(f"Error loading scores: {err}")
            return pd.DataFrame(columns=['Filename'] + list(CRITERIA.keys()) + ['Comments'])
    except Exception as e:
        st.error(f"Error processing scores file: {e}")
        return pd.DataFrame(columns=['Filename'] + list(CRITERIA.keys()) + ['Comments'])

def save_scores(scores_dict, filename, comments):
    """Appends scores to the DataFrame and saves it to Dropbox as a CSV."""
    new_row = {'Filename': os.path.basename(filename), 'Comments': comments}
    new_row.update(scores_dict)
    
    # Use pd.concat instead of .append() which is deprecated
    new_row_df = pd.DataFrame([new_row])
    st.session_state.scores_df = pd.concat([st.session_state.scores_df, new_row_df], ignore_index=True)
    
    # Save the full DataFrame to a CSV file in memory and upload to Dropbox
    try:
        csv_buffer = io.StringIO()
        st.session_state.scores_df.to_csv(csv_buffer, index=False)
        dbx.files_upload(
            csv_buffer.getvalue().encode('utf-8'), 
            SCORED_DATA_FILE, 
            mode=dropbox.files.WriteMode('overwrite')
        )
    except Exception as e:
        st.error(f"Failed to save scores: {e}")


# --- Streamlit UI ---
st.title("Ultrasound Quality Scoring Tool")

# Initialize session state
if 'images' not in st.session_state:
    st.session_state.images = []
if 'current_image_index' not in st.session_state:
    st.session_state.current_image_index = 0
if 'scores_df' not in st.session_state:
    # 3. FIX: Load existing scores on first run
    st.session_state.scores_df = load_scores_from_dropbox()

# Load images on the first run
if not st.session_state.images:
    with st.spinner("Loading images from Dropbox..."):
        all_images = load_images_from_dropbox()
        if all_images:
            # 4. IMPROVEMENT: Filter out images that are already scored
            scored_files = set(st.session_state.scores_df['Filename'])
            st.session_state.images = [
                path for path in all_images 
                if os.path.basename(path) not in scored_files
            ]
            
            st.info(f"Found {len(all_images)} total images. {len(st.session_state.images)} remain to be scored.")
            if not st.session_state.images and scored_files:
                st.success("All images in the folder have already been scored!")
        else:
            st.warning("No images found in the Dropbox folder.")

if st.session_state.images:
    current_path = st.session_state.images[st.session_state.current_image_index]
    image_bytes = get_image_bytes(current_path)

    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            st.image(img, caption=f"Scoring image {st.session_state.current_image_index + 1}/{len(st.session_state.images)}: {os.path.basename(current_path)}")
        except Exception as e:
            st.error(f"Could not open image file. It may be corrupt. {e}")
            # Skip this corrupt image
            st.session_state.images.pop(st.session_state.current_image_index)
            st.rerun()

        # Create a form for scoring
        # Use a unique key for the form to reset it on each new image
        with st.form(key=f"scoring_form_{current_path}"):
            st.markdown("### Score Criteria")
            scores = {}
            for criterion, description in CRITERIA.items():
                # Use st.radio for 0/1 scores, it's often clearer
                scores[criterion] = st.radio(
                    label=f"**{criterion}**", 
                    options=SCORES, 
                    key=f"score_{criterion}", 
                    horizontal=True,
                    help=description
                )
                st.markdown(f'<p style="font-size:14px; color:gray; margin-top:-10px;">{description}</p>', unsafe_allow_html=True)
                st.divider()

            comments = st.text_area("Comments", "N/A")
            
            # Form submission buttons
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_button = st.form_submit_button("Save Score and Next Image")
            with col_btn2:
                skip_button = st.form_submit_button("Skip Image") 

        if submit_button:
            save_scores(scores, current_path, comments)
            # Remove the image from the list so it's not scored again
            st.session_state.images.pop(st.session_state.current_image_index)
            # Check if index is now out of bounds
            if st.session_state.current_image_index >= len(st.session_state.images):
                st.session_state.current_image_index = 0
            st.success(f"Score saved for {os.path.basename(current_path)}")
            st.rerun() 
        elif skip_button:
            st.session_state.current_image_index += 1
            if st.session_state.current_image_index >= len(st.session_state.images):
                st.session_state.current_image_index = 0
            st.rerun() 

else:
    st.success("🎉 All available images have been processed or labeled!")
    st.write("Here's a summary of the scores:")
    st.dataframe(st.session_state.scores_df)
