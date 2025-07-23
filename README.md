# DocuPilot: AI-Powered Loan Processing System

DocuPilot is a comprehensive loan application processing system that leverages AI agents for document classification, field extraction, eligibility assessment, and automated decision-making.

## 🏗️ System Architecture

### Core Components

1. **Document Upload & Processing** (`loan_docu_pilot_app.py`)
   - Customer-facing Streamlit application
   - Document upload, classification, and field extraction
   - Loan application form with pre-filled data

2. **Loan Officer Dashboard** (`loan_officer_dashboard.py`)
   - Officer review interface
   - AI tools integration
   - Document verification and approval workflow
   - Comprehensive audit trail

3. **AI Agents**
   - **Eligibility Agent** (`agents/eligibility_agent/`) - Loan eligibility assessment
   - **Communication Agent** (`agents/communication_agent/`) - Customer notifications
   - **Verification Agent** (`agents/verification_agent/`) - Document authenticity checks
   - **Orchestration Service** (`agents/orchestration/`) - Pipeline coordination

4. **Data Layer**
   - Azure Cosmos DB for metadata and application state
   - Azure Blob Storage for document storage
   - Azure Cognitive Search for RAG-based document queries

## 🚀 Quick Start

### Prerequisites

1. Python 3.10+
2. Azure services configured:
   - Cosmos DB
   - Blob Storage
   - Form Recognizer
   - OpenAI/Azure OpenAI
   - Cognitive Search

### Environment Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file with your Azure credentials:
   ```env
   # Azure Cosmos DB
   COSMOS_ENDPOINT=your_cosmos_endpoint
   COSMOS_KEY=your_cosmos_key
   
   # Azure Blob Storage
   AZURE_STORAGE_CONNECTION_STRING=your_blob_connection_string
   
   # Azure Form Recognizer
   FORM_RECOGNIZER_ENDPOINT=your_form_recognizer_endpoint
   FORM_RECOGNIZER_KEY=your_form_recognizer_key
   
   # Azure OpenAI
   CHAT_ENDPOINT=your_openai_endpoint
   CHAT_API_KEY=your_openai_key
   EMBED_ENDPOINT=your_embed_endpoint
   EMBED_API_KEY=your_embed_key
   
   # Azure Cognitive Search
   SEARCH_ENDPOINT=your_search_endpoint
   SEARCH_API_KEY=your_search_key
   
   # Logic App for Email
   LOGIC_APP_URL=your_logic_app_url
   ```

### Running the System

1. **Start all backend services:**
   ```bash
   python start_services.py
   ```

2. **Start the customer application:**
   ```bash
   streamlit run loan_docu_pilot_app.py
   ```

3. **Start the officer dashboard:**
   ```bash
   streamlit run loan_officer_dashboard.py --server.port 8501
   ```

## 📋 End-to-End Workflow

### 1. Customer Journey
1. **Document Upload**: Customer uploads required documents (PAN, Passport, Bank Statement, ITR, Credit Report)
2. **Automatic Processing**: System classifies documents and extracts fields
3. **Loan Application**: Customer fills loan application with pre-populated data
4. **Submission**: Application enters processing pipeline

### 2. Automated Processing
1. **Classification**: AI classifies document types
2. **Extraction**: Azure Form Recognizer extracts structured data
3. **Validation**: System checks for completeness and required fields
4. **Eligibility Assessment**: AI evaluates loan eligibility with scoring
5. **Notification**: Customer receives status updates via email

### 3. Officer Review
1. **Dashboard Access**: Officers view applications by status
2. **Document Review**: Side-by-side view of documents and extracted data
3. **AI Tools**: Access to verification, compliance, and eligibility agents
4. **Decision Making**: Approve, reject, or request additional information
5. **Audit Trail**: Complete history of all actions and decisions

## 🤖 AI Agents

### Eligibility Agent
- **Purpose**: Assess loan eligibility based on extracted financial data
- **Input**: Applicant documents and extracted fields
- **Output**: Eligibility decision with confidence score and reasoning
- **Endpoint**: `http://localhost:8000`

### Communication Agent
- **Purpose**: Send automated notifications to customers
- **Features**: Email templates for different stages, Logic App integration
- **Endpoint**: `http://localhost:8001`

### Verification Agent
- **Purpose**: Verify document authenticity and completeness
- **Features**: RAG-based document analysis, fraud detection
- **Endpoint**: `http://localhost:8003`

### Orchestration Service
- **Purpose**: Coordinate the entire application processing pipeline
- **Features**: State management, agent coordination, status tracking
- **Endpoint**: `http://localhost:8002`

## 📊 Monitoring & Compliance

### Audit Trail
- Complete logging of all system actions
- User action tracking
- AI decision logging
- Compliance reporting
- Exportable audit reports

### Dashboard Features
- Real-time application status
- Pipeline metrics
- Document verification status
- AI tool integration
- RAG-based document assistant

## 🔧 Configuration

### Document Types Supported
- PAN Card
- Passport
- Bank Statement
- Income Tax Return
- Credit Report

### Eligibility Criteria
- Income stability assessment
- Credit score evaluation
- EMI-to-income ratio analysis
- Banking behavior analysis
- Tax filing consistency

## 🧪 Testing

Run individual components:

```bash
# Test blob upload
python tests/test_blob_upload.py

# Test eligibility agent
curl -X POST "http://localhost:8000/check-eligibility" \
     -H "Content-Type: application/json" \
     -d '{"applicant_id": "test123"}'

# Test communication agent
curl -X POST "http://localhost:8001/send-notification" \
     -H "Content-Type: application/json" \
     -d '{"applicant_id": "test123", "customer_name": "Test User", "customer_email": "test@example.com", "eligibility_decision": {"decision": "Yes"}, "notification_type": "eligibility"}'
```

## 📈 Scaling & Production

### Performance Considerations
- Use Azure Functions for document processing at scale
- Implement caching for frequently accessed data
- Consider Azure Service Bus for reliable message queuing

### Security
- Implement proper authentication and authorization
- Encrypt sensitive data at rest and in transit
- Regular security audits and compliance checks

### Monitoring
- Application Insights for performance monitoring
- Custom metrics for business KPIs
- Alerting for system failures and anomalies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the documentation in each component's folder
- Review the audit trail for debugging
- Check service logs for error details
- Ensure all Azure services are properly configured

## 🔮 Roadmap

- [ ] Advanced fraud detection algorithms
- [ ] Multi-language document support
- [ ] Mobile application for customers
- [ ] Advanced analytics and reporting
- [ ] Integration with external credit bureaus
- [ ] Automated loan disbursement workflow