# 💰 Expense Tracker

A full-stack web application for personal finance management and group expense tracking with built-in data analytics capabilities. This project demonstrates proficiency in data collection, storage, processing, and visualization—core skills for data science applications.

> **🚀 Live Demo**: [https://expense-tracker-ni27.onrender.com](https://expense-tracker-ni27.onrender.com)  
> **⚠️ Status**: Active development - new features and ML capabilities being added regularly

[![Python](https://img.shields.io/badge/Python-32.4%25-blue?logo=python)](https://www.python.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-31.6%25-yellow?logo=javascript)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![CSS](https://img.shields.io/badge/CSS-20.5%25-purple?logo=css3)](https://www.w3.org/Style/CSS/)
[![HTML](https://img.shields.io/badge/HTML-15.4%25-orange?logo=html5)](https://html.spec.whatwg.org/)

---

## 🎯 Project Overview

Expense Tracker is a comprehensive financial management platform that enables users to track personal expenses, manage shared group finances, and gain insights into spending patterns through data-driven analytics. The application serves as a practical demonstration of data science fundamentals applied to real-world financial data.

**Key Capabilities:**
- **Personal Finance Tracking**: Monitor individual income and expenses with detailed categorization
- **Group Expense Management**: Split bills and track shared costs among multiple users
- **Budget Analytics Dashboard**: Visualize spending patterns and financial health metrics
- **Automated Recurring Payments**: Schedule and auto-process recurring expenses
- **Income Allocation Tracking**: Categorize income distribution across savings, investments, and spending

---

## 🔬 Motivation: Data Science Connection

This project bridges personal finance management with data science methodology:

### **Data Collection & Management**
Financial data is inherently rich and complex. This application demonstrates:
- **Structured data modeling** for financial transactions, user relationships, and temporal patterns
- **Data integrity** through relational database design with proper foreign keys and cascading deletes
- **Real-time data ingestion** via REST APIs and form submissions

### **Financial Data Analysis**
Understanding spending behavior requires analytical thinking:
- **Time-series analysis** of income and expenses across months
- **Categorical aggregation** to identify spending patterns by category
- **Trend detection** using statistical methods (moving averages, variance calculations)
- **Anomaly detection** to identify unusual spending behavior

### **Data Visualization & Insights**
Effective data communication is crucial in data science:
- **Interactive pie charts** for categorical spending breakdowns (Chart.js)
- **Drill-down analysis** for exploring subcategories and detailed transactions
- **KPI dashboards** displaying key financial metrics (savings rate, net cashflow)
- **Budget health indicators** using the 50/30/20 budgeting rule

### **Predictive Analytics Foundation**
The application's architecture supports future ML integration:
- Historical data snapshots for training predictive models
- Automated budget recommendations based on spending patterns
- Infrastructure for time-series forecasting of future expenses

---

## 🛠️ Tech Stack

### **Backend (Python)**
- **Framework**: Flask 2.3.3 - Lightweight web framework for RESTful API design
- **Database ORM**: SQLAlchemy 2.0.23 - Object-relational mapping for complex data relationships
- **Database**: PostgreSQL with psycopg 3.2.9 - Production-grade relational database
- **Authentication**: Flask-Login 0.6.3 - Secure user session management
- **Migrations**: Flask-Migrate 4.0.5+ - Database version control
- **Production Server**: Gunicorn 21.2.0 - WSGI HTTP server

### **Frontend (JavaScript/HTML/CSS)**
- **Pure JavaScript** - No framework dependencies for lightweight performance
- **Chart.js 4.4.0** - Data visualization library for interactive charts
- **Responsive CSS** - Mobile-first design with custom styling
- **Dynamic DOM Manipulation** - Real-time UI updates without page reloads

### **Data Processing & Analytics**
- **Python dateutil** - Advanced date/time manipulation for time-series analysis
- **SQLAlchemy Aggregations** - Database-level data aggregation for efficiency
- **Custom Analytics Service** - Built-in statistical analysis module (see `analytics_service.py`)

### **DevOps & Deployment**
- **GitHub Actions** - Automated recurring payment processing via CI/CD
- **Render.com** - Cloud platform deployment
- **Environment Management** - python-dotenv for configuration

---

## ✨ Features

### **User & Financial Features**
- ✅ **Multi-User Support**: Create personal trackers or shared group expenses
- ✅ **Expense Tracking**: Add, edit, delete expenses with categories and descriptions
- ✅ **Income Tracking**: Record income sources and allocate to different accounts
- ✅ **Smart Bill Splitting**: Equal split calculation with participant selection
- ✅ **Balance Management**: Real-time calculation of who owes whom
- ✅ **Settlement Tracking**: Record payments between users
- ✅ **Recurring Payments**: Automated processing of monthly/weekly/daily expenses

### **Analytical & Data Science Features**
- 📊 **Budget Analytics Dashboard**: 
  - Monthly/yearly aggregated financial summaries
  - Category-wise expense breakdown with drill-down capability
  - Interactive pie charts with category filtering
  - Income vs. Expense visualization
- 💡 **Budget Analysis**:
  - Savings rate calculation
  - Budget health assessment using 50/30/20 rule
  - Essential vs. discretionary spending breakdown
  - Bucket-based allocation visualization (investments/savings/spending)
- 📅 **Data Collection Infrastructure**:
  - Structured data models for financial transactions
  - Time-series data storage with monthly snapshots
  - Automated data aggregation and categorization
  - Historical data preservation for future analysis

### **Data Management Capabilities**
- Filter expenses by date range, category, and user
- Drill-down from aggregate views to individual transactions
- Detailed transaction history with full context
- Automated recurring payment processing

---

## 📊 Data Handling & Analysis

### **Current Implementation**

**Database Architecture:**
The application uses a normalized relational database design with PostgreSQL:

**Core Data Models:**
- `users` - User authentication and profile management
- `groups` - Personal trackers and shared expense groups  
- `expenses` - Individual transaction records (amount, date, category, description)
- `income_entries` - Income tracking with source categorization
- `balances` - Calculated financial balances between users
- `budget_snapshots` - Monthly aggregated snapshots for historical tracking

**Relationship Tables:**
- `expense_participants` - Many-to-many expense splitting relationships
- `income_allocations` - Income distribution across savings/checking/investments
- `budget_categories` - Smart category-to-budget-type mappings

### **Data Processing Pipeline**

**1. Data Collection & Storage:**
- User input via web forms → REST API endpoints → SQLAlchemy ORM → PostgreSQL
- Real-time validation and data integrity checks
- Automated timestamp tracking for all transactions

**2. Data Aggregation (`analytics_service.py`):**
- Monthly financial summaries (income, expenses, allocations)
- Category-wise spending breakdowns with drill-down capability
- Budget-type classification (essentials, investments, savings, discretionary)
- Historical snapshot generation for trend analysis

**3. Automated Classification:**
The application uses keyword-based classification to categorize expenses:
- **Essential**: rent, utilities, groceries, healthcare, transportation
- **Investment**: 401k, IRA, stocks, retirement accounts
- **Emergency**: savings, emergency fund, reserves
- **Debt**: loans, credit cards, debt payments
- **Personal**: entertainment, dining, shopping, hobbies

This classification enables budget analysis using the **50/30/20 rule** (50% needs, 30% wants, 20% savings/investments).

**4. Real-Time Analytics:**
- Savings rate calculation: `(Income - Expenses) / Income × 100`
- Essential spending ratio: `Essential Expenses / Total Expenses × 100`
- Budget health indicators with color-coded alerts
- Dynamic KPI cards showing financial health metrics

### **Data Visualization**
- **Interactive Pie Charts** (Chart.js): Category breakdowns with click-to-drill-down
- **Allocation Buckets**: Visual separation of investments, savings, and spending
- **Time-Based Filtering**: Month/year selection for comparative analysis
- **Responsive Dashboards**: Mobile-friendly data displays

---

## 🚀 Setup & Running

### **Quick Start**

**Prerequisites:**
- Python 3.11+
- PostgreSQL 14+


**Production:** Deployed on Render.com with automated CI/CD via GitHub Actions for recurring payment processing.

---

## 🧪 Data Science Skills Demonstrated

This project showcases foundational data science competencies with a clear path toward advanced analytics:

### **Current Implementation**

**Data Engineering & Management:**
- ✅ Relational database design and normalization
- ✅ ETL pipeline implementation (user input → API → database)
- ✅ Data validation and integrity constraints
- ✅ Efficient SQL querying with SQLAlchemy ORM
- ✅ Database migrations and version control

**Data Processing & Aggregation:**
- ✅ Time-based data aggregation (monthly/yearly summaries)
- ✅ Multi-dimensional grouping (by category, user, budget type)
- ✅ Real-time calculation of financial metrics
- ✅ Automated data classification using keyword matching
- ✅ Historical snapshot generation for trend analysis

**Data Visualization:**
- ✅ Interactive dashboards with Chart.js
- ✅ Drill-down analysis from aggregates to transaction details
- ✅ Dynamic filtering and data slicing
- ✅ KPI cards with color-coded health indicators
- ✅ Responsive, mobile-friendly data displays

**Software Engineering:**
- ✅ RESTful API design and implementation
- ✅ Object-oriented programming (Python)
- ✅ Version control with Git/GitHub
- ✅ Production deployment with CI/CD (GitHub Actions)
- ✅ Environment management and configuration

**Problem Solving:**
- ✅ Breaking down complex financial tracking into modular components
- ✅ Building scalable, normalized data models
- ✅ Handling edge cases (zero values, missing data, date ranges)
- ✅ Performance optimization for database queries


---

## 📈 Future Improvements: Data Science Roadmap

This project is designed with extensibility in mind, providing a solid foundation for advanced data science applications. The following enhancements are planned to deepen the analytical capabilities and build production-ready ML systems:

### **Computer Vision & OCR Integration**
- **Receipt Scanner with OCR**:
  - Mobile-friendly camera interface for receipt capture
  - Optical Character Recognition (OCR) using Tesseract or Google Cloud Vision API
  - Automated extraction of merchant name, date, total amount, and line items
  - Image preprocessing (grayscale conversion, edge detection, perspective correction)
  - Confidence scoring for extracted data with manual review option
  
- **Data Augmentation Benefits**:
  - Significantly increases data volume for training ML models
  - Captures granular item-level purchase data (e.g., "eggs" vs. just "Grocery Store")
  - Enables more accurate category prediction with richer training examples
  - Real-world application of computer vision in a practical use case

### **Machine Learning for Expense Classification**
- **Automated Category Prediction**:
  - Train classification models (Random Forest, XGBoost, Neural Networks) on historical expense descriptions
  - NLP preprocessing: tokenization, stemming, TF-IDF vectorization
  - Multi-class classification to predict category from description text
  - Model evaluation: precision, recall, F1-score, confusion matrix analysis
  - Production deployment with confidence thresholds (auto-categorize if >90% confident)
  
- **Named Entity Recognition (NER)**:
  - Extract merchant names and locations from unstructured text
  - Fine-tune pre-trained models (spaCy, BERT) on financial transaction data
  - Build custom entity recognition for financial terms

### **Time-Series Forecasting & Predictive Analytics**
- **Expense Prediction Models**:
  - **ARIMA/SARIMA**: Classical time-series forecasting for monthly expense prediction
  - **Prophet (Facebook)**: Robust forecasting with automatic seasonality detection
  - **LSTM Neural Networks**: Deep learning for complex temporal patterns
  - Feature engineering: lag features, rolling statistics, day-of-week/month indicators
  - Forecast future expenses with 95% confidence intervals
  
- **Budget Planning Assistant**:
  - Predict when users will exceed their budget based on current spending velocity
  - Alert system for projected overspending in specific categories
  - "What-if" scenario analysis: "If I spend $X more on dining, how does it affect my savings goal?"

### **Anomaly Detection for Fraud & Errors**
- **Unsupervised Learning Approaches**:
  - **Isolation Forest**: Detect unusual transactions that deviate from normal patterns
  - **One-Class SVM**: Identify outliers in spending behavior
  - **Autoencoders**: Neural network-based reconstruction error for anomaly scoring
  - Real-time alerts for suspicious transactions (e.g., $500 grocery bill when average is $80)
  
- **Statistical Methods**:
  - Z-score based detection (flag expenses >2-3 standard deviations from mean)
  - Interquartile Range (IQR) method for robust outlier detection
  - Time-series based anomalies (spending spike compared to historical trends)

### **Personalized Recommendation System**
- **Smart Budget Recommendations**:
  - Collaborative filtering: "Users with similar spending patterns saved $X by reducing Y"
  - Content-based filtering: Recommend budget adjustments based on user's specific categories
  - Hybrid recommendation combining both approaches
  
- **Savings Opportunity Detection**:
  - Identify subscriptions that haven't been used (e.g., gym membership with no check-ins)
  - Detect categories with high variance → suggest switching to fixed budgets
  - Compare prices across merchants for frequently purchased items

### **Feature Engineering & Advanced Analytics**
- **Derived Metrics for ML Models**:
  - Spending velocity: rate of expense increase/decrease over time
  - Category entropy: measure of spending diversity
  - Cyclic features: sine/cosine transformations for day-of-week, month-of-year
  - Recency-frequency-monetary (RFM) analysis per category
  - Rolling window statistics: 7-day, 30-day, 90-day averages
  
- **Clustering & Segmentation**:
  - K-means clustering to identify distinct spending personas
  - DBSCAN for density-based pattern discovery
  - Hierarchical clustering for category relationship analysis
  - Cohort analysis: track behavior changes over time

### **Model Deployment & MLOps**
- **Production ML Pipeline**:
  - Feature store for consistent feature computation (training & inference)
  - Model versioning and A/B testing framework
  - Real-time model serving via REST API endpoints
  - Automated retraining pipelines when model performance degrades
  
- **Monitoring & Evaluation**:
  - Data drift detection: monitor input distribution changes
  - Model performance dashboards: track accuracy, latency, throughput
  - A/B testing infrastructure: compare model versions in production
  - Logging and explainability: SHAP values for model interpretability

### **Advanced Statistical Analysis**
- **Hypothesis Testing**:
  - T-tests to compare spending before/after budget implementation
  - Chi-square tests for category independence
  - ANOVA for comparing spending across multiple user groups
  
- **Regression Analysis**:
  - Linear regression: predict total monthly spending from category breakdowns
  - Polynomial regression for non-linear relationships
  - Ridge/Lasso regularization for feature selection
  
- **Time-Series Decomposition**:
  - Seasonal-Trend decomposition using LOESS (STL)
  - Identify weekly/monthly/yearly patterns
  - Residual analysis for understanding unexplained variance

### **Data Visualization & Reporting**
- **Interactive Dashboards** (Plotly/Dash):
  - Real-time spending heatmaps by hour/day/month
  - Sankey diagrams for income → allocation → spending flow
  - Time-series plots with confidence bands
  - Comparison charts: actual vs. predicted vs. budget
  
- **Automated Report Generation**:
  - Monthly financial health reports with insights
  - PDF export with charts and recommendations
  - Email digests with spending summaries and alerts

### **External Data Integration**
- **Banking APIs** (Plaid/Yodlee):
  - Automatic transaction import from bank accounts
  - Real-time balance synchronization
  - Reconciliation with manual entries
  
- **Data Export & Interoperability**:
  - CSV/Excel/Parquet export for external analysis
  - Integration with Google Sheets/Excel for custom reporting
  - API access for third-party applications

---

## 👨‍💻 Author

**Zach Skiba**
- GitHub: [@ZachSkiba](https://github.com/ZachSkiba)
- LinkedIn: [LinkedIn Profile](http://www.linkedin.com/in/zachary-skiba-727490293)
- Email: zskiba@hawk.illinoistech.edu
