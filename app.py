import streamlit as st
import dropbox
import pandas as pd
import io
from PIL import Image
import os

# --- Configuration ---
ACCESS_TOKEN = 'sl.u.AGFRBaeojzvFWCMey8QYMn0DURCrQbYCSLMbjWkajw3G_v7OSx2oImf5Cz_VKZ6-7eLwl7OjGZ-j8E5owC2ztUnYkK4jcS7YnH9i9DS36Ba6mqKdJJVdPbyNMlt3HjBAKIBqz5EnLdn56A77Qu_mRSZTFrDzWkLxqXAMU4w9zbNXkTKLfTzLDD54UNXbKEBc3brBwAlP-VF_bzQiU29XZfTJhlEByWxFzeNP0pUgb8TBsBS4-K1LNFbk7BhT7dQauC14f5uwLHvLb9M4_nB_C9w04XJRKqeL1NQXUHI8flauQwytkbrTAyy_HCE5fzBFo2lLcIRI73Q0y7Vozq7-e_JrvLjlfsasVucHRPiFyNVOPGnVxZmop4HuSxwwtqKB6k3F_6Q-Wpgva55xYxTps7MRdD5Ft8gzKLLfCTalo9czA2vRMq20avGJPyq3w5kBYzf9tvEAqNVvmyTuNI2qAcvhhbvcw-2onKSuaWyKmrkt3xjfpEJ7kIkLFBk8sjvR0ks56m8kvW0722wiKEQHutVR0QIbwTD1HIPWn5JJRtRemhOiIqljPJpF_F_gyqFUUahuTP_QU8WiZcbPEiqVFobNBaD7Kt-A6nOJFcZHvx052wHLHpH3VSxTxXxze1kJawfIDVtVf0yGopu6gMubTgBwtscKbIFj-9I7No2EDsX7wY2KcAPWjOcHTfh-I6HX5FFw_2zsy6acRVo4L6wvQWAXicAb4vmHKJOdImKId-95zTXOnuyBWof7n-PYf0bOiB76PdTB4IDgfOby0-1DrlaIyY_zkMta3eY3XhAcbhZAWdm5Xl_31ffDjiwFN9AlxdtEhP61cV6ff9WC_r1JtVWSO_Z8Ix4gj5o3nerjmNkadjZCnooa5dr2Q5M-2w9gxGk0Usb0ITD8ge8UbwhUoco6fmfXGgH3-N9aeXV5N51f4easR59qsg4_6YVMqxkdQbzeaOf3tPbpctcD-U2Mr4RRry6qWwUn658rrZmwaHfxL723bywXVN8BEmjCWeWvjXuluVSjZ312qofGUEbBRtBKkTKeypEa5VEgqGr2iNPNKZl5EZDrykWuJYgdE-wQWniW9XmREkH0MB5qv06VK66TMdMpkIxRJATfs95AV35C0JoEqx_HfyRQgi0SKfAI19gu6UBVK2UkQ3QKmyVOA8fk5JDTAs-bl_tgHoJAZ9QW0bCNrQUJFzY8aqEAumx_wrjQzjzHFOpth_tmmZYR2fJ9teRTnmUSCzH5WrTWWwtZnuC2SpPeE1u8SYWQLGzypOuimBXdmo3Xdcq80-WLRIxV'
IMAGE_FOLDER_PATH = '/Apps/iTECH_CRL_IMAGES'
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
