from flask import Flask, render_template, request, redirect, url_for, jsonify,session
from flask_uploads import UploadSet, configure_uploads, DATA,AllExcept
from werkzeug.utils import secure_filename
import pandas as pd
from flask import Response
import hashlib


from pymongo import MongoClient
import os

from bson import json_util

app = Flask(__name__)
app.secret_key = os.urandom(24)





# Configure Flask-Uploads
app.config['UPLOADED_FILES_DEST'] = 'uploads'
files = UploadSet('files', AllExcept(('exe', 'dll', 'so')))
configure_uploads(app, files)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['vehicle_data']
collection = db['info']



ADMIN_USERNAME = 'admin@gmail.com'
ADMIN_PASSWORD = '123'  # Don't store passwords in plaintext in real applications, use hashing



@app.route('/logout')
def logout():
    # Remove the 'is_admin' key from the session
    session.pop('is_admin', None)
    
    # Redirect to the login page
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        
        # Hash the provided password
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        # Check if the credentials are for an admin
        if username == ADMIN_USERNAME and hashed_password == hashlib.md5(ADMIN_PASSWORD.encode()).hexdigest():
            session['is_admin'] = True
            return redirect(url_for('index'))
        else:
            return 'Invalid credentials', 401
    else:
        # If it's a GET request, render the login.html template
        return render_template('login.html')

@app.route('/suggestions', methods=['GET'])
def get_suggestions():
    query = request.args.get('q', '')
    sticker_colour = request.args.get('StickerColour')
    records = []
    print(sticker_colour)
    
    # Filter based on sticker_colour
    filter_criteria = {}
    if sticker_colour:
        filter_criteria['StickerColour'] = {'$regex': sticker_colour, '$options': 'i'}  # Case-insensitive regex
    
    if query:
        filter_criteria['$or'] = [
            {'VehicleNo': {'$regex': query, '$options': 'i'}},
            {'StickerNo': {'$regex': query, '$options': 'i'}}
        ]
    
    print(f"Filter Criteria: {filter_criteria}")  # Debug print
    
    results = collection.find(filter_criteria).limit(4)  # Limit to 4 suggestions
    
    suggestions = [{'VehicleNo': doc['VehicleNo'], 'StickerNo': doc['StickerNo']} for doc in results]
    
    print(f"Suggestions: {suggestions}")  # Debug print
    
    records = json_util.dumps(suggestions)
    
    return records

@app.route('/fullData', methods=['GET'])
def get_full_data():
    vehicleNo = request.args.get('vehicleNo', '')
    stickerNo = request.args.get('stickerNo', '')
    stickerColour = request.args.get('stickerColour', '')

    
    filter_criteria = {}
    
    # If VehicleNo or StickerNo is provided, add it to the filter criteria
    if vehicleNo and vehicleNo != '[object Object]':
        print("hello")
        print(vehicleNo)
        filter_criteria['VehicleNo'] = vehicleNo
    
    if stickerNo:
        filter_criteria['StickerNo'] = stickerNo
    
    # Add StickerColour to the filter criteria
    if stickerColour:
        filter_criteria['StickerColour'] = {'$regex': stickerColour, '$options': 'i'}  # Case-insensitive regex search

    results = collection.find(filter_criteria)
    
    full_data = [doc for doc in results]

    if not session.get('is_admin'):
        for doc in full_data:
            doc.pop('ContactNumber', None)



    print(full_data)
    records = json_util.dumps(full_data)
    
    # Create a Flask response with the JSON data
    return records



@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ['xlsx', 'xls']:
            filename = os.path.join(app.config['UPLOADED_FILES_DEST'], file.filename)
            file.save(filename)
            
            # Read Excel file excluding the first row
            df = pd.read_excel(filename, engine='openpyxl', skiprows=1)
            
            # Correct column names by removing spaces
            corrected_columns = {
                'Vehicle No.': 'VehicleNo',
                'Contact Number': 'ContactNumber',
                'owner name': 'OwnerName'

            }
            df.rename(columns=corrected_columns, inplace=True)
            
            # Specify column names based on the data format
            column_mapping = {
                'Sr.No': 'SrNo',
                'Sticker Colour': 'StickerColour',
                'Type': 'Type',
                'Sticker No': 'StickerNo',
                'VehicleNo': 'VehicleNo',
                'Wing': 'Wing',
                'Name': 'Name',
                'OwnerName': 'OwnerName',

                'ContactNumber': 'ContactNumber'
            }
            
            df.rename(columns=column_mapping, inplace=True)
            
            # Convert DataFrame to dictionary
            records = df.to_dict(orient='records')
            
            # Insert records into MongoDB
            collection.insert_many(records)
            
            return redirect(url_for('index'))
    
    return render_template('upload.html')



@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
