from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import numpy as np
import json
from io import BytesIO
import os
import pandas as pd
from set_stack import set_stack
import ATR1D
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from get_electric import get_electric
from flask import Flask, jsonify, request
from random import randint
from flask_mail import Mail, Message
import time
import smtplib
from scipy.optimize import differential_evolution

app = Flask(__name__)
app.secret_key = 'your_secure_secret_key'  # Secret key for session management

# MongoDB setup
client = MongoClient('mongodb+srv://mamtasonwalkar:yGU66G4xsIeiGdjp@cluster0.jmfvm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['AWI_users']
users = db['AWI_users']

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_password'
mail = Mail(app)

# Temporary storage for OTPs (use a database or Redis in production)
otp_storage = {}

# Directory containing CSV material files
materials_directory = r"output_csv_files"
UPLOAD_FOLDER = r"output_csv_files"
UPLOADS_DIRECTORY = os.path.join(UPLOAD_FOLDER, 'uploads')  # Path for user-uploaded files
GLS_FILE_PATH = r"GLS_NEW.csv"

# Ensure both the main upload directory and the uploads subfolder exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOADS_DIRECTORY, exist_ok=True)

@app.route('/frontpage')
def frontpage():
    return render_template('new_fp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['email'] = email
            session['firstName'] = user['name'].split()[0]  # Extract the first name
            return redirect(url_for('materials'))
        else:
            return render_template('login.html', error='Invalid email or password')

    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['firstName'] + ' ' + request.form['lastName']
        email = request.form['signUpEmail'].strip().lower()
        password = request.form['signUpPassword']
        confirm_password = request.form['confirmPassword']

        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')

        hashed_password = generate_password_hash(password)
        new_user = {'name': name, 'email': email, 'password': hashed_password}
        users.insert_one(new_user)

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp = randint(100000, 999999)  # Generate a 6-digit OTP
    otp_storage[email] = {'otp': otp, 'expires': time.time() + 300}  # Store OTP for 5 minutes

    # Log the email and OTP for debugging
    print(f"Sending OTP {otp} to email {email}")

    # Send OTP via email
    try:
        msg = Message('Your OTP Code', sender='your_email@example.com', recipients=[email])
        msg.body = f"Your OTP code is {otp}. It is valid for 5 minutes."
        print("Attempting to send email...")
        mail.send(msg)
        print("Email sent successfully.")
        return jsonify({"message": "OTP sent successfully"}), 200
    except smtplib.SMTPException as smtp_error:
        print(f"SMTP error occurred: {smtp_error}")
        return jsonify({"error": "SMTP error occurred"}), 500
    except Exception as e:
        print(f"General error sending OTP: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    if email not in otp_storage:
        return jsonify({"error": "Invalid or expired OTP"}), 400

    stored_otp = otp_storage[email]
    if time.time() > stored_otp['expires']:
        return jsonify({"error": "OTP has expired"}), 400

    if int(otp) == stored_otp['otp']:
        del otp_storage[email]  # Remove OTP after successful verification
        return jsonify({"message": "OTP verified successfully"}), 200
    else:
        return jsonify({"error": "Invalid OTP"}), 400

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form['email'].strip().lower()  # Normalize to lowercase and strip spaces
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    hashed_password = generate_password_hash(new_password)

    # Debugging: Log the input email
    print(f"Input email (trimmed and lowercase): '{email}'")

    # Debugging: Print all emails in the database
    print("Database emails:")
    for user in users.find({}):
        print(f"Stored email: '{user['email']}'")

    # Perform the update query
    result = users.update_one(
        {"email": email},  # Exact match
        {"$set": {"password": hashed_password}}
    )

    if result.matched_count > 0:
        print("Password updated successfully for:", email)
        return jsonify({"message": "Password updated successfully"}), 200
    else:
        print("Email not found in query:", email)
        return jsonify({"error": "Email not found"}), 404



@app.route('/get_layers', methods=['GET'])
def get_layers():
    # Fetch the layers from the session
    layers = session.get('layers', [])
    return jsonify({"layers": layers})



def simulate_TRA(thicknesses, start_wavelength, end_wavelength):
    """
    Simulates TRA (Transmittance/Reflectance) for the given thicknesses and wavelength range.
    Args:
        thicknesses (list): List of layer thicknesses.
        start_wavelength (float): Start wavelength for the simulation.
        end_wavelength (float): End wavelength for the simulation.
    Returns:
        float: Average TRA value in the given range.
    """
    try:
        lam = np.linspace(start_wavelength, end_wavelength, 100)  # Wavelength range
        materials = session.get('materials', [])  # Retrieve materials from session
        theta = session.get('theta', 0)  # Angle of incidence
        incoh = session.get('incoh', 1000)  # Incoherence parameter

        stack = set_stack(materials, thicknesses, lam, theta, incoh)
        _, transmittance, _ = ATR1D(stack)

        # Compute the average transmittance over the wavelength range
        avg_transmittance = np.mean(transmittance['sp'])
        return avg_transmittance
    except Exception as e:
        print(f"Error in simulate_TRA: {str(e)}")
        raise e


@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        # Get data from the request
        data = request.json
        targets = data.get('targets', [])
        layers = data.get('layers', [])

        # Validate inputs
        if not targets or not layers:
            return jsonify({"error": "Invalid payload. Missing targets or layers."}), 400

        # Filter layers to exclude "Glass"
        layers_to_optimize = [layer for layer in layers if layer['material'].lower() != 'glass']

        if not layers_to_optimize:
            return jsonify({"error": "No layers selected for optimization."}), 400

        # Get session parameters (e.g., start_wavelength, end_wavelength, etc.)
        start_wavelength = session.get('start_wavelength', 380)
        end_wavelength = session.get('end_wavelength', 1200)
        theta = session.get('theta', 0)
        incoh = session.get('incoh', 1000)

        # Extract current thicknesses for optimization
        initial_thicknesses = [layer['thickness'] for layer in layers_to_optimize]

        # Objective function for optimization
        def objective_function(thicknesses):
            # Update session layers with current thickness
            for i, layer in enumerate(layers_to_optimize):
                layer['thickness'] = thicknesses[i]

            # Simulate the current setup and calculate TRA
            try:
                avg_TRA = simulate_TRA(thicknesses, start_wavelength, end_wavelength)
                return -avg_TRA  # Maximize TRA (negate because differential_evolution minimizes)
            except Exception as e:
                print(f"Simulation error: {str(e)}")
                return float('inf')  # Return high value for invalid configurations

        # Perform optimization using Differential Evolution
        bounds = [(1, 1000) for _ in initial_thicknesses]  # Example bounds for thicknesses (1nm to 1000nm)
        result = differential_evolution(objective_function, bounds, strategy='best1bin', maxiter=1000, tol=0.01)

        if not result.success:
            print(f"Optimization failed: {result.message}")
            return jsonify({"error": "Optimization failed. Please try again."}), 500

        # Update layers with optimized thicknesses
        optimized_thicknesses = result.x.tolist()
        for i, layer in enumerate(layers_to_optimize):
            layer['thickness'] = optimized_thicknesses[i]

        return jsonify({
            "success": True,
            "optimized_thicknesses": optimized_thicknesses,
            "objective_value": -result.fun,  # Negated back to reflect maximized TRA
        })
    except Exception as e:
        print(f"Error during optimization: {str(e)}")
        return jsonify({"error": "Failed to optimize layers."}), 500




@app.route('/save_targets', methods=['POST'])
def save_targets():
    try:
        # Get targets from the request
        targets = request.json.get('targets', [])

        # Validate targets (ensure required fields are present)
        validated_targets = []
        for target in targets:
            if not all(k in target for k in ['kind', 'reflTran', 'polarization', 'wavelengthBegin', 'wavelengthEnd', 'targetBegin', 'targetEnd', 'tolerance', 'environment']):
                return jsonify({"error": "Invalid target format"}), 400
            validated_targets.append(target)

        # Save to session (or optionally to a database)
        session['targets'] = validated_targets

        return jsonify({"success": True, "targets_saved": len(validated_targets)})
    except Exception as e:
        print(f"Error saving targets: {str(e)}")
        return jsonify({"error": "Failed to save targets."}), 500



@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    session.pop('first_name', None)
    return redirect(url_for('login'))

@app.route('/help', methods=['GET', 'POST'])
def help():
    return render_template('help.html', first_name=session.get('firstName'))

@app.route('/public_designs', methods=['GET'])
def public_designs():
    print("Accessing /public_designs route")  # Debugging print
    try:
        return render_template('public_designs.html', first_name=session.get('firstName'))
    except Exception as e:
        print(f"Error rendering template: {e}")
        return "Error loading page", 500


@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Get the data from the form submission
        start_wavelength = int(request.form['start_wavelength'])
        end_wavelength = int(request.form['end_wavelength'])
        glass_thickness = int(request.form['glass_thickness'])
        theta = float(request.form['theta'])
        incoh = float(request.form['incoh'])

        # Store these inputs in the session
        session['start_wavelength'] = start_wavelength
        session['end_wavelength'] = end_wavelength
        session['glass_thickness'] = glass_thickness
        session['theta'] = theta
        session['incoh'] = incoh

        return redirect(url_for('index'))

    print("Session data in welcome route:", session)  # Debugging: Print session data
    return render_template('welcome.html', first_name=session.get('firstName'))


@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('frontpage'))

    # Retrieve inputs from the session
    start_wavelength = session.get('start_wavelength', 380)
    end_wavelength = session.get('end_wavelength', 1080)
    glass_thickness = session.get('glass_thickness', 320000)
    theta = session.get('theta', 0)
    incoh = session.get('incoh', 1000)

    return render_template('index.html', first_name=session.get('firstName'),
                           start_wavelength=start_wavelength,
                           end_wavelength=end_wavelength,
                           glass_thickness=glass_thickness,
                           theta=theta,
                           incoh=incoh)

@app.route('/get_materials', methods=['GET'])
def get_materials():
    materials = {}
    for root, dirs, files in os.walk(materials_directory):
        for file in files:
            if file.endswith('.csv'):
                folder_name = os.path.basename(root)
                if folder_name not in materials:
                    materials[folder_name] = []
                materials[folder_name].append(file)
    return jsonify(materials)

@app.route('/preview_material', methods=['GET'])
def preview_material():
    folder = request.args.get('folder')
    material = request.args.get('material')

    if folder and material:
        # Construct path using folder and material
        material_path = os.path.join(materials_directory, folder, material)
    else:
        # Use filename directly if no folder is provided
        filename = request.args.get('filename')
        material_path = os.path.join(materials_directory, filename)

    try:
        with open(material_path, 'r') as file:
            lines = [file.readline().strip() for _ in range(10)]
        return jsonify({"material": material, "preview": lines})
    except Exception as e:
        print(f"Error previewing material: {str(e)}")
        return jsonify({"error": "Failed to preview material."}), 500
UPLOAD_FOLDER = r"output_csv_files"
GLS_FILE_PATH = r"GLS_NEW.csv"

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        start_wavelength = float(data.get('start_wavelength', 380))
        end_wavelength = float(data.get('end_wavelength', 1200))
        lam = np.linspace(start_wavelength, end_wavelength, 851)
        theta = float(data.get('theta', 0))

        if theta is None:
            return jsonify({"error": "Theta value is missing"}), 400

        # Check for None values
        if start_wavelength is None or end_wavelength is None or theta is None:
            return jsonify({"error": "Missing input values"}), 400

        # Convert to float
        try:
            start_wavelength = float(start_wavelength)
            end_wavelength = float(end_wavelength)
            theta = float(theta)
        except ValueError:
            return jsonify({"error": "Invalid input values"}), 400



        # Process Bragg1 and Bragg2 file paths with a check to avoid double prefixing
        bragg1_files = [
            os.path.normpath(file if file.startswith(UPLOAD_FOLDER) else os.path.join(UPLOAD_FOLDER, file.replace(" - ", os.sep)))
            for file in data.get('bragg1', [])
        ]
        bragg2_files = [
            os.path.normpath(file if file.startswith(UPLOAD_FOLDER) else os.path.join(UPLOAD_FOLDER, file.replace(" - ", os.sep)))
            for file in data.get('bragg2', [])
        ]

        # Construct materials list, handling "air" and GLS_NEW.csv as special cases
        materials = ["air"] + bragg1_files + [GLS_FILE_PATH] + bragg2_files + ["air"]

        # Print constructed paths for debugging
        print("Constructed materials paths:", materials)  # Debug print to verify paths

        # Retrieve other parameters
        dBragg1 = data.get('dBragg1', [34.13])
        dBragg2 = data.get('dBragg2', [53.91])
        dgls = data.get('dgls', 320000)
        theta = data.get('theta', 0)
        incoh = data.get('incoh', 1000)

        # Combine thicknesses for stack
        dPSC = dBragg1 + [dgls] + dBragg2

        # Check file paths for all materials except "air"
        for material_path in materials:
            if material_path != "air" and not os.path.exists(material_path):
                print(f"Error: File not found - {material_path}")  # Debug statement
                return jsonify({"error": f"File not found: {material_path}"}), 400

        # Create the stack and run the ATR1D simulation
        stack = set_stack(materials, dPSC, lam, theta, incoh)
        A, T_PSC_AZO_EVA_PV, R = ATR1D(stack)

        # Process results
        transmittance = np.array(T_PSC_AZO_EVA_PV['sp'])
        reflectance = np.array(R['sp'])
        absorptance = 1 - transmittance - reflectance

        # Calculate electrical properties
        IV = get_electric(lam, transmittance)
        jsc = IV['jsc']

        # Prepare response
        response = {
            'wavelengths': lam.tolist(),
            'transmittance': transmittance.tolist(),
            'reflectance': reflectance.tolist(),
            'absorptance': absorptance.tolist(),
            'jsc': jsc
        }
        return jsonify(response)
    except Exception as e:
        print(f"Error during calculation: {str(e)}")  # Log exception for debugging
        return jsonify({"error": str(e)}), 500



@app.route('/save_design', methods=['POST'])
def save_design():
    if not session.get('logged_in'):
        return jsonify({"error": "User not logged in"}), 403

    user_email = session.get('email')
    design_data = request.json

    try:
        # Extract design data
        name = design_data.get('name', 'Unnamed Design')
        visibility = design_data.get('visibility', 'private')  # Default to private if not specified
        front_materials = design_data.get('frontMaterials', [])
        front_thicknesses = design_data.get('frontThicknesses', [])
        back_materials = design_data.get('backMaterials', [])
        back_thicknesses = design_data.get('backThicknesses', [])
        glass_thickness = design_data.get('glassThickness', 0)
        start_wavelength = design_data.get('startWavelength', 0)
        end_wavelength = design_data.get('endWavelength', 0)
        theta = design_data.get('theta', 0)
        incoh = design_data.get('incoh', 0)

        # Construct the design document
        design_document = {
            "user_email": user_email,
            "name": name,
            "visibility": visibility,
            "design": {
                "name": name,
                "visibility": visibility,
                "frontMaterials": front_materials,
                "frontThicknesses": front_thicknesses,
                "backMaterials": back_materials,
                "backThicknesses": back_thicknesses,
                "glassThickness": glass_thickness,
                "startWavelength": start_wavelength,
                "endWavelength": end_wavelength,
                "theta": theta,
                "incoh": incoh,
            }
        }

        # Insert the document into the database
        db['designs'].insert_one(design_document)

        return jsonify({"success": True}), 201
    except Exception as e:
        print(f"Error saving design: {str(e)}")
        return jsonify({"error": "Failed to save design."}), 500
@app.route('/get_user_designs', methods=['GET'])
def get_user_designs():
    if not session.get('logged_in'):
        return jsonify({"error": "User not logged in"}), 403

    user_email = session.get('email')
    if not user_email:
        return jsonify({"error": "User email not found in session"}), 403

    try:
        # Fetch designs for the logged-in user
        designs = db['designs'].find({"user_email": user_email}, {"_id": 0, "design": 1})
        design_list = []

        for design in designs:
            if 'design' not in design:
                print(f"Missing 'design' key in document: {design}")
            else:
                design_list.append({
                    "name": design["design"].get("name", "Unnamed Design"),
                    "details": design["design"]
                })

        for design in design_list:
            design["details"]["theta"] = design["details"].get("theta", 0)  # Default to 0 if missing

        return jsonify({"designs": design_list}), 200
    except Exception as e:
        print(f"Error retrieving designs: {str(e)}")
        return jsonify({"error": "Failed to retrieve designs"}), 500


@app.route('/upload_material', methods=['POST'])
def upload_material():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Check file extension
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Please upload a .csv file"}), 400

    # Validate contents: Check if the file has three columns separated by commas
    content = file.read().decode('utf-8').strip()
    lines = content.split('\n')
    for line in lines:
        if len(line.split(',')) != 3:
            return jsonify({"error": "The CSV must have exactly three columns: wavelength, n, k"}), 400

    # Save the file to the uploads directory specifically for user-uploaded files
    file_path = os.path.join(UPLOADS_DIRECTORY, file.filename)
    file.seek(0)  # Reset file pointer to the beginning after reading for validation
    file.save(file_path)
    print(f"File saved to: {file_path}")  # Debugging statement to verify file path

    return jsonify({"message": "File uploaded successfully", "file_path": file_path}), 200

@app.route('/get_public_designs', methods=['GET'])
def get_public_designs():
    try:
        # Fetch all public designs and include user_email explicitly
        public_designs = db['designs'].find(
            {"visibility": "public"},
            {"_id": 0, "name": 1, "user_email": 1, "design": 1}  # Ensure user_email is included
        )

        # Log the fetched designs for debugging
        designs_list = []
        for design in public_designs:
            print("Fetched design from DB:", design)  # Debugging log
            designs_list.append({
                "name": design.get("name", "Unnamed Design"),
                "user_email": design.get("user_email", "Unknown User"),
                "details": design.get("design", {})
            })

        print("Formatted designs list:", designs_list)  # Debugging log
        return jsonify({"designs": designs_list}), 200
    except Exception as e:
        print(f"Error fetching public designs: {str(e)}")
        return jsonify({"error": "Failed to fetch public designs"}), 500





@app.route('/load_design', methods=['GET'])
def load_design():
    if not session.get('logged_in'):
        return jsonify({"error": "User not logged in"}), 403

    design_name = request.args.get('design_name')
    if not design_name:
        return jsonify({"error": "Design name is required"}), 400

    user_email = session.get('email')
    try:
        design = db['designs'].find_one({"user_email": user_email, "design.name": design_name}, {"_id": 0, "design": 1})
        if not design:
            return jsonify({"error": "Design not found"}), 404

        return jsonify({"design": design["design"]}), 200
    except Exception as e:
        print(f"Error loading design: {str(e)}")
        return jsonify({"error": "Failed to load design"}), 500

@app.route('/delete_design', methods=['DELETE'])
def delete_design():
    if not session.get('logged_in'):
        return jsonify({"error": "User not logged in"}), 403

    user_email = session.get('email')
    if not user_email:
        return jsonify({"error": "User email not found in session"}), 403

    data = request.json  # Get JSON payload
    design_name = data.get('name')  # Extract design name

    print(f"Delete request received for user: {user_email}")  # Log user email
    print(f"Delete request received for design name: {design_name}")  # Log design name

    if not design_name:
        return jsonify({"error": "Design name is required"}), 400

    try:
        # Ensure the query matches the structure of your MongoDB document
        result = db['designs'].delete_one({
            "user_email": user_email,  # Match by user email
            "design.name": design_name  # Match by nested design name
        })

        if result.deleted_count == 0:
            print("No design found to delete.")  # Debugging log
            return jsonify({"error": "Design not found"}), 404

        print(f"Deleted design successfully: {design_name}")  # Debugging log
        return jsonify({"success": True}), 200
    except Exception as e:
        print(f"Error deleting design: {str(e)}")  # Log exception
        return jsonify({"error": "Failed to delete design"}), 500



@app.route('/materials', methods=['GET', 'POST'])
def materials():
    # Fetch the list of available materials from the directory or database
    materials_list = os.listdir(materials_directory)  # Assuming materials are stored as files
    return render_template('available_materials.html', materials=materials_list,  first_name=session.get('firstName'))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
