# Jira-Transition-Automation-Tool

This python script automates the process of reviewing and closing automated tests within Jira.

## Manual

Follow these steps to set up and run the script on your local machine.

### 1. Prerequisites
- **Python** installed on your system.
- A **Personal Access Token** generated from your Jira profile settings.

### 2. Installation & Environment Setup
It is highly recommended to use a Virtual Environment to keep your dependencies isolated. Run theses commands to install the dependencies

1. python -m venv venv
2. .\venv\Scripts\activate
3. If you get a 'SecurityError' regarding Execution Policies, run this first: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
4. pip install -r requirements.txt

### 3. Creating .env file
The script uses environment variables to handle sensitive information securely.
Copy the provided template (template.env) to create your local configuration file.
Open the newly created .env file and fill in your specific details:
1. JIRA_SERVER: The base URL of your Jira instance (e.g., https://jira.com).
2. JIRA_TOKEN: Your Personal Access Token.
3. JQL_QUERY: The search query (e.g., project = SSA AND labels = Sensified AND status = "READY FOR REVIEW").

### 4. Usage
Once your configuration is complete, run the script from your terminal:
python jira_reviewer.py