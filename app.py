import flask as jsonify
from flask import Flask, request, jsonify,send_file
from flask_sqlalchemy import SQLAlchemy
import barcode
from barcode.writer import ImageWriter
import io
import os
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import logging
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user








# Initialize Flask app and SQLAlchemy
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_NAME'] = 'your_session_cookie_name'  # Optional, but can be set for clarity

# Configure the app with database URI (modify with your actual credentials)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://assetmanagement_2nrj_user:6tIhGApu4uX9Hcx7AUJ1iXNSyAee7GPG@dpg-cue8pft2ng1s7384v3h0-a.oregon-postgres.render.com/assetmanagement_2nrj'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Directory to save barcode images in the project directory (optional)
UPLOAD_FOLDER = 'barcodes'  # Folder inside the project directory to store barcode images
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# Initialize the SQLAlchemy object with the app
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)





# Define the Employee model
class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    designation = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='active')  # Status column with default value 'active'

    # Define relationship with Product (one-to-many relationship)
    products = db.relationship('Product', backref='assigned_employee', lazy=True)

    def __init__(self, name, designation, email, status='active'):
        self.name = name
        self.designation = designation
        self.email = email
        self.status = status


# Define the Product model
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.String(255), unique=True, nullable=False)
    company = db.Column(db.String(255))  # Renamed 'product_details' to 'company'
    barcode = db.Column(db.LargeBinary)  # To store the barcode image as binary data
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'),
                            nullable=True)  # Foreign key to Employee (optional)

    # New fields
    purchase_date = db.Column(db.Date, nullable=True)  # Date of purchase
    status = db.Column(db.String(50), nullable=True)  # Status of the product (Available/Allocated/Under Maintenance)
    condition = db.Column(db.String(50), nullable=True)  # Condition of the product (e.g., new, used, damaged)
    # Define relationship with Repairs (one-to-many relationship)
    repairs = db.relationship('Repair', backref='product', lazy=True)
    cost = db.Column(db.Float, nullable=True)
    def __init__(self, product_name, serial_number, company, employee_id=None, purchase_date=None, status=None,
                 condition=None,cost=None):
        self.product_name = product_name
        self.serial_number = serial_number
        self.company = company
        self.employee_id = employee_id
        self.purchase_date = purchase_date
        self.status = status
        self.condition = condition
        self.cost=cost


    def generate_barcode(self, product_id):
        try:
            # Choose the barcode format (e.g., 'code128')
            barcode_format = barcode.get_barcode_class('code128')

            # Create the barcode with the product ID
            barcode_instance = barcode_format(str(product_id), writer=ImageWriter())

            # Save the barcode to an in-memory buffer (binary data)
            barcode_buffer = io.BytesIO()
            barcode_instance.write(barcode_buffer)

            # Get the binary data
            barcode_data = barcode_buffer.getvalue()

            # Save the barcode image to the file system (optional)
            barcode_image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'barcode_{product_id}.png')
            barcode_instance.save(barcode_image_path)

            # Return the barcode data and the image path (if needed)
            return barcode_data
        except Exception as e:
            print(f"Error generating barcode: {e}")
            return None

# Define the Repair model
class Repair(db.Model):
    __tablename__ = 'repairs'

    id = db.Column(db.Integer, primary_key=True)
    issue_description = db.Column(db.String(255), nullable=False)
    repair_center = db.Column(db.String(255), nullable=False)
    repair_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=False)

    # Foreign key to connect this repair record with a product (required but can be added later)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    def __init__(self, issue_description, repair_center, repair_date, return_date, product_id):
        self.issue_description = issue_description
        self.repair_center = repair_center
        self.repair_date = repair_date
        self.return_date = return_date
        self.product_id = product_id


class IntangibleAsset(db.Model):
    __tablename__ = 'intangible_assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # Name of the asset
    license_key = db.Column(db.String(255), unique=True, nullable=True)  # License key (optional for non-license assets)
    validity_start_date = db.Column(db.Date, nullable=True)  # Start date of validity
    validity_end_date = db.Column(db.Date, nullable=True)  # End date of validity
    vendor = db.Column(db.String(255), nullable=True)  # Vendor or provider name
    assigned_to = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # Assigned employee (optional)
    status = db.Column(db.String(50), nullable=False, default='active')  # Status (e.g., active, expired, inactive)
    subscription_cost = db.Column(db.Float, nullable=True)
    # Define relationship with Employee
    assigned_employee = db.relationship('Employee', backref='intangible_assets', lazy=True)

    def __init__(self, name, license_key=None, validity_start_date=None, validity_end_date=None, vendor=None,
                 assigned_to=None, status='active',subscription_cost=None):
        self.name = name
        self.license_key = license_key
        self.validity_start_date = validity_start_date
        self.validity_end_date = validity_end_date
        self.vendor = vendor
        self.assigned_to = assigned_to
        self.status = status
        self.subscription_cost = subscription_cost


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True, nullable=False)
    password=db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_type=db.Column(db.String(120), nullable=False)


class AdditionalAsset(db.Model):
    __tablename__ = 'additional_assets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # Name of the asset
    number = db.Column(db.Integer, nullable=False)  # Quantity or number of assets
    status = db.Column(db.String(50), nullable=True)  # Status of the asset (e.g., 'Available', 'Requested', etc.)

    def __init__(self, name, number, status=None):
        self.name = name
        self.number = number
        self.status = status


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        login_user(user)
        print(f"User {user.username} logged in successfully.")  # Debugging line
        return jsonify({'message': 'login successfully'}), 200
    return jsonify({'error': 'Invalid username or password'}), 401



# Route to add a new product
@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.get_json()

    # Validate required fields
    product_name = data.get('product_name')
    serial_number = data.get('serial_number')
    if not product_name or not serial_number:
        return jsonify({'error': 'Product name and serial number are required'}), 400

    # Optional fields
    company = data.get('company')
    employee_id = data.get('employee_id')  # The ID of the employee the product is assigned to
    purchase_date = data.get('purchase_date')  # Optional purchase date
    status = data.get('status')  # Optional status
    condition = data.get('condition')  # Optional condition

    # Create a new Product instance
    new_product = Product(
        product_name=product_name,
        serial_number=serial_number,
        company=company,
        employee_id=employee_id,
        purchase_date=purchase_date,
        status=status,
        condition=condition
    )

    try:
        # Save the product to the database
        db.session.add(new_product)
        db.session.commit()

        # Comment out barcode generation
        # barcode_data = new_product.generate_barcode(new_product.id)

        # if barcode_data:
        #     # Save the barcode image as binary data in the database
        #     new_product.barcode = barcode_data
        #     db.session.commit()

        return jsonify({
            'message': f"Product '{product_name}' added successfully.",
            'product_id': new_product.id,
            # 'barcode': f"Barcode generated and saved for product ID {new_product.id}"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Route to add a new repair
@app.route('/add_repair', methods=['POST'])
def add_repair():
    data = request.get_json()

    # Get repair details from the request
    issue_description = data.get('issue_description')
    repair_center = data.get('repair_center')
    repair_date = data.get('repair_date')
    return_date = data.get('return_date')
    product_id = data.get('product_id')  # The ID of the product being repaired

    # Create a new Repair instance
    new_repair = Repair(
        issue_description=issue_description,
        repair_center=repair_center,
        repair_date=repair_date,
        return_date=return_date,
        product_id=product_id
    )

    try:
        # Save the repair to the database
        db.session.add(new_repair)
        db.session.commit()

        return jsonify({
            'message': f"Repair record added successfully for product ID {product_id}.",
            'repair_id': new_repair.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Route to add a new employee
@app.route('/add_employee', methods=['POST'])
def add_employee():
    data = request.get_json()

    # Validate required fields
    name = data.get('name')
    designation = data.get('designation')
    email = data.get('email')
    status = data.get('status', 'active')  # Default status to 'active' if not provided

    if not name or not designation or not email:
        return jsonify({'error': 'Name, designation, and email are required.'}), 400

    # Create a new Employee instance
    new_employee = Employee(name=name, designation=designation, email=email, status=status)

    try:
        # Save the employee to the database
        db.session.add(new_employee)
        db.session.commit()

        return jsonify({
            'message': f"Employee '{name}' added successfully.",
            'employee_id': new_employee.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/assign_employee/<int:product_id>', methods=['PUT'])
def assign_employee(product_id):
    data = request.get_json()
    employee_id = data.get('employee_id')

    # Find the product by ID
    product = Product.query.get(product_id)

    if product:
        product.employee_id = employee_id  # Assign the employee to the product
        db.session.commit()
        return jsonify({'message': f"Employee {employee_id} assigned to product {product_id}."}), 200
    else:
        return jsonify({'error': 'Product not found'}), 404




@app.route('/add_intangible_asset', methods=['POST'])
def add_intangible_asset():
    data = request.get_json()

    # Validate required fields
    name = data.get('name')
    license_key = data.get('license_key')
    validity_start_date = data.get('validity_start_date')  # Should be in ISO format (YYYY-MM-DD)
    validity_end_date = data.get('validity_end_date')  # Should be in ISO format (YYYY-MM-DD)
    vendor = data.get('vendor')
    assigned_to = data.get('assigned_to')  # Employee ID to assign the asset
    status = data.get('status', 'active')  # Default to 'active' if not provided

    if not name:
        return jsonify({'error': 'Asset name is required.'}), 400

    if assigned_to:
        # Check if the employee exists
        employee = Employee.query.get(assigned_to)
        if not employee:
            return jsonify({'error': f'Employee with ID {assigned_to} not found.'}), 404

    # Create a new IntangibleAsset instance
    new_asset = IntangibleAsset(
        name=name,
        license_key=license_key,
        validity_start_date=validity_start_date,
        validity_end_date=validity_end_date,
        vendor=vendor,
        assigned_to=assigned_to,
        status=status
    )

    try:
        # Save the asset to the database
        db.session.add(new_asset)
        db.session.commit()

        return jsonify({
            'message': f"Intangible asset '{name}' added successfully.",
            'asset_id': new_asset.id,
            'assigned_to': assigned_to if assigned_to else None
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/edit_employee_status/<int:employee_id>', methods=['PUT'])
def edit_employee_status(employee_id):
    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'error': 'Status is required.'}), 400

    # Fetch the employee
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({'error': f'Employee with ID {employee_id} not found.'}), 404

    try:
        # Update the employee's status
        employee.status = new_status

        # If the status is 'left', update related products and intangible assets
        if new_status.lower() == 'left':
            # Update products assigned to the employee
            Product.query.filter_by(employee_id=employee_id).update({
                'status': 'Available',
                'employee_id': None
            })

            # Update intangible assets assigned to the employee
            IntangibleAsset.query.filter_by(assigned_to=employee_id).update({
                'assigned_to': None
            })

        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            'message': f"Employee status updated successfully to '{new_status}'.",
            'employee_id': employee.id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400








#new addings

#view asset listings
@app.route('/asset_listings', methods=['GET'])
def get_asset_listings():
    try:
        # Fetch all products (tangible assets)
        products = Product.query.all()

        # Fetch all intangible assets
        intangible_assets = IntangibleAsset.query.all()

        # Prepare the response
        asset_listings = {
            "tangible_assets": [{
                "id": product.id,
                "product_name": product.product_name,
                "serial_number": product.serial_number,
                "company": product.company,
                "status": product.status,
                "condition": product.condition,
                "assigned_to": product.assigned_employee.name if product.assigned_employee else None
            } for product in products],
            "intangible_assets": [{
                "id": asset.id,
                "name": asset.name,
                "vendor": asset.vendor,
                "status": asset.status,
                "assigned_to": asset.assigned_employee.name if asset.assigned_employee else None
            } for asset in intangible_assets]
        }

        return jsonify(asset_listings), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Internal server error"}), 500




#edit product
@app.route('/update_product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        # Find the product by ID
        product = Product.query.get(product_id)

        if not product:
            return jsonify({'error': 'Product not found'}), 404

        # Get the updated data from the request
        data = request.get_json()

        # Update the product fields
        if 'product_name' in data:
            product.product_name = data['product_name']
        if 'serial_number' in data:
            product.serial_number = data['serial_number']
        if 'company' in data:
            product.company = data['company']
        if 'purchase_date' in data:
            product.purchase_date = data['purchase_date']
        if 'status' in data:
            product.status = data['status']
        if 'condition' in data:
            product.condition = data['condition']

        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            'message': f"Product {product_id} updated successfully",
            'product': {
                'id': product.id,
                'product_name': product.product_name,
                'serial_number': product.serial_number,
                'company': product.company,
                'purchase_date': product.purchase_date,
                'status': product.status,
                'condition': product.condition
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400




@app.route('/update_intangible_asset/<int:asset_id>', methods=['PUT'])
def update_intangible_asset(asset_id):
    try:
        # Find the intangible asset by ID
        asset = IntangibleAsset.query.get(asset_id)

        if not asset:
            return jsonify({'error': 'Intangible asset not found'}), 404

        # Get the updated data from the request
        data = request.get_json()

        # Update the intangible asset fields
        if 'name' in data:
            asset.name = data['name']
        if 'license_key' in data:
            asset.license_key = data['license_key']
        if 'validity_start_date' in data:
            asset.validity_start_date = data['validity_start_date']
        if 'validity_end_date' in data:
            asset.validity_end_date = data['validity_end_date']
        if 'vendor' in data:
            asset.vendor = data['vendor']
        if 'status' in data:
            asset.status = data['status']
        if 'assigned_to' in data:
            asset.assigned_to = data['assigned_to']

        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            'message': f"Intangible asset {asset_id} updated successfully",
            'asset': {
                'id': asset.id,
                'name': asset.name,
                'license_key': asset.license_key,
                'validity_start_date': str(asset.validity_start_date),
                'validity_end_date': str(asset.validity_end_date),
                'vendor': asset.vendor,
                'status': asset.status,
                'assigned_to': asset.assigned_to
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400



@app.route('/assign_intangible_asset/<int:asset_id>', methods=['PUT'])
def assign_intangible_asset(asset_id):
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')

        # Find the intangible asset by ID
        asset = IntangibleAsset.query.get(asset_id)

        if not asset:
            return jsonify({'error': 'Intangible asset not found'}), 404

        # Find the employee by ID
        employee = Employee.query.get(employee_id)

        if not employee:
            return jsonify({'error': 'Employee not found'}), 404

        # Assign the employee to the intangible asset
        asset.assigned_to = employee_id

        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            'message': f"Intangible asset {asset_id} assigned to employee {employee_id} successfully",
            'asset': {
                'id': asset.id,
                'name': asset.name,
                'assigned_to': asset.assigned_to
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400




@app.route('/repairs/history/<int:product_id>', methods=['GET'])
def get_repair_history(product_id):
    try:
        # Query to fetch the product
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"message": "Product not found."}), 404

        # Query to fetch repairs for the given product_id, sorted by repair_date
        repair_history = Repair.query.filter_by(product_id=product_id).order_by(Repair.repair_date.desc()).all()

        # Check if there are any repairs found
        if not repair_history:
            return jsonify({"message": "No repair history found for this product."}), 404

        # Serialize the repair records
        history = [{
            "id": repair.id,
            "issue_description": repair.issue_description,
            "repair_center": repair.repair_center,
            "repair_date": repair.repair_date.strftime('%Y-%m-%d'),
            "return_date": repair.return_date.strftime('%Y-%m-%d'),
        } for repair in repair_history]

        # Prepare the response
        response = {
            "product_info": {
                "id": product.id,
                "name": product.product_name,
                "serial_number": product.serial_number
            },
            "repair_history": history
        }

        return jsonify(response), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Internal server error"}), 500




@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(
        username=data['username'],
        password=hashed_password,
        name=data['name'],
        email=data['email'],
        user_type=data['user_type']

    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Registered successfully'}), 201

@app.route('/logout', methods=['POST', 'GET'])
 # Ensure only logged-in users can access this route
def logout():
    try:
        # Log out the user using Flask-Login's logout_user() function
        logout_user()
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        logging.error(f"Error during logout: {str(e)}")
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500


@app.route('/monitor_intangible_budget', methods=['GET'])
def monitor_intangible_budget():
    try:
        # Fetch all intangible assets
        intangible_assets = IntangibleAsset.query.all()

        # Calculate the total subscription cost for intangible assets
        total_intangible_cost = sum(
            asset.subscription_cost for asset in intangible_assets if asset.subscription_cost
        )

        # Define your budget limit for intangible assets
        intangible_budget_limit =5000  # Example budget limit for intangible assets

        # Determine if the total intangible cost is within the budget
        within_budget = total_intangible_cost <= intangible_budget_limit

        # Prepare the response
        response = {
            "total_intangible_cost": total_intangible_cost,
            "intangible_budget_limit": intangible_budget_limit,
            "within_budget": within_budget
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/strategic_reports', methods=['GET'])
def strategic_reports():
    try:
        # Fetch all tangible and intangible assets
        tangible_assets = Product.query.all()
        intangible_assets = IntangibleAsset.query.all()

        # Calculate total costs
        total_tangible_cost = sum(asset.cost for asset in tangible_assets if asset.cost)
        total_intangible_cost = sum(asset.subscription_cost for asset in intangible_assets if asset.subscription_cost)
        total_cost = total_tangible_cost + total_intangible_cost

        # Count total assets
        total_tangible_assets = len(tangible_assets)
        total_intangible_assets = len(intangible_assets)

        # Prepare allocation details
        allocation_details = []
        for asset in tangible_assets:
            if asset.employee_id:
                employee = Employee.query.get(asset.employee_id)
                allocation_details.append({
                    "asset_type": "Tangible",
                    "asset_name": asset.product_name,
                    "allocated_to": employee.name if employee else "Unassigned"
                })

        for asset in intangible_assets:
            if asset.assigned_to:
                employee = Employee.query.get(asset.assigned_to)
                allocation_details.append({
                    "asset_type": "Intangible",
                    "asset_name": asset.name,
                    "allocated_to": employee.name if employee else "Unassigned"
                })

        # Prepare the response
        response = {
            "total_tangible_assets": total_tangible_assets,
            "total_intangible_assets": total_intangible_assets,
            "total_cost": total_cost,
            "allocation_details": allocation_details
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/add_additional_asset', methods=['POST'])
def add_additional_asset():
    # Get the data from the request
    data = request.get_json()

    # Check if 'name' and 'number' are in the request data
    if not data.get('name') or not data.get('number'):
        return jsonify({'message': 'Name and number are required'}), 400

    # Set default status to 'Pending' if not provided
    status = data.get('status', 'Pending')

    # Create a new AdditionalAsset instance with the default status
    new_asset = AdditionalAsset(name=data['name'], number=data['number'], status=status)

    # Add the new asset to the database
    db.session.add(new_asset)
    db.session.commit()

    # Return a success response
    return jsonify({
        'message': 'Additional asset added successfully',
        'asset': {
            'id': new_asset.id,
            'name': new_asset.name,
            'number': new_asset.number,
            'status': new_asset.status
        }
    }), 201


@app.route('/update_asset_status/<int:asset_id>', methods=['PUT'])
def update_asset_status(asset_id):
    # Get the asset by its ID
    asset = AdditionalAsset.query.get(asset_id)

    # If the asset does not exist, return a 404 error
    if not asset:
        return jsonify({'message': 'Asset not found'}), 404

    # Update the status to 'Approved'
    asset.status = 'Approved'

    # Commit the changes to the database
    db.session.commit()

    # Return a success response
    return jsonify({
        'message': 'Asset status updated to Approved',
        'asset': {
            'id': asset.id,
            'name': asset.name,
            'number': asset.number,
            'status': asset.status
        }
    }), 200


@app.route('/get_pending_assets', methods=['GET'])
def get_pending_assets():
    # Query the database for assets with status 'Pending'
    pending_assets = AdditionalAsset.query.filter_by(status='Pending').all()

    # If no pending assets are found, return a message
    if not pending_assets:
        return jsonify({'message': 'No pending assets found'}), 404

    # Prepare the response with the details of the pending assets
    assets_data = [{
        'id': asset.id,
        'name': asset.name,
        'number': asset.number,
        'status': asset.status
    } for asset in pending_assets]

    # Return the response with the list of pending assets
    return jsonify({
        'message': 'Pending assets fetched successfully',
        'assets': assets_data
    }), 200









if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002)