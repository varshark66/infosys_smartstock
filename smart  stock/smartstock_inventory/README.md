# Smart Inventory Management System

A modern, web-based inventory management system designed for retail store owners and staff. Built with Flask, MongoDB, and modern web technologies.

## 🚀 Features

### 📊 Dashboard
- **Real-time Statistics**: Total products, stock levels, sales data
- **Interactive Charts**: Sales overview, inventory status, top-selling products
- **Quick Actions**: Add products, record sales, generate reports
- **Alerts Panel**: Low stock warnings and system notifications

### 📦 Product Management
- **Complete CRUD Operations**: Add, edit, delete products
- **Stock Tracking**: Real-time inventory levels
- **Category Management**: Organize products by categories
- **Search & Filter**: Find products quickly
- **Status Indicators**: Visual stock status (In Stock, Low Stock, Out of Stock)

### 📈 Inventory Control
- **Stock Updates**: Stock in/out operations
- **Low Stock Alerts**: Automatic notifications
- **Reorder Suggestions**: Smart recommendations
- **Bulk Operations**: Update multiple items
- **Inventory Reports**: Comprehensive analytics

### 💰 Sales & Transactions
- **Sales Recording**: Quick transaction entry
- **Payment Methods**: Multiple payment options
- **Transaction History**: Complete sales records
- **Daily Summaries**: Revenue and transaction analytics
- **Customer Management**: Optional customer details

### ⚠️ Alerts System
- **Smart Notifications**: Low stock, out of stock alerts
- **Priority Levels**: Critical, warning, info alerts
- **Alert Management**: Resolve and track alerts
- **Email Notifications**: Optional email alerts
- **Alert History**: Complete audit trail

### 📄 Reports & Analytics
- **Sales Reports**: Detailed sales analytics
- **Inventory Reports**: Stock level analysis
- **Financial Summaries**: Revenue tracking
- **Export Options**: CSV and PDF exports
- **Custom Date Ranges**: Flexible reporting periods

### 🤖 Smart Assistant
- **AI-Powered Chat**: Natural language queries
- **Quick Actions**: Predefined common tasks
- **Inventory Insights**: Smart recommendations
- **Natural Language Processing**: User-friendly interface

### 👥 User Management
- **Role-Based Access**: Admin, Manager, Staff roles
- **User Profiles**: Complete user management
- **Permission Controls**: Granular access rights
- **Activity Tracking**: User login monitoring

### ⚙️ System Settings
- **Shop Configuration**: Business details setup
- **Alert Preferences**: Customizable notifications
- **System Preferences**: Currency, timezone, language
- **Backup & Restore**: Data protection features

## 🛠️ Technology Stack

### Backend
- **Flask**: Python web framework
- **MongoDB**: NoSQL database
- **JWT**: Authentication tokens
- **Werkzeug**: Security utilities

### Frontend
- **Bootstrap 5**: Responsive UI framework
- **Font Awesome**: Icon library
- **Chart.js**: Data visualization
- **Vanilla JavaScript**: Interactive features

### Design
- **Modern UI**: Clean, professional interface
- **Responsive Design**: Mobile-friendly
- **Business-Friendly**: Suitable for non-technical users
- **Accessibility**: WCAG compliant design

## 📋 Installation

### Prerequisites
- Python 3.8+
- MongoDB server
- pip package manager

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd smartstock_inventory
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure MongoDB**
   - Ensure MongoDB is running on localhost:27017
   - Create database named "smartstock"

5. **Run the Application**
   ```bash
   cd smartstock_inventory/smartstock_inventory/smartstock_inventory
   python app.py
   ```

6. **Access the Application**
   - Open browser to: http://127.0.0.1:5000
   - Login with existing credentials or register new account

## 🔧 Configuration

### Database Configuration
Update MongoDB connection in `app.py`:
```python
client = MongoClient("mongodb://localhost:27017/")
db = client["smartstock"]
```

### Email Configuration
Update email settings in `app.py`:
```python
EMAIL_ADDRESS = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"
```

### Security Settings
Update secret key in `app.py`:
```python
app.config["SECRET_KEY"] = "your-secret-key"
```

## 📱 User Guide

### Getting Started
1. **Login**: Use your credentials to access the system
2. **Dashboard**: Overview of your inventory status
3. **Navigation**: Use sidebar menu to access different modules

### Managing Products
1. Go to **Products** section
2. Click **Add Product** to create new items
3. Use search and filters to find products
4. Edit or delete products using action buttons

### Recording Sales
1. Navigate to **Sales** section
2. Select product and enter quantity
3. Choose payment method
4. Click **Record Sale** to complete transaction

### Managing Inventory
1. Visit **Inventory** section
2. View current stock levels
3. Use **Update Stock** for stock in/out operations
4. Check reorder suggestions for low stock items

### Generating Reports
1. Go to **Reports** section
2. Select report type and date range
3. Click **Generate Report**
4. Export results in CSV or PDF format

## 🎯 Key Features for Business Owners

### Easy to Use
- **Intuitive Interface**: No technical knowledge required
- **Quick Actions**: One-click operations for common tasks
- **Visual Indicators**: Color-coded status for easy understanding

### Time-Saving
- **Automated Alerts**: Never run out of stock unexpectedly
- **Quick Sales Entry**: Fast transaction recording
- **Smart Suggestions**: AI-powered recommendations

### Business Insights
- **Real-time Analytics**: Understand your business performance
- **Sales Trends**: Track product popularity
- **Inventory Optimization**: Reduce carrying costs

### Scalable
- **Multi-User Support**: Add staff members with role-based access
- **Growth Ready**: Handles increasing product volumes
- **Flexible Configuration**: Customize to your business needs

## 🔒 Security Features

- **JWT Authentication**: Secure user sessions
- **Password Hashing**: Protected user credentials
- **Role-Based Access**: Controlled system access
- **Input Validation**: Prevents common attacks
- **Session Management**: Secure user sessions

## 📊 Reporting Capabilities

### Sales Reports
- Daily/Weekly/Monthly sales
- Product performance analysis
- Revenue tracking
- Customer insights

### Inventory Reports
- Stock level analysis
- Low stock alerts
- Inventory valuation
- Movement tracking

### Financial Reports
- Revenue summaries
- Profit analysis
- Cost tracking
- Tax reporting

## 🚀 Performance Features

- **Fast Loading**: Optimized database queries
- **Responsive Design**: Works on all devices
- **Real-time Updates**: Live data synchronization
- **Efficient Search**: Quick product lookup
- **Bulk Operations**: Handle multiple items efficiently

## 🛠️ Development

### Project Structure
```
smartstock_inventory/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── dashboard.html   # Dashboard page
│   ├── products.html    # Products management
│   ├── inventory.html   # Inventory control
│   ├── sales.html       # Sales transactions
│   ├── alerts.html      # Alerts management
│   ├── reports.html     # Reports generation
│   ├── smart_assistant.html # AI assistant
│   ├── user_management.html # User management
│   └── settings.html    # System settings
└── static/
    ├── css/
    │   └── dashboard.css # Custom styles
    └── js/
        └── dashboard.js  # JavaScript functionality
```

### API Endpoints
- `/api/dashboard/stats` - Dashboard statistics
- `/api/products` - Product CRUD operations
- `/api/sales` - Sales management
- `/api/inventory/update` - Stock updates
- `/api/alerts` - Alert management
- `/api/reports/generate` - Report generation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Email: support@smartstock.com
- Documentation: Check this README and inline comments
- Issues: Report bugs via GitHub issues

## 🔄 Updates

Version 1.0.0 - Initial Release
- Complete inventory management system
- User authentication and authorization
- Real-time dashboard and analytics
- Smart assistant with AI capabilities
- Comprehensive reporting system
- Mobile-responsive design

---

**Smart Inventory Management System** - Empowering businesses with intelligent inventory solutions.
