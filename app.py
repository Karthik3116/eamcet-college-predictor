import json
import pandas as pd
from flask import Flask, request, render_template, make_response
from xhtml2pdf import pisa
from io import BytesIO
import os
from datetime import datetime
import pytz

temp_caste = ''
temp_gender = ''
temp_rank = 0
temp_preferred_courses = None
temp_phase = ''

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Path to the JSON file to save the visit count
visit_count_file = 'visit_count.json'

# Initialize the visit count if the file does not exist
if not os.path.exists(visit_count_file):
    with open(visit_count_file, 'w') as f:
        json.dump({'total_visits_count': 0, 'pdf_download_count': 0, 'reached_count': 0}, f)

# Function to read the visit count from the JSON file
# def read_visit_count():
#     with open(visit_count_file, 'r') as f:
#         data = json.load(f)
#     return data.get('total_visits_count', 0), data.get('pdf_download_count', 0), data.get('reached_count', 0)

# # Function to update the visit count in the JSON file
# def update_visit_count(total_visits_count, pdf_download_count, reached_count):
#     with open(visit_count_file, 'w') as f:
#         json.dump({'total_visits_count': total_visits_count, 'pdf_download_count': pdf_download_count, 'reached_count': reached_count}, f)

# Function to read the visit count from the JSON file
def read_visit_count():
    # Check if the file exists and is not empty
    if not os.path.exists(visit_count_file) or os.stat(visit_count_file).st_size == 0:
        # Initialize the JSON file with default values if it's empty or does not exist
        with open(visit_count_file, 'w') as f:
            json.dump({'total_visits_count': 0, 'pdf_download_count': 0, 'reached_count': 0}, f)
        return 0, 0, 0  # Return default counts

    try:
        with open(visit_count_file, 'r') as f:
            data = json.load(f)
        return data.get('total_visits_count', 0), data.get('pdf_download_count', 0), data.get('reached_count', 0)
    except json.JSONDecodeError:
        # If there's an error decoding the JSON, reinitialize the file
        with open(visit_count_file, 'w') as f:
            json.dump({'total_visits_count': 0, 'pdf_download_count': 0, 'reached_count': 0}, f)
        return 0, 0, 0

# Function to update the visit count in the JSON file
def update_visit_count(total_visits_count, pdf_download_count, reached_count):
    try:
        with open(visit_count_file, 'w') as f:
            json.dump({'total_visits_count': total_visits_count, 'pdf_download_count': pdf_download_count, 'reached_count': reached_count}, f)
    except IOError as e:
        print(f"Error writing to JSON file: {e}")


# Define a function to load the data based on the selected phase
def load_data(phase):
    try:
        # Load the CSV file, skipping bad lines
        data = pd.read_csv(phase, on_bad_lines='skip')
        return data
    except pd.errors.ParserError as e:
        print(f"Error reading CSV file: {e}")
        return None

# Create a directory named 'saved_data' if it doesn't exist
if not os.path.exists('saved_data'):
    os.makedirs('saved_data')

# Define the path to the CSV file to save user data
csv_file_path = 'saved_data/user_data.csv'

def get_local_time():
    # Set the time zone you want to convert to (e.g., 'Asia/Kolkata')
    local_tz = pytz.timezone('Asia/Kolkata')
    # Get the current time in UTC
    utc_now = datetime.utcnow()
    # Convert the current UTC time to the local time
    local_time = utc_now.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_time

def save_to_csv(user_data):
    user_data['timestamp'] = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
    user_data_df = pd.DataFrame(user_data, index=[0])

    # Check if the file exists
    if os.path.exists(csv_file_path):
        # Read the existing data to check for the timestamp column
        try:
            existing_data = pd.read_csv(csv_file_path)
        except pd.errors.ParserError as e:
            print(f"Error reading existing CSV file: {e}")
            existing_data = pd.DataFrame()

        # If the timestamp column does not exist, create it
        if 'timestamp' not in existing_data.columns:
            existing_data['timestamp'] = ''
            existing_data.to_csv(csv_file_path, index=False)

        # Append the new data to the CSV
        user_data_df.to_csv(csv_file_path, mode='a', index=False, header=False)
    else:
        # Create a new CSV with the new data
        user_data_df.to_csv(csv_file_path, index=False)

def get_colleges(phase, caste, gender, rank, preferred_courses=None, not_preferred_courses=None):
    total_visits_count, pdf_download_count, reached_count = read_visit_count()
    total_visits_count += 1
    update_visit_count(total_visits_count, pdf_download_count, reached_count)

    data = load_data(phase)

    if data is None:
        raise ValueError("Error loading data from CSV file")

    # Sanitize column names to remove unwanted characters
    data.columns = data.columns.str.replace(r'\s+', ' ').str.strip()

    caste_column = f"{caste.upper()} {gender.upper()}"

    if caste_column not in data.columns:
        raise ValueError("Invalid caste or gender")

    if rank <= 7000:
        lower_diff = rank * (90 / 100)
        upper_diff = 20000
    elif 7000 < rank < 50000:
        lower_diff = 4000
        upper_diff = 25000
    elif 50000 < rank < 70000:
        lower_diff = 5000
        upper_diff = 35000
    else:
        lower_diff = 6000
        upper_diff = 40000

    rank_min = rank - lower_diff
    rank_max = rank + upper_diff

    filtered_data = data[
        (data[caste_column] >= rank_min) & (data[caste_column] <= rank_max)
    ]

    if preferred_courses:
        filtered_data = filtered_data[filtered_data['Branch Code'].isin(preferred_courses)]

    if not_preferred_courses:
        filtered_data = filtered_data[~filtered_data['Branch Code'].isin(not_preferred_courses)]

    columns_to_return = ['Inst Code', 'Institute Name', 'Place',
                         'Co Education', 'College Type',
                         'Branch Code', 'Branch Name', caste_column,
                         'Tuition Fee', 'Affiliated To']

    sorted_data = filtered_data[columns_to_return].sort_values(by=caste_column)

    return sorted_data

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     global temp_caste, temp_gender, temp_rank, temp_preferred_courses, temp_phase

#     total_visits_count, pdf_download_count, reached_count = read_visit_count()
#     reached_count += 1
#     update_visit_count(total_visits_count, pdf_download_count, reached_count)

#     if request.method == 'POST':
#         phase = request.form['phase']
#         caste = request.form['caste']
#         gender = request.form['gender']
#         rank = int(request.form['rank'])

#         user_data = {
#             'phase': phase,
#             'caste': request.form['caste'],
#             'gender': request.form['gender'],
#             'rank': request.form['rank'],
#             'preferred_courses': request.form['preferred_courses'],
#         }

#         preferred_courses = request.form['preferred_courses']

#         if preferred_courses:
#             preferred_courses = [course.strip() for course in preferred_courses.split(',')]
#         else:
#             preferred_courses = None

#         not_preferred_courses = None

#         print(f"Form Data: Phase: {phase}, Caste: {caste}, Gender: {gender}, Rank: {rank}, Preferred Courses: {preferred_courses}")

#         try:
#             filtered_colleges = get_colleges(phase, caste, gender, rank, preferred_courses=preferred_courses,
#                                              not_preferred_courses=not_preferred_courses)
#         except ValueError as e:
#             return str(e), 500

#         temp_phase = phase
#         temp_caste = caste
#         temp_gender = gender
#         temp_rank = rank
#         temp_preferred_courses = preferred_courses

#         total_colleges = len(filtered_colleges)

#         save_to_csv(user_data)
#         return render_template('results.html', tables=[filtered_colleges.to_html(classes='data', index=False)],
#                               titles=filtered_colleges.columns.values, total_colleges=total_colleges)

#     return render_template('index1.html', visits_count=total_visits_count, pdf_download_count=pdf_download_count, reached_count=reached_count)

@app.route('/', methods=['GET', 'POST'])
def index():
    global temp_caste, temp_gender, temp_rank, temp_preferred_courses, temp_phase

    # Increment total visits count on every reload (GET request)
    total_visits_count, pdf_download_count, reached_count = read_visit_count()
    total_visits_count += 1
    update_visit_count(total_visits_count, pdf_download_count, reached_count)

    # Increment reached count when page is accessed via GET or POST
    if request.method == 'GET':
        reached_count += 1
        update_visit_count(total_visits_count, pdf_download_count, reached_count)

    if request.method == 'POST':
        phase = request.form['phase']
        caste = request.form['caste']
        gender = request.form['gender']
        rank = int(request.form['rank'])

        user_data = {
            'phase': phase,
            'caste': request.form['caste'],
            'gender': request.form['gender'],
            'rank': request.form['rank'],
            'preferred_courses': request.form['preferred_courses'],
        }

        preferred_courses = request.form['preferred_courses']

        if preferred_courses:
            preferred_courses = [course.strip() for course in preferred_courses.split(',')]
        else:
            preferred_courses = None

        not_preferred_courses = None

        print(f"Form Data: Phase: {phase}, Caste: {caste}, Gender: {gender}, Rank: {rank}, Preferred Courses: {preferred_courses}")

        try:
            filtered_colleges = get_colleges(phase, caste, gender, rank, preferred_courses=preferred_courses,
                                             not_preferred_courses=not_preferred_courses)
        except ValueError as e:
            return str(e), 500

        temp_phase = phase
        temp_caste = caste
        temp_gender = gender
        temp_rank = rank
        temp_preferred_courses = preferred_courses

        total_colleges = len(filtered_colleges)

        save_to_csv(user_data)
        return render_template('results.html', tables=[filtered_colleges.to_html(classes='data', index=False)],
                              titles=filtered_colleges.columns.values, total_colleges=total_colleges)

    return render_template('index1.html', visits_count=total_visits_count, pdf_download_count=pdf_download_count, reached_count=reached_count)


@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    global temp_phase, temp_caste, temp_gender, temp_rank, temp_preferred_courses

    try:
        filtered_colleges = get_colleges(temp_phase, temp_caste, temp_gender, temp_rank, preferred_courses=temp_preferred_courses)
    except ValueError as e:
        return str(e), 500

    html = render_template('results.html', tables=[filtered_colleges.to_html(classes='data', index=False)],
                          titles=filtered_colleges.columns.values, total_colleges=len(filtered_colleges))

    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=pdf)

    total_visits_count, pdf_download_count, reached_count = read_visit_count()
    pdf_download_count += 1
    update_visit_count(total_visits_count, pdf_download_count, reached_count)

    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=results.pdf'

    return response

# Define the path to the CSV file to save feedback
feedback_csv_path = 'saved_data/feedback.csv'

def save_feedback(feedback_data):
    feedback_data['timestamp'] = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
    feedback_data_df = pd.DataFrame(feedback_data, index=[0])

    # Check if the file exists
    if os.path.exists(feedback_csv_path):
        feedback_data_df.to_csv(feedback_csv_path, mode='a', index=False, header=False)
    else:
        feedback_data_df.to_csv(feedback_csv_path, index=False)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback = request.form['feedback']
    feedback_data = {
        'feedback': feedback
    }
    save_feedback(feedback_data)
    return 'Feedback submitted successfully', 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4000)
